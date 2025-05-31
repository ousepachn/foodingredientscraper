from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from playwright.async_api import Browser, Page
import re
import logging
from datetime import datetime

from app.models.product import ProductData


class BaseScraper(ABC):
    """Base class for all product scrapers"""

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """Initialize scraper with configuration"""
        self.headless = headless
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    async def scrape(self, url: str) -> ProductData:
        """
        Scrape product data from URL.

        Args:
            url: Product page URL to scrape

        Returns:
            ProductData object with scraped information
        """
        pass

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """
        Check if this scraper can handle the given URL.

        Args:
            url: URL to check

        Returns:
            True if scraper can handle URL, False otherwise
        """
        pass

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

    async def wait_for_content(self, page: Page) -> bool:
        """Wait for page content to load"""
        try:
            # Wait for network to be idle
            await page.wait_for_load_state("networkidle")

            # Wait for body to be visible
            await page.wait_for_selector("body", state="visible")

            return True
        except Exception as e:
            self.logger.error(f"Error waiting for content: {str(e)}")
            return False

    def parse_ingredients(self, text: str) -> List[str]:
        """Parse ingredients list from text"""
        if not text:
            return []

        # Split by common delimiters
        ingredients = []
        for part in re.split(r"[,;]", text):
            # Clean up each ingredient
            ingredient = part.strip().lower()
            if ingredient:
                # Remove common prefixes
                ingredient = re.sub(r"^contains\s+", "", ingredient)
                ingredient = re.sub(r"^ingredients:\s*", "", ingredient)
                ingredients.append(ingredient)

        return ingredients

    def parse_allergens(self, text: str) -> Optional[List[str]]:
        """Parse allergens from text"""
        if not text:
            return None

        # Common allergen patterns
        allergen_patterns = [
            r"contains:\s*([^.]*)",
            r"allergens:\s*([^.]*)",
            r"may contain:\s*([^.]*)",
            r"manufactured in a facility that processes:\s*([^.]*)",
        ]

        allergens = []
        for pattern in allergen_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Split and clean allergens
                for allergen in re.split(r"[,;]", match.group(1)):
                    allergen = allergen.strip().lower()
                    if allergen:
                        allergens.append(allergen)

        return allergens if allergens else None

    def parse_nutrition(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse nutrition facts from text"""
        if not text:
            return None

        nutrition = {}

        # Common nutrition patterns
        patterns = {
            "serving_size": r"serving size:\s*([^\n]*)",
            "servings_per_container": r"servings per container:\s*(\d+)",
            "calories": r"calories:\s*(\d+)",
            "total_fat": r"total fat:\s*(\d+(?:\.\d+)?)\s*g",
            "saturated_fat": r"saturated fat:\s*(\d+(?:\.\d+)?)\s*g",
            "trans_fat": r"trans fat:\s*(\d+(?:\.\d+)?)\s*g",
            "cholesterol": r"cholesterol:\s*(\d+)\s*mg",
            "sodium": r"sodium:\s*(\d+)\s*mg",
            "total_carbohydrates": r"total carbohydrates:\s*(\d+(?:\.\d+)?)\s*g",
            "dietary_fiber": r"dietary fiber:\s*(\d+(?:\.\d+)?)\s*g",
            "sugars": r"sugars:\s*(\d+(?:\.\d+)?)\s*g",
            "protein": r"protein:\s*(\d+(?:\.\d+)?)\s*g",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    nutrition[key] = value
                except ValueError:
                    nutrition[key] = match.group(1)

        return nutrition if nutrition else None

    async def handle_errors(self, page: Page, error: Exception) -> ProductData:
        """Handle scraping errors and return error product data"""
        self.logger.error(f"Scraping error: {str(error)}")

        # Create error product data
        product = ProductData(
            url=page.url,
            scrape_status="failed",
            error_message=str(error),
            scrape_duration=0.0,
        )

        try:
            # Try to get product name even if other scraping failed
            product.product_name = await self._extract_product_name(page)
        except:
            pass

        return product

    async def _extract_product_name(self, page: Page) -> str:
        """Extract product name from page"""
        # Default implementation - override in specific scrapers
        try:
            # Try common selectors
            selectors = [
                "h1.product-name",
                "h1.product-title",
                'h1[itemprop="name"]',
                "h1",
            ]

            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text:
                        return text.strip()

            return "Unknown Product"
        except Exception as e:
            self.logger.error(f"Error extracting product name: {str(e)}")
            return "Unknown Product"
