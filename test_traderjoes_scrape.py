import asyncio
from app.scrapers.trader_joes import TraderJoesScraper


async def main():
    url = (
        "https://www.traderjoes.com/home/products/pdp/strawberry-doodle-cookies-081523"
    )
    scraper = TraderJoesScraper(headless=True)
    product = await scraper.scrape(url)
    print("Scraped Product Data:")
    print(product.to_dict())


if __name__ == "__main__":
    asyncio.run(main())
