import logging
import urllib.parse
import json
import re
from typing import List, Set, Dict, Optional, Any
from playwright.async_api import Page
from scraper.adapters.base import JobPortalAdapter
from scraper.core.models import Job
from scraper.core.rate_limit import with_retry, page_limiter, serp_limiter
from scraper.config.settings import settings

logger = logging.getLogger(__name__)


class IndeedAdapter(JobPortalAdapter):
    """
    Indeed adapter using embedded JSON extraction with stable CSS fallbacks.
    Resilient to HTML changes by preferring JSON-LD and window data over DOM selectors.
    """

    BASE_URL = "https://www.indeed.com"
    SEARCH_URL = "https://www.indeed.com/jobs"
    MAX_PAGES = 5  # Limit pagination to avoid infinite loops
    JOBS_PER_PAGE = 10  # Indeed default

    def __init__(
        self, context, query: str = "software engineer", location: str = "remote"
    ):
        super().__init__(context)
        self.query = query
        self.location = location
        self.seen_jks: Set[str] = set()

    def _extract_json_from_script(
        self, html: str, pattern: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from script tags using regex pattern.
        Returns None if extraction or parsing fails.
        """
        try:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Failed to parse JSON from script: {e}")
        return None

    async def _extract_mosaic_data(self, page: Page) -> List[Dict[str, Any]]:
        """
        Extract job cards from window.mosaic.providerData embedded in page.
        This is Indeed's primary data structure for search results.
        """
        try:
            html = await page.content()
            # Pattern matches: window.mosaic.providerData["mosaic-provider-jobcards"]={...}
            pattern = r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*({.*?});'
            data = self._extract_json_from_script(html, pattern)

            if (
                data
                and "metaData" in data
                and "mosaicProviderJobCardsModel" in data["metaData"]
            ):
                job_cards = data["metaData"]["mosaicProviderJobCardsModel"].get(
                    "results", []
                )
                logger.info(f"Extracted {len(job_cards)} jobs from mosaic data")
                return job_cards
        except Exception as e:
            logger.warning(f"Failed to extract mosaic data: {e}")
        return []

    async def _extract_jobs_from_dom(self, page: Page) -> List[Dict[str, str]]:
        """
        Fallback: Extract job data from DOM using stable selectors.
        Returns list of job dictionaries with id, title, company, location, url.
        Based on actual Indeed HTML structure: #mosaic-provider-jobcards > div > ul > li
        """
        jobs = []
        try:
            # Try user-provided specific path first (slider items), then generic list items
            # User path: #mosaic-provider-jobcards ... div.slider_item ...
            potential_cards = [
                # Deep selector for table-based layout matches user provided structure
                "#mosaic-provider-jobcards > div > ul > li > div > div > div > div.slider_item.css-17bghu4.eu4oa1w0 > div > div > table > tbody > tr > td",
                "#mosaic-provider-jobcards ul li div.slider_item",  # Specific slider item for Indeed India
                "#mosaic-provider-jobcards ul li",  # Generic list item fallback
            ]

            job_cards = []
            for selector in potential_cards:
                cards = await page.locator(selector).all()
                if cards:
                    logger.info(
                        f"Found {len(cards)} job cards using selector: {selector}"
                    )
                    job_cards = cards
                    break

            if not job_cards:
                logger.warning("No job cards found with any selector")
                return []

            for card in job_cards:
                try:
                    job_data = {}

                    # Extract job link with data-jk attribute (contains job ID)
                    # Use .first to find it anywhere within the card container
                    link = card.locator("a[data-jk]").first
                    if await link.count() == 0:
                        continue

                    # Job ID from data-jk attribute
                    job_id = await link.get_attribute("data-jk")
                    if not job_id:
                        continue
                    job_data["id"] = job_id

                    # Job URL from href
                    href = await link.get_attribute("href")
                    if href:
                        # Indeed URLs can be relative, make absolute
                        if href.startswith("/"):
                            job_data["url"] = f"{self.BASE_URL}{href}"
                        else:
                            job_data["url"] = href
                    else:
                        job_data["url"] = f"{self.BASE_URL}/viewjob?jk={job_id}"

                    # Job Title from span with title attribute or link text
                    title_span = card.locator("span[title]").first
                    if await title_span.count() > 0:
                        title = await title_span.get_attribute("title")
                        job_data["title"] = title if title else await link.inner_text()
                    else:
                        job_data["title"] = await link.inner_text()

                    # Company name from data-testid="company-name"
                    company_elem = card.locator('[data-testid="company-name"]').first
                    if await company_elem.count() > 0:
                        job_data["company"] = await company_elem.inner_text()

                    # Location from data-testid="text-location"
                    location_elem = card.locator('[data-testid="text-location"]').first
                    if await location_elem.count() > 0:
                        job_data["location"] = await location_elem.inner_text()

                    jobs.append(job_data)

                except Exception as e:
                    logger.debug(f"Failed to extract job card: {e}")
                    continue

            logger.info(f"Successfully extracted {len(jobs)} jobs from DOM")
        except Exception as e:
            logger.warning(f"Failed to extract jobs from DOM: {e}")

        return jobs

    async def _detect_bot_challenge(self, page: Page) -> bool:
        """
        Detect if Indeed is showing captcha or bot detection page.
        More specific checks to avoid false positives.
        """
        try:
            # Check for actual CAPTCHA elements or challenge page indicators
            captcha_selectors = [
                'iframe[src*="hcaptcha"]',
                'iframe[src*="recaptcha"]',
                'div[class*="captcha"]',
                'div[id*="captcha"]',
                '#px-captcha',
                '.g-recaptcha',
            ]
            
            for selector in captcha_selectors:
                if await page.locator(selector).count() > 0:
                    logger.warning(f"CAPTCHA detected: {selector}")
                    return True
            
            # Check if we're on an error/blocked page (no job listings)
            has_jobs = await page.locator("#mosaic-provider-jobcards").count() > 0
            if not has_jobs:
                html = await page.content()
                # Only flag if we see blocking keywords AND no job cards
                blocking_keywords = [
                    "security check",
                    "verify you're human",
                    "access denied",
                    "blocked",
                ]
                html_lower = html.lower()
                if any(keyword in html_lower for keyword in blocking_keywords):
                    logger.warning("Possible bot challenge page detected")
                    return True
            
            return False
        except Exception as e:
            logger.debug(f"Error in bot detection: {e}")
            return False

    async def _scroll_to_load_all_jobs(self, page: Page) -> None:
        """
        Slowly scroll down to the bottom of the page to ensure all job listings are loaded.
        Indeed uses lazy loading, so scrolling triggers loading of additional job cards.
        """
        try:
            logger.info("Starting slow scroll to load all jobs...")
            
            # Get initial scroll height
            previous_height = await page.evaluate("document.body.scrollHeight")
            
            # Scroll in steps to simulate human behavior and trigger lazy loading
            scroll_step = 300  # pixels per scroll
            scroll_pause = 0.3  # seconds between scrolls
            
            current_position = 0
            max_scrolls = 50  # Safety limit to prevent infinite scrolling
            scrolls_done = 0
            
            while scrolls_done < max_scrolls:
                # Scroll down by scroll_step pixels
                current_position += scroll_step
                await page.evaluate(f"window.scrollTo(0, {current_position})")
                
                # Wait for content to load
                await page.wait_for_timeout(int(scroll_pause * 1000))
                
                # Check if we've reached the bottom
                current_height = await page.evaluate("document.body.scrollHeight")
                viewport_bottom = await page.evaluate("window.pageYOffset + window.innerHeight")
                
                # If we're at the bottom and no new content loaded, we're done
                if viewport_bottom >= current_height - 100:  # 100px threshold
                    # Wait a bit to see if more content loads
                    await page.wait_for_timeout(1000)
                    new_height = await page.evaluate("document.body.scrollHeight")
                    
                    if new_height == previous_height:
                        logger.info(f"Reached bottom after {scrolls_done} scrolls")
                        break
                    
                    previous_height = new_height
                
                scrolls_done += 1
            
            # Scroll back to top to start extraction
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)
            
            logger.info("Scrolling complete, all jobs loaded")
            
        except Exception as e:
            logger.warning(f"Error during scrolling: {e}")
            # Continue anyway - we'll work with whatever loaded

    @with_retry()
    async def discover_jobs(self) -> List[str]:
        """
        Discover job URLs from Indeed SERP with pagination support.
        Extracts from embedded JSON first, falls back to DOM selectors.
        """
        job_urls: List[str] = []
        page_num = 0

        async with serp_limiter:
            page = await self.context.new_page()
            try:
                while page_num < self.MAX_PAGES:
                    start_offset = page_num * self.JOBS_PER_PAGE
                    params = {
                        "q": self.query,
                        "l": self.location,
                        "sort": "date",
                        "start": start_offset,
                    }
                    url = f"{self.SEARCH_URL}?{urllib.parse.urlencode(params)}"

                    logger.info(f"Navigating to SERP page {page_num + 1}: {url}")
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=settings.NAVIGATION_TIMEOUT,
                    )

                    # Check for bot detection
                    if await self._detect_bot_challenge(page):
                        logger.error(
                            "Bot detection challenge detected. Stopping pagination."
                        )
                        break

                    # Scroll to load all jobs before extraction
                    await self._scroll_to_load_all_jobs(page)

                    # Try extracting from mosaic JSON first
                    job_cards = await self._extract_mosaic_data(page)
                    new_jobs_found = 0

                    if job_cards:
                        # Use JSON data
                        for card in job_cards:
                            jk = card.get("jobkey")
                            if jk and jk not in self.seen_jks:
                                self.seen_jks.add(jk)
                                job_url = f"{self.BASE_URL}/viewjob?jk={jk}"
                                job_urls.append(job_url)
                                new_jobs_found += 1
                    else:
                        # Fallback to DOM extraction
                        logger.info("Mosaic JSON not found, using DOM fallback")
                        jobs = await self._extract_jobs_from_dom(page)
                        for job in jobs:
                            jk = job.get("id")
                            if jk and jk not in self.seen_jks:
                                self.seen_jks.add(jk)
                                # Use the URL from the card if available
                                job_url = job.get(
                                    "url", f"{self.BASE_URL}/viewjob?jk={jk}"
                                )
                                job_urls.append(job_url)
                                new_jobs_found += 1

                    # Stop pagination if no new jobs found
                    if new_jobs_found == 0:
                        logger.info("No new jobs found, stopping pagination")
                        break

                    page_num += 1

            except Exception as e:
                logger.error(f"Error discovering jobs: {e}")
                # Don't raise - return partial results
            finally:
                await page.close()

        logger.info(f"Discovery complete: {len(job_urls)} total jobs found")
        return job_urls

    async def scrape_jobs_batch(self, job_urls: List[str], max_concurrent: int = 5) -> List[Job]:
        """
        Scrape multiple jobs concurrently using a batch/queue approach.
        Opens up to max_concurrent tabs at a time to avoid overwhelming the browser.
        
        Args:
            job_urls: List of job URLs to scrape
            max_concurrent: Maximum number of concurrent tabs (default 5)
            
        Returns:
            List of successfully scraped Job objects
        """
        jobs: List[Job] = []
        total = len(job_urls)
        
        logger.info(f"Starting batch scraping of {total} jobs with max {max_concurrent} concurrent tabs")
        
        # Process in batches
        for batch_start in range(0, total, max_concurrent):
            batch_end = min(batch_start + max_concurrent, total)
            batch_urls = job_urls[batch_start:batch_end]
            batch_num = (batch_start // max_concurrent) + 1
            total_batches = (total + max_concurrent - 1) // max_concurrent
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_urls)} jobs)")
            
            # Open all tabs in this batch
            pages_and_urls = []
            for url in batch_urls:
                try:
                    page = await self.context.new_page()
                    pages_and_urls.append((page, url))
                except Exception as e:
                    logger.error(f"Failed to open tab for {url}: {e}")
            
            # Navigate all tabs
            for page, url in pages_and_urls:
                try:
                    logger.info(f"Loading: {url}")
                    await page.goto(url, wait_until="domcontentloaded", timeout=settings.NAVIGATION_TIMEOUT)
                    await page.wait_for_timeout(1000)  # Let page settle
                except Exception as e:
                    logger.error(f"Failed to navigate to {url}: {e}")
            
            # Extract data from all tabs
            for page, url in pages_and_urls:
                try:
                    # Check for bot detection
                    if await self._detect_bot_challenge(page):
                        logger.warning(f"Bot challenge detected for {url}")
                        await page.close()
                        continue
                    
                    # Extract job data using simplified approach
                    job = await self._extract_job_from_page(page, url)
                    if job:
                        jobs.append(job)
                        logger.info(f"✓ Scraped: {job.title} at {job.company}")
                    
                except Exception as e:
                    logger.error(f"Failed to extract job from {url}: {e}")
                finally:
                    await page.close()
            
            logger.info(f"Batch {batch_num}/{total_batches} complete. Total scraped: {len(jobs)}")
        
        logger.info(f"Batch scraping complete: {len(jobs)}/{total} jobs successfully scraped")
        return jobs

    async def _extract_job_from_page(self, page: Page, url: str) -> Optional[Job]:
        """
        Extract job data from an already-loaded job detail page.
        Uses #jobDescriptionText as the primary selector.
        
        Args:
            page: Already navigated page object
            url: Job URL for reference
            
        Returns:
            Job object or None if extraction fails
        """
        try:
            # Extract job ID from URL
            parsed_url = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed_url.query)
            job_id = qs.get("jk", ["unknown"])[0]
            
            # Try JSON-LD extraction first (best source of structured data)
            json_ld = await self._extract_json_ld(page)
            
            # Extract core fields
            title = await self._extract_title(page, json_ld)
            company = await self._extract_company(page, json_ld)
            location = await self._extract_location(page, json_ld)
            salary = await self._extract_salary(page, json_ld)
            
            # Extract description using #jobDescriptionText selector
            description = ""
            try:
                desc_element = page.locator("#jobDescriptionText")
                if await desc_element.count() > 0:
                    description = await desc_element.inner_text()
                    logger.debug(f"Extracted description ({len(description)} chars)")
                else:
                    # Fallback to JSON-LD
                    if json_ld and "description" in json_ld:
                        description = json_ld["description"]
                        logger.debug("Used JSON-LD description")
            except Exception as e:
                logger.warning(f"Failed to extract description: {e}")
            
            # Extract posted date from JSON-LD if available
            posted_at = None
            if json_ld and "datePosted" in json_ld:
                posted_at = json_ld["datePosted"]
            
            # Validate required fields
            if title.startswith("Unknown") or job_id == "unknown":
                logger.warning(f"Missing critical fields for {url}")
                return None
            
            job = Job(
                id=job_id,
                title=title,
                company=company,
                location=location,
                description=description,
                source="indeed",
                url=url,
                salary=salary,
                posted_at=posted_at,
            )
            
            return job
            
        except Exception as e:
            logger.error(f"Error extracting job from page: {e}")
            return None

    async def _extract_json_ld(self, page: Page) -> Optional[Dict[str, Any]]:
        """
        Extract JSON-LD structured data from script tag.
        JSON-LD is stable W3C standard used for SEO.
        """
        try:
            scripts = await page.locator('script[type="application/ld+json"]').all()
            for script in scripts:
                content = await script.inner_text()
                try:
                    data = json.loads(content)
                    # Check if it's a JobPosting schema
                    if isinstance(data, dict) and data.get("@type") == "JobPosting":
                        return data
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.warning(f"Failed to extract JSON-LD: {e}")
        return None

    async def _safe_extract(
        self, page: Page, selectors: List[str], field_name: str
    ) -> str:
        """
        Try multiple selectors in order, return first match or 'Unknown'.
        Handles both CSS and XPath selectors.
        """
        for selector in selectors:
            try:
                if selector.startswith("//") or selector.startswith("xpath="):
                    if not selector.startswith("xpath="):
                        selector = f"xpath={selector}"
                    loc = page.locator(selector)
                else:
                    loc = page.locator(selector)

                if await loc.count() > 0:
                    text = await loc.first.inner_text()
                    if text and text.strip():
                        return text.strip()
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed for {field_name}: {e}")
                continue

        logger.warning(f"All selectors failed for {field_name}")
        return f"Unknown {field_name.title()}"

    async def _extract_title(self, page: Page, json_ld: Optional[Dict] = None) -> str:
        """Extract title from JSON-LD or stable CSS selectors"""
        if json_ld and "title" in json_ld:
            return json_ld["title"]

        selectors = [
            'h2[data-testid*="jobsearch-JobInfoHeader-title"] span',
            'h1[class*="jobsearch-JobInfoHeader-title"]',
            "h2.jobsearch-JobInfoHeader-title span",
        ]
        return await self._safe_extract(page, selectors, "title")

    async def _extract_company(self, page: Page, json_ld: Optional[Dict] = None) -> str:
        """Extract company from JSON-LD or stable CSS selectors"""
        if json_ld and "hiringOrganization" in json_ld:
            org = json_ld["hiringOrganization"]
            if isinstance(org, dict) and "name" in org:
                return org["name"]

        selectors = [
            "div[data-company-name]",
            'a[data-tn-element="companyName"]',
            'span[class*="companyName"] a',
            "div.jobsearch-InlineCompanyRating div",
        ]
        return await self._safe_extract(page, selectors, "company")

    async def _extract_location(
        self, page: Page, json_ld: Optional[Dict] = None
    ) -> str:
        """Extract location from JSON-LD or stable CSS selectors"""
        if json_ld and "jobLocation" in json_ld:
            loc = json_ld["jobLocation"]
            if isinstance(loc, dict) and "address" in loc:
                addr = loc["address"]
                if isinstance(addr, dict):
                    city = addr.get("addressLocality", "")
                    region = addr.get("addressRegion", "")
                    return f"{city}, {region}".strip(", ")

        selectors = [
            'div[data-testid*="location"]',
            'div[class*="jobsearch-JobInfoHeader-subtitle"] div',
            "div.jobsearch-JobInfoHeader-subtitle div",
        ]
        return await self._safe_extract(page, selectors, "location")

    async def _extract_description(
        self, page: Page, json_ld: Optional[Dict] = None
    ) -> str:
        """Extract description from JSON-LD or stable ID selector"""
        if json_ld and "description" in json_ld:
            return json_ld["description"]

        try:
            # #jobDescriptionText is stable ID that rarely changes
            container = page.locator("div#jobDescriptionText")
            if await container.count() > 0:
                return await container.inner_text()
        except Exception as e:
            logger.warning(f"Failed to extract description: {e}")

        return ""

    async def _extract_salary(
        self, page: Page, json_ld: Optional[Dict] = None
    ) -> Optional[str]:
        """Extract salary from JSON-LD or text pattern matching"""
        if json_ld and "baseSalary" in json_ld:
            salary = json_ld["baseSalary"]
            if isinstance(salary, dict):
                value = salary.get("value", {})
                if isinstance(value, dict):
                    min_val = value.get("minValue")
                    max_val = value.get("maxValue")
                    currency = value.get("currency", "")
                    if min_val and max_val:
                        return f"{currency}{min_val} - {currency}{max_val}"

        # Pattern match for salary text (e.g., "$50,000 - $80,000" or "₹20,000 - ₹30,000")
        try:
            html = await page.content()
            # Match currency symbols followed by numbers
            patterns = [
                r"[$₹€£¥]\s*[\d,]+(?:\.\d{2})?\s*-\s*[$₹€£¥]\s*[\d,]+(?:\.\d{2})?",
                r"[\d,]+(?:\.\d{2})?\s*-\s*[\d,]+(?:\.\d{2})?\s*(?:per|/)\s*(?:month|year|hour)",
            ]
            for pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    return match.group(0)
        except Exception as e:
            logger.debug(f"Salary pattern matching failed: {e}")

        return None

    @with_retry()
    async def scrape_job(self, url: str) -> Job:
        """
        Scrape job details using JSON-LD first, CSS selectors as fallback.
        Never crashes - returns partial data with warnings.
        """
        async with page_limiter:
            page = await self.context.new_page()
            try:
                logger.info(f"Scraping job: {url}")
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=settings.NAVIGATION_TIMEOUT,
                )

                # Check for bot detection
                if await self._detect_bot_challenge(page):
                    logger.error(f"Bot challenge detected for {url}")
                    raise Exception("Bot detection triggered")

                # Try JSON-LD extraction first
                json_ld = await self._extract_json_ld(page)
                if json_ld:
                    logger.info("Successfully extracted JSON-LD data")

                # Extract all fields with fallbacks
                title = await self._extract_title(page, json_ld)
                company = await self._extract_company(page, json_ld)
                location = await self._extract_location(page, json_ld)
                description = await self._extract_description(page, json_ld)
                salary = await self._extract_salary(page, json_ld)

                # Extract posted date from JSON-LD if available
                posted_at = None
                if json_ld and "datePosted" in json_ld:
                    posted_at = json_ld["datePosted"]

                # Extract job ID from URL
                parsed_url = urllib.parse.urlparse(url)
                qs = urllib.parse.parse_qs(parsed_url.query)
                job_id = qs.get("jk", ["unknown"])[0]

                # Skip if critical fields are missing
                if title.startswith("Unknown") or job_id == "unknown":
                    logger.warning(f"Skipping job {url}: missing critical fields")
                    raise Exception("Missing critical job fields")

                job = Job(
                    id=job_id,
                    title=title,
                    company=company,
                    location=location,
                    description=description,
                    source="indeed",
                    url=url,
                    salary=salary,
                    posted_at=posted_at,
                )

                return job

            except Exception as e:
                logger.error(f"Error scraping job {url}: {e}")
                raise
            finally:
                await page.close()
