import asyncio
import argparse
from app.scrapers.product_url_scraper import ProductUrlScraper


async def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Scrape Trader Joe's product URLs")
    parser.add_argument(
        "--max-pages", type=int, help="Maximum number of pages to scrape"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode",
    )
    args = parser.parse_args()

    # Initialize scraper with max_pages if provided
    scraper = ProductUrlScraper(headless=args.headless, max_pages=args.max_pages)

    # Category URL to scrape
    category_url = "https://www.traderjoes.com/home/products/category/products-2"

    print(f"Starting URL scraping for category: {category_url}")
    if args.max_pages:
        print(f"Maximum pages to scrape: {args.max_pages}")

    try:
        # Scrape product URLs
        product_urls = await scraper.scrape_category(category_url)

        # Print results
        print(f"\nFound {len(product_urls)} product URLs")

        # Save URLs to file
        scraper.save_urls_to_file(product_urls)

        # Print first few URLs as sample
        print("\nSample URLs:")
        for url in product_urls[:5]:
            print(f"- {url}")

    except Exception as e:
        print(f"\nError during scraping: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
