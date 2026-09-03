#!/usr/bin/env python3
"""
Debug script to inspect Woolworths beauty category HTML structure
Run this to see what's actually on the page
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

def debug_beauty_page():
    """
    Load the beauty page and inspect its structure.
    This helps us find the correct selectors.
    """
    
    print("=" * 60)
    print("DEBUGGING WOOLWORTHS BEAUTY CATEGORY")
    print("=" * 60)
    
    url = 'https://www.woolworths.com.au/shop/browse/beauty'
    
    # Setup Chrome
    options = Options()
    # DON'T use headless - we want to see what's happening
    # options.add_argument('--headless=new')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = None
    
    try:
        driver = webdriver.Chrome(options=options)
        
        print(f"\n1. Loading {url}")
        driver.get(url)
        
        print("2. Waiting 3 seconds for page to load...")
        time.sleep(3)
        
        print("3. Scrolling down to trigger content loading...")
        driver.execute_script("window.scrollBy(0, 1000)")
        time.sleep(2)
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        print("\n4. DEBUGGING: Looking for product containers...\n")
        
        # Try different selectors
        selectors_to_try = [
            ('wc-product-tile', 'Web Component'),
            ('div.product-tile-body', 'product-tile-body'),
            ('[class*="product"]', 'Any class with product'),
            ('[class*="Product"]', 'Any class with Product'),
            ('article', 'article tags'),
            ('[role="article"]', 'role=article'),
            ('[data-testid*="product"]', 'data-testid with product'),
            ('div[class*="tile"]', 'Any class with tile'),
            ('li', 'li tags'),
        ]
        
        for selector, description in selectors_to_try:
            try:
                elements = soup.select(selector)
                if elements:
                    print(f"✓ Found {len(elements)} elements with: {description} ({selector})")
                    
                    # Print first element's HTML
                    if elements:
                        print(f"  First element (first 300 chars):")
                        html_str = str(elements[0])[:300]
                        print(f"  {html_str}...\n")
            except:
                pass
        
        # Check for specific text patterns
        print("\n5. DEBUGGING: Looking for price/product indicators...\n")
        
        # Look for dollar signs (prices)
        if '$' in html:
            print("✓ Found $ symbols (prices exist)")
            # Find elements with $
            price_elements = soup.find_all(string=lambda text: text and '$' in text)
            if price_elements:
                print(f"  Found {len(price_elements)} price indicators")
                print(f"  Sample: {price_elements[0]}")
        else:
            print("✗ No $ symbols found (prices might be loaded differently)")
        
        # Look for common product keywords
        keywords = ['product', 'item', 'price', 'product-', 'tile', 'card']
        for keyword in keywords:
            count = html.lower().count(keyword)
            if count > 0:
                print(f"✓ Found '{keyword}' {count} times in HTML")
        
        # Print full HTML to file for inspection
        print("\n6. DEBUGGING: Saving full HTML to file...\n")
        with open('beauty_page_debug.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✓ Saved full HTML to beauty_page_debug.html")
        print("  Open this file in a text editor to inspect structure")
        
        # Print first 2000 chars
        print("\n7. FIRST 2000 CHARACTERS OF PAGE:\n")
        print(html[:2000])
        
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("""
1. Open beauty_page_debug.html in a web browser
2. Right-click on a product → Inspect
3. Look for the class names or tags containing the product
4. Report back with what you see

Common issues:
- Products might be in <li> tags instead of <wc-product-tile>
- Might use different class names
- Might be loaded by different JavaScript
        """)
        
    finally:
        if driver:
            time.sleep(5)  # Keep window open for inspection
            driver.quit()

if __name__ == '__main__':
    debug_beauty_page()
