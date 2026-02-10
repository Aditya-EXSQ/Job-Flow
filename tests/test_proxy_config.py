#!/usr/bin/env python3
"""
Quick test script to verify proxy configuration system.
Tests different proxy providers and configuration scenarios.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_proxy_config():
    """Test the proxy configuration with different providers."""
    from scraper.config.settings import settings
    from scraper.browser.proxy import get_proxy_config, PROXY_PROVIDERS

    print("=" * 60)
    print("Proxy Configuration System Test")
    print("=" * 60)

    print(f"\n📋 Available Providers: {', '.join(PROXY_PROVIDERS.keys())}")
    print(f"\n🔧 Current Configuration:")
    print(f"   PROXY_PROVIDER: {settings.PROXY_PROVIDER}")
    print(
        f"   SCRAPERAPI_API_KEY: {'✓ Set' if settings.SCRAPERAPI_API_KEY else '✗ Not set'}"
    )
    print(
        f"   SCRAPEOPS_API_KEY: {'✓ Set' if settings.SCRAPEOPS_API_KEY else '✗ Not set'}"
    )
    print(f"   PROXY_SERVER: {settings.PROXY_SERVER or '✗ Not set'}")

    print(f"\n🚀 Testing get_proxy_config()...")
    config = get_proxy_config()

    if config:
        print(f"\n✅ Proxy configured successfully!")
        print(f"   Server: {config.get('server')}")
        print(f"   Username: {config.get('username')}")
        print(f"   Password: {'*' * 8 if config.get('password') else 'None'}")
    else:
        print(f"\n⚠️  No proxy configured (provider: {settings.PROXY_PROVIDER})")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

    # Test switching providers
    print("\n💡 To switch providers, update PROXY_PROVIDER in .env:")
    print("   - PROXY_PROVIDER=scraperapi  (recommended)")
    print("   - PROXY_PROVIDER=scrapeops")
    print("   - PROXY_PROVIDER=generic")
    print("   - PROXY_PROVIDER=none")
    print()


if __name__ == "__main__":
    test_proxy_config()
