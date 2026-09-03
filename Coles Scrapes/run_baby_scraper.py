from universal_coles_scraper import UniversalColesScraper

scraper = UniversalColesScraper()

# Baby category
products = scraper.scrape_pages(
    'https://www.coles.com.au/browse/baby',
    start_page=1,
    end_page=999
)

if products:
    print(f"✓ Got {len(products)} products!")
    # Specify your custom CSV filename here
    scraper.save_to_csv(products, filename='coles_baby.csv')
else:
    print("Still failing - run debug.py")