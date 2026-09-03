from universal_woolworths_scraper import UniversalWoolworthsScraper

scraper = UniversalWoolworthsScraper()

# Baby category
products = scraper.scrape_pages(
    'https://www.woolworths.com.au/shop/browse/baby?isHideEverydayMarketProducts=true&excludeUnavailableProducts=true&sortBy=Name',
    start_page=1,
    end_page=999
)

if products:
    print(f"✓ Got {len(products)} products!")
    # Specify your custom CSV filename here
    scraper.save_to_csv(products, filename='woolworths_baby.csv')
else:
    print("Still failing - run debug.py")