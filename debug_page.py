"""Debug script to save page HTML for analysis."""
import asyncio
from scraper import ScholarshipScraper


async def save_page_html():
    """Save the page HTML to inspect the structure."""
    async with ScholarshipScraper() as scraper:
        url = "https://scholarshipdb.net/phd-scholarships/"

        print(f"Navigating to {url}...")
        success = await scraper.navigate_with_retry(url)

        if not success:
            print("Failed to navigate")
            return

        print("Saving page HTML...")
        content = await scraper.page.content()

        with open('phd_page.html', 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✓ Saved to phd_page.html ({len(content)} bytes)")

        # Also save a screenshot
        print("Taking screenshot...")
        await scraper.page.screenshot(path='phd_page.png', full_page=True)
        print("✓ Saved screenshot to phd_page.png")

        # Print some page info
        title = await scraper.page.title()
        print(f"\nPage title: {title}")
        print(f"Current URL: {scraper.page.url}")


if __name__ == "__main__":
    asyncio.run(save_page_html())
