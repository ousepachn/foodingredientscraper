import asyncio
import json
from datetime import datetime
from app.scrapers.traderjoes import TraderJoesScraper


def get_valid_url() -> str:
    """Get and validate Trader Joe's product URL from user input"""
    while True:
        url = input(
            "\nPlease enter a Trader Joe's product URL (or 'q' to quit): "
        ).strip()

        if url.lower() == "q":
            print("Exiting...")
            exit(0)

        if not url:
            print("URL cannot be empty. Please try again.")
            continue

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        if "traderjoes.com" not in url.lower():
            print("Please enter a valid Trader Joe's URL.")
            continue

        if "/products/" not in url.lower():
            print("Please enter a valid Trader Joe's product URL.")
            continue

        return url


async def main():
    # Initialize scraper
    scraper = TraderJoesScraper(headless=True)  # Set headless=True for stability

    print("Trader Joe's Product Scraper")
    print("============================")

    while True:
        # Get URL from user
        url = get_valid_url()

        print(f"\nStarting scrape of {url}")
        start_time = datetime.now()

        try:
            # Scrape product data
            product = await scraper.scrape(url)

            # Print results
            print("\nScraping Results:")
            print(
                f"Duration: {(datetime.now() - start_time).total_seconds():.2f} seconds"
            )
            print(f"Status: {product.scrape_status}")

            if product.scrape_status == "success":
                print("\nProduct Details:")
                print(f"Name: {product.product_name}")
                print(f"Brand: {product.brand}")
                print(f"Price: ${product.price if product.price else 'N/A'}")

                if product.description:
                    print(f"\nDescription: {product.description}")

                if product.ingredients:
                    print("\nIngredients:")
                    for ingredient in product.ingredients:
                        print(f"- {ingredient}")

                if product.allergens:
                    print("\nAllergens:")
                    for allergen in product.allergens:
                        print(f"- {allergen}")

                if product.nutrition_facts:
                    print("\nNutrition Facts:")
                    for key, value in product.nutrition_facts.items():
                        print(f"- {key}: {value}")
            else:
                print(f"\nError: {product.error_message}")

            # Print raw product data
            print("\nRaw Product Data:")
            print(json.dumps(product.to_dict(), indent=2))

        except Exception as e:
            print(f"\nError during scraping: {str(e)}")

        # Ask if user wants to scrape another product
        while True:
            choice = (
                input("\nWould you like to scrape another product? (y/n): ")
                .lower()
                .strip()
            )
            if choice in ["y", "n"]:
                break
            print("Please enter 'y' or 'n'")

        if choice == "n":
            print("Exiting...")
            break


if __name__ == "__main__":
    asyncio.run(main())
