import asyncio
import os
import sys
from playwright.async_api import async_playwright

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scraper.adapters.indeed import IndeedAdapter
from scraper.core.browser import BrowserManager


async def test_local_mock():
    """Test extraction on local mock HTML file"""
    print("\n=== Testing with Live Indeed Page ===")
    
    # Initialize BrowserManager
    await BrowserManager.initialize()
    page = await BrowserManager.new_page()

    try:
        # file_path = f"file://{cwd}/tests/mock_indeed.html"
        file_path = f"https://in.indeed.com/jobs?q=ai+engineer&l=Gurugram%2C+Haryana&radius=25&from=searchOnDesktopSerp%2Cwhatautocomplete%2CwhatautocompleteSourceStandard%2Cwhereautocomplete&vjk=77bb2acfef0cea88"
        print(f"Loading {file_path}")
        await page.goto(file_path)

        adapter = IndeedAdapter(context=None)

        # Test JSON-LD extraction
        json_ld = await adapter._extract_json_ld(page)
        print(f"JSON-LD extracted: {json_ld is not None}")

        # Test field extraction methods
        print("-" * 40)
        title = await adapter._extract_title(page, json_ld)
        print(f"Title: {title}")

        company = await adapter._extract_company(page, json_ld)
        print(f"Company: {company}")

        location = await adapter._extract_location(page, json_ld)
        print(f"Location: {location}")

        salary = await adapter._extract_salary(page, json_ld)
        print(f"Salary: {salary}")

        description = await adapter._extract_description(page, json_ld)
        print(f"Description (len={len(description)}): {description[:100]}...")

    except Exception as e:
        print(f"Error during test: {e}")
        # Save screenshot for debugging
        await page.screenshot(path="debug_screenshot.png")
    finally:
        await BrowserManager.close()


async def test_live_indeed():
    """Test extraction on live Indeed page (may trigger bot detection)"""
    print("\n=== Testing with Live Indeed Page ===")
     # Initialize BrowserManager
    await BrowserManager.initialize()
    page = await BrowserManager.new_page()

    # Test URL - job detail page
    url = "https://in.indeed.com/jobs?q=&l=Gurugram%2C+Haryana&from=searchOnHP"
    print(f"Loading {url}")
    print("NOTE: This may trigger bot detection and fail gracefully")

    try:
        await page.goto(url, timeout=30000)

        # Save debug artifacts
        print("Saving debug artifacts...")
        await page.screenshot(path="debug_screenshot.png")
        content = await page.content()
        with open("debug_page.html", "w") as f:
            f.write(content)
        print("Saved debug_screenshot.png and debug_page.html")

        adapter = IndeedAdapter(context=None)

        # Check bot detection
        is_challenge = await adapter._detect_bot_challenge(page)
        print(f"Bot challenge detected: {is_challenge}")

        if not is_challenge:
            # Test JSON-LD extraction
            json_ld = await adapter._extract_json_ld(page)
            print(f"JSON-LD extracted: {json_ld is not None}")

            if json_ld:
                print(f"JSON-LD fields: {list(json_ld.keys())}")

    except Exception as e:
        print(f"Expected error (likely bot detection): {e}")

    await BrowserManager.close()


async def test_scroll_loading():
    """Test that scrolling loads all job cards on the search results page"""
    print("\n=== Testing Scroll Functionality ===")
    
    await BrowserManager.initialize()
    page = await BrowserManager.new_page()
    
    # Search results URL
    url = "https://in.indeed.com/jobs?q=software+engineer&l=Delhi"
    print(f"Loading {url}")
    
    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        
        # Add delay to let page settle
        print("Waiting for page to settle...")
        await page.wait_for_timeout(2000)
        
        # Save initial state
        print("Saving initial state...")
        await page.screenshot(path="debug_scroll_before.png")
        
        adapter = IndeedAdapter(context=None, query="software engineer", location="Delhi")
        
        # Check bot detection
        is_challenge = await adapter._detect_bot_challenge(page)
        if is_challenge:
            print("❌ Bot challenge detected - test cannot proceed")
            await page.screenshot(path="debug_bot_challenge.png")
            return
        else:
            print("✅ No bot detection - page loaded successfully!")
        
        # Get initial metrics
        initial_height = await page.evaluate("document.body.scrollHeight")
        initial_position = await page.evaluate("window.pageYOffset")
        
        # Count job cards before scroll
        initial_cards = await page.locator("#mosaic-provider-jobcards ul li").count()
        print(f"Initial scroll height: {initial_height}px")
        print(f"Initial position: {initial_position}px")
        print(f"Initial job cards visible: {initial_cards}")
        
        # Perform scroll
        print("\n🔄 Starting slow scroll...")
        await adapter._scroll_to_load_all_jobs(page)
        
        # Get metrics after scroll
        final_height = await page.evaluate("document.body.scrollHeight")
        final_position = await page.evaluate("window.pageYOffset")
        final_cards = await page.locator("#mosaic-provider-jobcards ul li").count()
        
        print(f"\nFinal scroll height: {final_height}px")
        print(f"Final position (should be ~0, scrolled back to top): {final_position}px")
        print(f"Final job cards visible: {final_cards}")
        
        # Save final state
        print("\nSaving final state...")
        await page.screenshot(path="debug_scroll_after.png")
        content = await page.content()
        with open("debug_scroll_page.html", "w") as f:
            f.write(content)
        
        # Verify results
        print("\n" + "=" * 50)
        print("📊 SCROLL TEST RESULTS:")
        print("=" * 50)
        print(f"✓ Page height changed: {initial_height} → {final_height} ({final_height - initial_height:+}px)")
        print(f"✓ Job cards loaded: {initial_cards} → {final_cards} ({final_cards - initial_cards:+} new cards)")
        print(f"✓ Scrolled back to top: {final_position}px")
        print(f"\n📁 Debug files saved:")
        print(f"  - debug_scroll_before.png (initial state)")
        print(f"  - debug_scroll_after.png (after scroll)")
        print(f"  - debug_scroll_page.html (final HTML)")
        
        if final_cards > initial_cards:
            print(f"\n✅ SUCCESS: Loaded {final_cards - initial_cards} additional job cards!")
        else:
            print(f"\n⚠️  WARNING: No new cards loaded (page may have been fully loaded initially)")
        
        # Also test the DOM extraction to see what we got
        print("\n" + "=" * 50)
        print("📋 TESTING JOB EXTRACTION:")
        print("=" * 50)
        jobs = await adapter._extract_jobs_from_dom(page)
        print(f"Total jobs extracted: {len(jobs)}")
        
        if jobs:
            print("\nFirst 3 jobs:")
            for i, job in enumerate(jobs[:len(jobs)], 1):
                print(f"\n  Job {i}:")
                print(f"    ID: {job.get('id', 'N/A')}")
                print(f"    Title: {job.get('title', 'N/A')}")
                print(f"    Company: {job.get('company', 'N/A')}")
                print(f"    Location: {job.get('location', 'N/A')}")
                print(f"    URL: {job.get('url', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error during scroll test: {e}")
        import traceback
        traceback.print_exc()
        
        # Save error state
        await page.screenshot(path="debug_scroll_error.png")
        
    finally:
        await BrowserManager.close()


async def test_full_job_scraping_flow():
    """Test the complete flow: scroll + extract URLs + visit job pages in batches"""
    print("\n" + "=" * 60)
    print("🚀 TESTING FULL JOB SCRAPING FLOW")
    print("=" * 60)
    
    await BrowserManager.initialize()
    context = await BrowserManager.get_context()
    
    adapter = IndeedAdapter(context=context, query="software engineer", location="Delhi")
    
    try:
        # Step 1: Discover job URLs (includes scrolling)
        print("\n📄 STEP 1: Discovering jobs (loading + scrolling + extracting)...")
        job_urls = await adapter.discover_jobs()
        print(f"✅ Found {len(job_urls)} job URLs")
        
        if not job_urls:
            print("❌ No jobs found - stopping test")
            return
        
        # Step 2: Scrape first 5 jobs in batch
        print(f"\n🌐 STEP 2: Scraping first 5 jobs in batch...")
        jobs_to_scrape = job_urls[:5]
        
        jobs = await adapter.scrape_jobs_batch(jobs_to_scrape, max_concurrent=5)
        
        # Step 3: Display results
        print(f"\n{'=' * 60}")
        print(f"📊 RESULTS:")
        print(f"{'=' * 60}")
        print(f"Total jobs discovered: {len(job_urls)}")
        print(f"Jobs scraped: {len(jobs)}")
        print(f"\n{'─' * 60}")
        
        for i, job in enumerate(jobs, 1):
            print(f"\n📋 Job {i}:")
            print(f"  🏷️  ID: {job.id}")
            print(f"  💼 Title: {job.title}")
            print(f"  🏢 Company: {job.company}")
            print(f"  📍 Location: {job.location}")
            print(f"  💰 Salary: {job.salary or 'N/A'}")
            print(f"  🔗 URL: {job.url}")
            
            desc_preview = job.description[:150].replace('\n', ' ').strip() if job.description else "N/A"
            print(f"  📝 Description: {desc_preview}...")
            
            # Save to file
            with open(f"debug_job_{i}_scraped.txt", "w") as f:
                f.write(f"Job ID: {job.id}\n")
                f.write(f"Title: {job.title}\n")
                f.write(f"Company: {job.company}\n")
                f.write(f"Location: {job.location}\n")
                f.write(f"Salary: {job.salary or 'N/A'}\n")
                f.write(f"Posted: {job.posted_at or 'N/A'}\n")
                f.write(f"URL: {job.url}\n")
                f.write(f"\n{'=' * 60}\n")
                f.write(f"DESCRIPTION:\n")
                f.write(f"{'=' * 60}\n\n")
                f.write(job.description or "No description")
            print(f"  💾 Saved: debug_job_{i}_scraped.txt")
        
        print(f"\n{'=' * 60}")
        print(f"✅ TEST COMPLETE")
        print(f"{'=' * 60}")
        
    except Exception as e:
        print(f"\n❌ Error in full flow test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await BrowserManager.close()


async def main():
    # Test with local mock first (should always work)
    # await test_local_mock()

    # Optionally test with live page (may fail due to bot detection)
    # await test_live_indeed()
    
    # Test scrolling functionality only
    # await test_scroll_loading()
    
    # Test complete flow: scroll + extract + visit job pages
    await test_full_job_scraping_flow()


if __name__ == "__main__":
    asyncio.run(main())
