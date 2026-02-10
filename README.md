# Job-Flow

A Python-based job scraping tool that automates discovery and extraction of job postings from Indeed using Playwright browser automation with advanced anti-detection techniques.

## Features

- **Stealth Browser Automation**: Playwright with anti-detection measures (user-agent rotation, webdriver masking, plugin spoofing)
- **Multi-Layer Extraction**: JSON-LD structured data → embedded JSON → CSS selectors
- **Resilient Scraping**: Exponential backoff retries, rate limiting, bot detection handling
- **Proxy Support**: Multiple proxy providers (ScraperAPI, ScrapeOps, generic HTTP/SOCKS) with easy switching
- **Modular Architecture**: Clean separation of concerns with adapter pattern for multiple job portals

## Architecture

```
scraper/
├── browser/          # Browser management & anti-detection
├── adapters/         # Job portal adapters (currently: Indeed)
│   ├── base.py      # Abstract adapter interface
│   └── indeed/      # Indeed-specific implementation
├── core/            # Orchestration, models, rate limiting
├── config/          # Settings via pydantic-settings
└── main.py          # Entry point
```

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Job-Flow
   ```

2. **Create virtual environment and install dependencies**
   
   Using `uv` (recommended):
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e .
   ```
   
   Or using pip:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

3. **Install Playwright browsers**
   ```bash
   playwright install chromium
   ```

4. **Configure environment variables** (optional)
   
   Create a `.env` file in the project root:
   ```env
   # Optional: ScrapeOps proxy API key for IP rotation
   SCRAPEOPS_API_KEY=your_api_key_here
   
   # Browser settings
   HEADLESS=False  # Set to True for headless mode
   ```

## Usage

### Basic Usage

Run the scraper with default settings (searches for "python developer" in "Remote"):

```bash
python -m scraper.main
```

### Custom Search

Edit `scraper/main.py` to customize the search:

```python
async def main():
    portal = "indeed"
    query = "data scientist"      # Your search query
    location = "New York, NY"     # Your location
    
    await runner.run(portal=portal, query=query, location=location)
```

Then run:
```bash
python -m scraper.main
```

### Running Tests

**DOM Extraction Test** (works offline with mock HTML):
```bash
python tests/test_dom_extraction.py
```

**Live Indeed Test** (requires internet, may trigger bot detection):
```bash
python tests/test_indeed_extraction.py
```

**Proxy Rotation Test**:
```bash
python tests/test_proxy_rotation.py
```

## Configuration

All settings are in `scraper/config/settings.py` and can be overridden via `.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `HEADLESS` | `False` | Run browser in headless mode |
| `PROXY_PROVIDER` | `none` | Proxy provider: `none`, `scrapeops`, `scraperapi`, `generic` |
| `MAX_CONCURRENT_PAGES` | `5` | Max concurrent job detail tabs |
| `MAX_CONCURRENT_SERP` | `1` | Max concurrent search result pages |
| `MAX_RETRIES` | `3` | Retry attempts on failure |
| `NAVIGATION_TIMEOUT` | `30000` | Page load timeout (ms) |

### Proxy Configuration

Job-Flow supports multiple proxy providers to help bypass rate limits and anti-scraping measures. Switch between providers by changing the `PROXY_PROVIDER` environment variable.

**Supported Providers:**

| Provider | Type | Setup |
|----------|------|-------|
| `none` | No proxy | Default, no configuration needed |
| `scraperapi` | Premium | Requires API key from [scraperapi.com](https://www.scraperapi.com/) |
| `scrapeops` | Premium | Requires API key from [scrapeops.io](https://scrapeops.io/) |
| `generic` | Any HTTP/SOCKS | Works with free proxy lists or custom proxies |

**Quick Setup Examples:**

```bash
# Use ScraperAPI (recommended)
PROXY_PROVIDER=scraperapi
SCRAPERAPI_API_KEY=your_api_key_here

# Use ScrapeOps
PROXY_PROVIDER=scrapeops
SCRAPEOPS_API_KEY=your_api_key_here

# Use a free/custom proxy
PROXY_PROVIDER=generic
PROXY_SERVER=http://proxy.example.com:8080
PROXY_USERNAME=optional_username  # if authentication required
PROXY_PASSWORD=optional_password

# Disable proxy
PROXY_PROVIDER=none
```

**Adding Custom Providers:**

Create a new provider class in `scraper/browser/proxy.py`:

```python
class MyProxyProvider(ProxyProvider):
    def get_config(self) -> Optional[Dict[str, str]]:
        return {
            "server": "http://my-proxy.com:8080",
            "username": "user",
            "password": settings.MY_PROXY_API_KEY,
        }
    
    def get_name(self) -> str:
        return "My Proxy"

# Register in PROXY_PROVIDERS dict
PROXY_PROVIDERS["myproxy"] = MyProxyProvider
```

See `.env.example` for all configuration options.

## How It Works

1. **Discovery Phase**
   - Navigates to Indeed search results
   - Scrolls to trigger lazy loading
   - Extracts job URLs from `window.mosaic.providerData` JSON or DOM

2. **Scraping Phase**
   - Opens individual job detail pages
   - Extracts structured data from JSON-LD schema
   - Falls back to CSS selectors if needed
   - Handles bot detection and retries

3. **Output**
   - Currently prints to stdout
   - Ready for database/file persistence (see `runner.py` comment)

## Project Structure

```
Job-Flow/
├── scraper/
│   ├── browser/              # Browser management
│   │   ├── manager.py        # BrowserManager singleton
│   │   ├── stealth.py        # Anti-detection scripts
│   │   ├── proxy.py          # Proxy configuration
│   │   └── ...
│   ├── adapters/
│   │   ├── base.py           # Abstract adapter interface
│   │   └── indeed/           # Indeed adapter
│   │       ├── adapter.py    # Main adapter class
│   │       ├── discovery.py  # Job URL discovery
│   │       ├── scraping.py   # Job detail extraction
│   │       ├── extraction/   # Extraction strategies
│   │       └── ...
│   ├── core/
│   │   ├── runner.py         # Orchestration
│   │   ├── models.py         # Job dataclass
│   │   └── rate_limit.py     # Rate limiting & retries
│   ├── config/
│   │   └── settings.py       # Configuration
│   └── main.py               # Entry point
├── tests/                    # Test scripts
├── .env                      # Environment variables (create this)
├── pyproject.toml            # Dependencies
└── README.md
```

## Adding New Job Portals

To add support for a new job portal:

1. Create a new adapter in `scraper/adapters/your_portal/`
2. Implement `JobPortalAdapter` interface:
   - `discover_jobs()` - return list of job URLs
   - `scrape_job(url)` - return `Job` object
3. Register in `scraper/core/runner.py`:
   ```python
   ADAPTERS = {
       "indeed": IndeedAdapter,
       "your_portal": YourPortalAdapter,  # Add here
   }
   ```

## Troubleshooting

**Bot Detection**: Indeed may block requests. Solutions:
- Configure a proxy provider (see Proxy Configuration section)
- Use `PROXY_PROVIDER=scraperapi` or `PROXY_PROVIDER=scrapeops` for best results
- Reduce `MAX_CONCURRENT_PAGES` to 1
- Increase delays in `rate_limit.py`

**Import Errors**: Clear cached bytecode:
```bash
find . -type d -name __pycache__ -exec rm -rf {} +
```

**Playwright Errors**: Reinstall browsers:
```bash
playwright install --force chromium
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
