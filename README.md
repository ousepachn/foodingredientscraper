# Trader Joe's Product Scraper

A Python-based web scraper for extracting product information from Trader Joe's website. This scraper uses Playwright for browser automation and can extract product details including ingredients, allergens, and nutritional information.

## Features

- Extracts product information from Trader Joe's product pages
- Handles dynamic content loading
- Extracts:
  - Product name
  - Brand
  - Description
  - Price
  - Ingredients
  - Allergens
  - Nutrition facts
- Robust error handling and logging
- Case-insensitive text matching
- Configurable browser settings

## Requirements

- Python 3.11 or higher
- Playwright
- Other dependencies listed in requirements.txt

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install
```

## Usage

Run the test script to scrape a product:
```bash
python test_scraper.py
```

The script will prompt you to enter a Trader Joe's product URL. Enter the URL and the scraper will extract and display the product information.

## Project Structure

```
.
├── app/
│   ├── scrapers/
│   │   ├── base.py
│   │   └── traderjoes.py
│   └── models/
│       └── product.py
├── logs/
├── test_scraper.py
├── requirements.txt
└── README.md
```

## Logging

Logs are stored in the `logs` directory:
- `traderjoes_scraper.log`: Contains detailed logging information
- Console output shows real-time scraping progress

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 