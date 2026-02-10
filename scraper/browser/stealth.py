import logging
from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)


async def apply_stealth_scripts(context: BrowserContext, user_agent: str):
    """
    Apply stealth init scripts to the browser context to avoid bot detection.
    Overrides navigator properties, hides webdriver, spoofs plugins, etc.
    """
    # Enhanced stealth: Override multiple navigator properties to avoid detection
    platform = (
        "Win32"
        if "Windows" in user_agent
        else "MacIntel"
        if "Mac" in user_agent
        else "Linux x86_64"
    )
    await context.add_init_script(f"""
        // Override navigator properties
        Object.defineProperty(navigator, 'platform', {{
            get: () => '{platform}'
        }});
        
        // Hide webdriver property
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined
        }});
        
        // Remove automation flags
        delete navigator.__proto__.webdriver;
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({{ state: Notification.permission }}) :
                originalQuery(parameters)
        );
        
        // Plugin spoofing
        Object.defineProperty(navigator, 'plugins', {{
            get: () => [
                {{
                    0: {{type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"}},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                }},
                {{
                    0: {{type: "application/pdf", suffixes: "pdf", description: ""}},
                    description: "",
                    filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                    length: 1,
                    name: "Chrome PDF Viewer"
                }},
                {{
                    0: {{type: "application/x-nacl", suffixes: "", description: "Native Client Executable"}},
                    description: "Native Client Executable",
                    filename: "internal-nacl-plugin",
                    length: 2,
                    name: "Native Client"
                }}
            ]
        }});
        
        // Languages
        Object.defineProperty(navigator, 'languages', {{
            get: () => ['en-US', 'en']
        }});
        
        // Chrome runtime
        window.chrome = {{
            runtime: {{}}
        }};
        
        // Screen properties
        Object.defineProperty(window.screen, 'availWidth', {{
            get: () => 1366
        }});
        Object.defineProperty(window.screen, 'availHeight', {{
            get: () => 768
        }});
    """)

    logger.info("Browser context created with stealth settings.")
