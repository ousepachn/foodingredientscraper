from typing import List, Optional
from playwright.async_api import Browser, Page
import logging
from datetime import datetime
import json
from pathlib import Path


class ProductUrlScraper:
    """Scraper for collecting Trader Joe's product URLs"""

    def __init__(
        self, headless: bool = True, timeout: int = 30000, max_pages: int = None
    ):
        """Initialize scraper with configuration"""
        self.headless = headless
        self.timeout = timeout
        self.max_pages = max_pages

        # Set up logging with more detailed format
        self.logger = logging.getLogger("product_url_scraper")
        self.logger.setLevel(logging.DEBUG)  # Set to DEBUG level for more detailed logs

        # Create console handler with a higher log level
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Create file handler which logs even debug messages
        file_handler = logging.FileHandler("logs/product_url_scraper.log")
        file_handler.setLevel(logging.DEBUG)

        # Create formatter and add it to the handlers
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Add the handlers to the logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    async def scrape_category(self, category_url: str) -> List[str]:
        """Scrape all product URLs from a category page"""
        product_urls = []
        page = None
        current_page = 1

        try:
            async with await self._launch_browser() as browser:
                page = await self.setup_page(browser)
                current_url = category_url

                while current_url:
                    self.logger.info(f"Scraping page {current_page}: {current_url}")

                    # Check if we've reached the maximum number of pages
                    if self.max_pages and current_page > self.max_pages:
                        self.logger.info(
                            f"Reached maximum page limit of {self.max_pages}"
                        )
                        break

                    # Navigate to the page
                    await page.goto(current_url, wait_until="networkidle")
                    await page.wait_for_load_state("domcontentloaded")

                    # Extract product URLs from current page
                    page_urls = await self._extract_product_urls(page)
                    product_urls.extend(page_urls)

                    # Get next page URL
                    current_url = await self._get_next_page_url(page)
                    current_page += 1

                    if current_url:
                        self.logger.info(f"Found next page: {current_url}")
                    else:
                        self.logger.info("No more pages to scrape")

                return product_urls

        except Exception as e:
            self.logger.error(f"Error scraping category: {str(e)}")
            return product_urls

    async def _extract_product_urls(self, page: Page) -> List[str]:
        """Extract product URLs from the current page"""
        try:
            # Wait for the product list container to load
            await page.wait_for_selector(
                'ul[class*="ProductList_productList__list"]', timeout=10000
            )

            # Get all product links within the product list
            product_links = await page.query_selector_all(
                'ul[class*="ProductList_productList__list"] a[class*="ProductCard_card__title"]'
            )

            urls = []
            for link in product_links:
                href = await link.get_attribute("href")
                text = await link.text_content()
                if href:
                    # Convert relative URL to absolute URL
                    full_url = f"https://www.traderjoes.com{href}"
                    urls.append(full_url)
                    self.logger.debug(f"Found product: {text} - {full_url}")

            self.logger.info(f"Found {len(urls)} product URLs on current page")
            return urls

        except Exception as e:
            self.logger.error(f"Error extracting product URLs: {str(e)}")
            return []

    async def _get_next_page_url(self, page: Page) -> Optional[str]:
        """Get the URL of the next page if it exists"""
        try:
            # Wait for pagination container
            await page.wait_for_selector(
                'div[class*="Pagination_pagination__"]', timeout=5000
            )

            # Check if there's a next page button that's not disabled
            next_button = await page.query_selector(
                'button[class*="Pagination_pagination__arrow__"]:not([disabled])'
            )

            if next_button:
                # Get all pagination items
                pagination_items = await page.query_selector_all(
                    'li[class*="PaginationItem_paginationItem__"]'
                )

                # Find the currently selected page
                current_page = None
                for item in pagination_items:
                    if await item.get_attribute("aria-current") == "page":
                        current_page = item
                        break

                if current_page:
                    # Get the text content and clean it
                    current_page_text = await current_page.text_content()
                    # Remove 'page' and any special characters, then strip whitespace
                    current_page_num = current_page_text.replace("page", "").strip()
                    self.logger.debug(
                        f"Current page text: {current_page_text}, Cleaned: {current_page_num}"
                    )

                    try:
                        # Get the next page number
                        next_page_num = int(current_page_num) + 1

                        # Get the base URL without any query parameters
                        current_url = page.url
                        base_url = current_url.split("?")[0]

                        # Construct next page URL with filters parameter
                        next_url = (
                            f"{base_url}?filters=%7B%22page%22%3A{next_page_num}%7D"
                        )

                        self.logger.info(f"Found next page URL: {next_url}")
                        return next_url
                    except ValueError as e:
                        self.logger.error(
                            f"Error parsing page number '{current_page_num}': {str(e)}"
                        )
                        return None

            self.logger.info("No next page found")
            return None

        except Exception as e:
            self.logger.error(f"Error getting next page URL: {str(e)}")
            return None

    async def _launch_browser(self) -> Browser:
        """Launch browser instance"""
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=self.headless)
        return browser

    async def setup_page(self, browser: Browser) -> Page:
        """Configure browser page with common settings"""
        page = await browser.new_page()

        # Set viewport and user agent
        await page.set_viewport_size({"width": 1280, "height": 800})
        await page.set_extra_http_headers(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
            }
        )

        # Set default timeout
        page.set_default_timeout(self.timeout)

        return page

    def save_urls_to_file(self, urls: List[str], filename: str = "product_urls.json"):
        """Save scraped URLs to a JSON file"""
        try:
            # Create data directory if it doesn't exist
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)

            # Save URLs to file
            file_path = data_dir / filename
            with open(file_path, "w") as f:
                json.dump(
                    {
                        "scraped_at": datetime.now().isoformat(),
                        "total_urls": len(urls),
                        "urls": urls,
                    },
                    f,
                    indent=2,
                )

            self.logger.info(f"Saved {len(urls)} URLs to {file_path}")

        except Exception as e:
            self.logger.error(f"Error saving URLs to file: {str(e)}")
