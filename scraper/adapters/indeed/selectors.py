"""
All CSS, XPath, and data-attribute selectors used by the Indeed adapter.
Centralized here so that selector changes only need to happen in one place.
"""

# --- SERP (Search Results Page) Selectors ---

# Homepage Search Selectors
WHAT_INPUT_SELECTOR = "#text-input-what"
WHERE_INPUT_SELECTOR = "#text-input-where"
FIND_JOBS_BUTTON_SELECTOR = "#jobsearch > div > div.css-1m0ipk7.eu4oa1w0 > button"

# Job card container selectors - tried in order during DOM extraction
SERP_CARD_SELECTORS = [
    # Deep selector for table-based layout matches user provided structure
    "#mosaic-provider-jobcards > div > ul > li > div > div > div > div.slider_item.css-17bghu4.eu4oa1w0 > div > div > table > tbody > tr > td",
    "#mosaic-provider-jobcards ul li div.slider_item",  # Specific slider item for Indeed India
    "#mosaic-provider-jobcards ul li",  # Generic list item fallback
]

# Job link with job key attribute
JOB_LINK_SELECTOR = "a[data-jk]"

# Job title from span with title attribute
JOB_TITLE_SPAN_SELECTOR = "span[title]"

# Company name
COMPANY_NAME_SELECTOR = '[data-testid="company-name"]'

# Location
LOCATION_SELECTOR = '[data-testid="text-location"]'

# Job cards container (for bot detection check)
JOB_CARDS_CONTAINER_SELECTOR = "#mosaic-provider-jobcards"

# --- CAPTCHA / Bot Detection Selectors ---

CAPTCHA_SELECTORS = [
    'iframe[src*="hcaptcha"]',
    'iframe[src*="recaptcha"]',
    'div[class*="captcha"]',
    'div[id*="captcha"]',
    "#px-captcha",
    ".g-recaptcha",
]

# Bot-blocking keywords (checked in page HTML)
BLOCKING_KEYWORDS = [
    "security check",
    "verify you're human",
    "access denied",
    "blocked",
]

# --- Job Detail Page Selectors ---

# Title selectors (tried in order)
TITLE_SELECTORS = [
    'h2[data-testid*="jobsearch-JobInfoHeader-title"] span',
    'h1[class*="jobsearch-JobInfoHeader-title"]',
    "h2.jobsearch-JobInfoHeader-title span",
]

# Company selectors (tried in order)
COMPANY_SELECTORS = [
    "div[data-company-name]",
    'a[data-tn-element="companyName"]',
    'span[class*="companyName"] a',
    "div.jobsearch-InlineCompanyRating div",
]

# Location selectors (tried in order)
LOCATION_DETAIL_SELECTORS = [
    'div[data-testid*="location"]',
    'div[class*="jobsearch-JobInfoHeader-subtitle"] div',
    "div.jobsearch-JobInfoHeader-subtitle div",
]

# Description selector (stable ID)
DESCRIPTION_SELECTOR = "div#jobDescriptionText"
DESCRIPTION_SELECTOR_ALT = "#jobDescriptionText"

# JSON-LD script selector
JSON_LD_SELECTOR = 'script[type="application/ld+json"]'

# --- Salary Extraction Patterns ---

# Regex patterns for salary text matching
SALARY_PATTERNS = [
    r"[$₹€£¥]\s*[\d,]+(?:\.\d{2})?\s*-\s*[$₹€£¥]\s*[\d,]+(?:\.\d{2})?",
    r"[\d,]+(?:\.\d{2})?\s*-\s*[\d,]+(?:\.\d{2})?\s*(?:per|/)\s*(?:month|year|hour)",
]
