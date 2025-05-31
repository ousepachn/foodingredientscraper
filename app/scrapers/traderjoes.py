from typing import Optional, Dict, Any
from playwright.async_api import Browser, Page
import re
from datetime import datetime
import logging
import os
from pathlib import Path

from app.scrapers.base import BaseScraper
from app.models.product import ProductData


# Set up logging
def setup_logging():
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create a logger
    logger = logging.getLogger("traderjoes_scraper")
    logger.setLevel(logging.INFO)

    # Create handlers
    # File handler for all logs
    file_handler = logging.FileHandler(log_dir / "traderjoes_scraper.log")
    file_handler.setLevel(logging.INFO)

    # Console handler for INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create formatters and add it to handlers
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(log_format)
    console_handler.setFormatter(log_format)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Initialize logger
logger = setup_logging()


class TraderJoesScraper(BaseScraper):
    """Scraper for Trader Joe's product pages"""

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """Initialize scraper with configuration"""
        super().__init__(headless, timeout)
        self.logger = logger  # Use the configured logger

    def can_handle(self, url: str) -> bool:
        """Check if URL is a Trader Joe's product page"""
        return "traderjoes.com" in url.lower() and "/products/" in url.lower()

    async def scrape(self, url: str) -> ProductData:
        """Scrape product data from Trader Joe's URL"""
        start_time = datetime.now()
        page = None

        try:
            async with await self._launch_browser() as browser:
                page = await self.setup_page(browser)

                # Navigate to the page
                await page.goto(url, wait_until="networkidle")

                # Wait for the page to be fully loaded
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("networkidle")

                # Additional wait for content
                try:
                    await page.wait_for_selector("h1", timeout=10000)
                except:
                    self.logger.warning("Timeout waiting for h1 element")

                if not await self.wait_for_content(page):
                    raise Exception("Failed to load page content")

                # Extract product data
                product = ProductData(
                    url=url,
                    product_name=await self._extract_product_name(page),
                    brand="Trader Joe's",
                    description=await self._extract_description(page),
                    price=await self._extract_price(page),
                    ingredients=await self._extract_ingredients(page),
                    allergens=await self._extract_allergens(page),
                    nutrition_facts=await self._extract_nutrition(page),
                    scraped_at=datetime.now().isoformat(),
                    scrape_status="success",
                    scrape_duration=(datetime.now() - start_time).total_seconds(),
                )

                return product

        except Exception as e:
            if page:
                return await self.handle_errors(page, e)
            else:
                # If page wasn't created, create a basic error product
                return ProductData(
                    url=url,
                    scrape_status="failed",
                    error_message=str(e),
                    scrape_duration=(datetime.now() - start_time).total_seconds(),
                )

    async def _launch_browser(self) -> Browser:
        """Launch browser instance"""
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=self.headless)
        return browser

    async def _extract_product_name(self, page: Page) -> str:
        """Extract product name from page"""
        try:
            # Try multiple selectors for Trader Joe's product name
            selectors = [
                'h1[data-testid="product-name"]',
                "h1.ProductDetails__title",
                "h1.ProductDetails__name",
                'h1[class*="ProductDetails"]',
                'h1[class*="product-name"]',
                'h1[class*="product-title"]',
                'h1[itemprop="name"]',
                "h1",  # Fallback to any h1
            ]

            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text and text.strip() and text.strip() != "Oops!":
                        self.logger.info(
                            f"Found product name using selector: {selector}"
                        )
                        return text.strip()

            # If we get here, try to get the page title as a last resort
            title = await page.title()
            if title and "Trader Joe's" in title:
                # Remove "Trader Joe's" and any trailing text
                name = title.split("|")[0].replace("Trader Joe's", "").strip()
                if name and name != "Oops!":
                    self.logger.info("Using page title as product name")
                    return name

            self.logger.warning("Could not find product name with any selector")
            return "Unknown Product"
        except Exception as e:
            self.logger.error(f"Error extracting product name: {str(e)}")
            return "Unknown Product"

    async def _extract_description(self, page: Page) -> Optional[str]:
        """Extract product description"""
        try:
            # Try different description selectors
            selectors = [
                'div[data-testid="product-description"]',
                "div.ProductDetails__description",
                'div[class*="ProductDetails__description"]',
                'div[class*="product-description"]',
                'div[itemprop="description"]',
                "div.ProductDetails__content",
                'div[class*="ProductDetails__content"]',
            ]

            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text and text.strip():
                        self.logger.info(
                            f"Found description using selector: {selector}"
                        )
                        return text.strip()

            return None
        except Exception as e:
            self.logger.error(f"Error extracting description: {str(e)}")
            return None

    async def _extract_price(self, page: Page) -> Optional[float]:
        """Extract product price"""
        try:
            # Try different price selectors
            selectors = [
                'span[data-testid="product-price"]',
                "span.product-price",
                'span[itemprop="price"]',
            ]

            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text:
                        # Extract numeric price
                        match = re.search(r"\$?(\d+\.?\d*)", text)
                        if match:
                            return float(match.group(1))

            return None
        except Exception as e:
            self.logger.error(f"Error extracting price: {str(e)}")
            return None

    async def _extract_ingredients(self, page: Page) -> list[str]:
        """Extract ingredients list"""
        try:
            # Try different ingredients selectors
            selectors = [
                'div[class*="IngredientsSummary"]',
                'div[class*="ingredients-summary"]',
                'div[class*="ingredients"]',
                'div[data-testid="ingredients"]',
                'div[itemprop="ingredients"]',
                'div:has-text("Ingredients" i)',
            ]

            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text:
                        # Clean up the text to get just the ingredients
                        text = text.replace("Ingredients:", "").strip()
                        ingredients = self.parse_ingredients(text)
                        if ingredients:
                            self.logger.info(
                                f"Found ingredients using selector: {selector}"
                            )
                            return ingredients

            return []
        except Exception as e:
            self.logger.error(f"Error extracting ingredients: {str(e)}")
            return []

    async def _extract_allergens(self, page: Page) -> Optional[list[str]]:
        """Extract allergens information"""
        try:
            # Try different allergen selectors
            selectors = [
                "ul.IngredientsSummary_ingredientsSummary__allergensList__1ROpD li",
                'ul[class*="IngredientsSummary_ingredientsSummary__allergensList"] li',
                'ul[class*="allergensList"] li',
                "div.IngredientsSummary_ingredientsSummary__1WMGh ul li",
                'div[class*="IngredientsSummary_ingredientsSummary"] ul li',
                'div[class*="ingredients-summary"] ul li',
                'div[class*="allergens"]',
                'div[data-testid="allergens"]',
                'div[class*="allergen-information"]',
                'div:has-text("allergen" i)',
                'div:has-text("contains" i)',
            ]

            for selector in selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    allergens = []
                    for element in elements:
                        text = await element.text_content()
                        if text:
                            # Clean up the text
                            text = (
                                text.replace("CONTAINS", "")
                                .replace("Contains", "")
                                .strip()
                            )
                            # Split by common delimiters
                            for allergen in re.split(r"[,;]", text):
                                allergen = allergen.strip()
                                if allergen:
                                    allergens.append(allergen)

                    if allergens:
                        self.logger.info(f"Found allergens using selector: {selector}")
                        return allergens

            return None
        except Exception as e:
            self.logger.error(f"Error extracting allergens: {str(e)}")
            return None

    async def _extract_nutrition(self, page: Page) -> Optional[Dict[str, Any]]:
        """Extract nutrition facts"""
        try:
            # Try different nutrition selectors
            selectors = [
                'div[data-testid="nutrition-facts"]',
                "div.ProductDetails__nutrition",
                'div[class*="ProductDetails__nutrition"]',
                'div[class*="nutrition-facts"]',
                'div[itemprop="nutrition"]',
                'div.ProductDetails__content:has-text("Nutrition Facts")',
                'div[class*="ProductDetails__content"]:has-text("Nutrition Facts")',
                "table.NutritionFacts",
                'table[class*="NutritionFacts"]',
            ]

            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    # First try to get the text content
                    text = await element.text_content()
                    if text:
                        self.logger.info(
                            f"Found nutrition facts using selector: {selector}"
                        )

                        # Try to parse the text content
                        nutrition = self.parse_nutrition(text)
                        if nutrition:
                            return nutrition

                        # If text parsing fails, try to parse table structure
                        try:
                            # Look for table rows
                            rows = await element.query_selector_all("tr")
                            if rows:
                                nutrition = {}
                                for row in rows:
                                    # Get cells in the row
                                    cells = await row.query_selector_all("td, th")
                                    if len(cells) >= 2:
                                        label = await cells[0].text_content()
                                        value = await cells[1].text_content()

                                        # Clean up the values
                                        label = label.strip().lower()
                                        value = value.strip()

                                        # Map common nutrition labels
                                        if "serving size" in label:
                                            nutrition["serving_size"] = value
                                        elif "servings per container" in label:
                                            nutrition["servings_per_container"] = value
                                        elif "calories" in label:
                                            try:
                                                nutrition["calories"] = float(
                                                    re.search(r"\d+", value).group()
                                                )
                                            except:
                                                pass
                                        elif "total fat" in label:
                                            try:
                                                nutrition["total_fat"] = float(
                                                    re.search(
                                                        r"\d+(?:\.\d+)?", value
                                                    ).group()
                                                )
                                            except:
                                                pass
                                        elif "saturated fat" in label:
                                            try:
                                                nutrition["saturated_fat"] = float(
                                                    re.search(
                                                        r"\d+(?:\.\d+)?", value
                                                    ).group()
                                                )
                                            except:
                                                pass
                                        elif "trans fat" in label:
                                            try:
                                                nutrition["trans_fat"] = float(
                                                    re.search(
                                                        r"\d+(?:\.\d+)?", value
                                                    ).group()
                                                )
                                            except:
                                                pass
                                        elif "cholesterol" in label:
                                            try:
                                                nutrition["cholesterol"] = float(
                                                    re.search(r"\d+", value).group()
                                                )
                                            except:
                                                pass
                                        elif "sodium" in label:
                                            try:
                                                nutrition["sodium"] = float(
                                                    re.search(r"\d+", value).group()
                                                )
                                            except:
                                                pass
                                        elif "total carbohydrate" in label:
                                            try:
                                                nutrition["total_carbohydrates"] = (
                                                    float(
                                                        re.search(
                                                            r"\d+(?:\.\d+)?", value
                                                        ).group()
                                                    )
                                                )
                                            except:
                                                pass
                                        elif "dietary fiber" in label:
                                            try:
                                                nutrition["dietary_fiber"] = float(
                                                    re.search(
                                                        r"\d+(?:\.\d+)?", value
                                                    ).group()
                                                )
                                            except:
                                                pass
                                        elif "sugars" in label:
                                            try:
                                                nutrition["sugars"] = float(
                                                    re.search(
                                                        r"\d+(?:\.\d+)?", value
                                                    ).group()
                                                )
                                            except:
                                                pass
                                        elif "protein" in label:
                                            try:
                                                nutrition["protein"] = float(
                                                    re.search(
                                                        r"\d+(?:\.\d+)?", value
                                                    ).group()
                                                )
                                            except:
                                                pass

                                if nutrition:
                                    return nutrition
                        except Exception as e:
                            self.logger.error(
                                f"Error parsing nutrition table: {str(e)}"
                            )

            return None
        except Exception as e:
            self.logger.error(f"Error extracting nutrition facts: {str(e)}")
            return None
