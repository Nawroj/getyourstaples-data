#!/usr/bin/env python3
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

"""
UNIVERSAL Woolworths Scraper
Handles multiple HTML structures (food, beauty, etc.)
Stays open, clicks the "Next" pagination button, and bypasses bot-blocks
"""

import random
import time
import json
import csv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup


class UniversalWoolworthsScraper:
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

    def scrape_pages(self, base_url, start_page=1, end_page=999, verbose=True):
        """
        Opens a single browser session, scrapes the page, and clicks the 'Next' button.
        """
        all_products = []
        
        # Initialize undetected-chromedriver options
        options = uc.ChromeOptions()
        options.add_argument('--window-size=1920,1080')
        
        # Note: We removed the `add_experimental_option` lines because 
        # undetected_chromedriver automatically handles those anti-bot evasions for us!
        
        driver = None
        
        try:
            driver = uc.Chrome(options=options)
            
            if verbose:
                print(f"  1. Loading initial page: {base_url}")
            
            driver.get(base_url)
            time.sleep(3) # Give the initial site framework time to load
            
            for page_num in range(start_page, end_page + 1):
                if verbose:
                    print(f"\n--- Scraping Page {page_num} ---")
                    print("  2. Scrolling to trigger lazy loading...")
                
                # Scroll down slowly to mimic human behavior
                for _ in range(5):
                    driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(1.5)
                
                if verbose:
                    print("  3. Waiting for products to load...")
                    
                # Wait for products to appear on screen
                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: d.execute_script(
                            "return document.querySelectorAll('wc-product-tile, .product-tile-body').length > 0;"
                        )
                    )
                except:
                    if verbose:
                        print("  ⚠ Timeout waiting for products to render, proceeding anyway...")
                
                time.sleep(random.uniform(2.5, 3.5))
                
                if verbose:
                    print("  4. Extracting data via JavaScript...")
                
                extract_js = """
                var products = [];
                var tiles = document.querySelectorAll('wc-product-tile, .product-tile-body');
                var seen = new Set();
                
                tiles.forEach(function(tile) {
                    var root = tile.shadowRoot ? tile.shadowRoot : tile;
                    
                    var titleEl = root.querySelector('.title a') || root.querySelector('.title');
                    var priceEl = root.querySelector('.product-tile-price .primary') || root.querySelector('.price') || root.querySelector('.primary');
                    var imgEl = root.querySelector('.product-tile-image img') || root.querySelector('img');
                    
                    if (titleEl && priceEl) {
                        var name = titleEl.textContent.trim();
                        var price = priceEl.textContent.trim();
                        var img = imgEl ? (imgEl.src || imgEl.getAttribute('src')) : 'N/A';
                        
                        if (!seen.has(name) && name.length > 0) {
                            seen.add(name);
                            products.push({
                                'name': name,
                                'price': price,
                                'image': img
                            });
                        }
                    }
                });
                return products;
                """
                
                js_products = driver.execute_script(extract_js)
                current_page_products = []
                
                if js_products and len(js_products) > 0:
                    current_page_products = js_products
                else:
                    if verbose:
                        print("  5. JS extraction found 0 products. Falling back to BeautifulSoup...")
                    html = driver.page_source
                    soup = BeautifulSoup(html, 'html.parser')
                    current_page_products = self._find_products_auto_detect(soup, verbose)
                
                if current_page_products:
                    if verbose:
                        print(f"     ✓ Found {len(current_page_products)} products on this page!")
                    all_products.extend(current_page_products)
                else:
                    if verbose:
                        print("  ✗ No products found. Stopping.")
                    break
                
                # Check for the Next button
                if page_num < end_page:
                    if verbose:
                        print("  5. Looking for 'Next' button...")
                    
                    next_btn_js = """
                    var nextButton = document.querySelector('a.paging-next, button.paging-next, [aria-label*="Next page"], .pagination-next');
                    
                    if (!nextButton) {
                        var allLinks = document.querySelectorAll('a, button');
                        for (var i=0; i<allLinks.length; i++) {
                            var text = allLinks[i].innerText || '';
                            if (text.trim().toLowerCase() === 'next') {
                                nextButton = allLinks[i];
                                break;
                            }
                        }
                    }
                    if (nextButton) {
                        // Check if it has a disabled attribute or class
                        if (nextButton.hasAttribute('disabled') || 
                            nextButton.classList.contains('disabled') || 
                            nextButton.getAttribute('aria-disabled') === 'true') {
                            return "DISABLED";
                        }
                        return nextButton;
                    }
                    return null;
                    """
                    
                    next_btn = driver.execute_script(next_btn_js)
                    
                    if next_btn == "DISABLED":
                        if verbose:
                            print("  ✓ Reached the last page ('Next' button is disabled).")
                        break
                    elif next_btn:
                        if verbose:
                            print("  ✓ Clicking 'Next' page...")
                            
                        # Wipe the old products off the screen before clicking next!
                        driver.execute_script("document.querySelectorAll('wc-product-tile, .product-tile-body').forEach(e => e.remove());")
                        
                        # Click the button via JS to avoid "element intercepted" errors
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", next_btn)
                        
                        # Wait for the network to fetch the new products
                        time.sleep(random.uniform(3.5, 5.0))
                    else:
                        if verbose:
                            print("  ✗ No 'Next' button found. Stopping.")
                        break

        except Exception as e:
            if verbose:
                print(f"  ✗ Fatal Error: {e}")
                
        finally:
            if driver:
                driver.quit()
                
        return all_products

    # -------------------------------------------------------------------
    # FALLBACK BEAUTIFULSOUP METHODS
    # -------------------------------------------------------------------

    def _find_products_auto_detect(self, soup, verbose=False):
        products = self._extract_from_product_tiles(soup, verbose)
        if products: return products
            
        products = self._extract_from_generic_product_class(soup, verbose)
        if products: return products
            
        products = self._extract_from_list_items(soup, verbose)
        if products: return products
            
        products = self._extract_from_articles(soup, verbose)
        if products: return products
        
        return []
    
    def _extract_from_product_tiles(self, soup, verbose=False):
        products = []
        tiles = soup.find_all('div', class_=lambda x: x and 'product-tile-body' in x)
        for tile in tiles:
            try:
                name = self._extract_text(tile, '[class*="title"] a') or 'N/A'
                price = self._extract_text(tile, '[class*="price"]') or 'N/A'
                image = self._extract_image(tile, 'img') or 'N/A'
                if name != 'N/A' and price != 'N/A':
                    products.append({'name': name, 'price': price, 'image': image})
            except: continue
        return products
    
    def _extract_from_generic_product_class(self, soup, verbose=False):
        products = []
        elements = soup.find_all(lambda tag: tag.name and tag.get('class') and any('product' in c.lower() for c in tag.get('class', [])))
        seen_names = set()
        for elem in elements[:100]: 
            try:
                texts = elem.find_all(['a', 'h2', 'h3', 'h4', 'span'])
                name = 'N/A'
                for text_elem in texts:
                    text = text_elem.get_text(strip=True)
                    if len(text) > 5 and len(text) < 200 and '$' not in text:
                        name = text; break
                
                price = 'N/A'
                for text_elem in elem.find_all(['span', 'div']):
                    text = text_elem.get_text(strip=True)
                    if '$' in text and len(text) < 20:
                        price = text; break
                
                image = 'N/A'
                img = elem.find('img')
                if img: image = img.get('src', 'N/A')
                
                if (name != 'N/A' and price != 'N/A' and name not in seen_names):
                    seen_names.add(name)
                    products.append({'name': name, 'price': price, 'image': image})
            except: continue
        return products
    
    def _extract_from_list_items(self, soup, verbose=False):
        products = []
        seen_names = set()
        for li in soup.find_all('li'):
            try:
                text = li.get_text()
                if '$' not in text: continue
                name = self._extract_text(li, 'a') or self._extract_text(li, '[class*="title"]') or 'N/A'
                price = self._extract_text(li, lambda t: t and '$' in t.get_text()) or 'N/A'
                image = self._extract_image(li, 'img') or 'N/A'
                if name != 'N/A' and price != 'N/A' and name not in seen_names:
                    seen_names.add(name)
                    products.append({'name': name, 'price': price, 'image': image})
            except: continue
        return products
    
    def _extract_from_articles(self, soup, verbose=False):
        products = []
        seen_names = set()
        for article in soup.find_all('article'):
            try:
                if '$' not in article.get_text(): continue
                name = self._extract_text(article, 'a') or self._extract_text(article, '[class*="title"]') or 'N/A'
                price = self._extract_text(article, lambda t: t and '$' in t.get_text()) or 'N/A'
                image = self._extract_image(article, 'img') or 'N/A'
                if name != 'N/A' and price != 'N/A' and name not in seen_names:
                    seen_names.add(name)
                    products.append({'name': name, 'price': price, 'image': image})
            except: continue
        return products
    
    def _extract_text(self, element, selector):
        try:
            elem = element.find(selector) if callable(selector) else element.select_one(selector)
            if elem: return elem.get_text(strip=True)
        except: pass
        return None
    
    def _extract_image(self, element, selector):
        try:
            img = element.select_one(selector)
            if img and img.get('src'): return img['src']
        except: pass
        return None
    
    def save_to_json(self, products, filename='woolworths_products.json'):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved {len(products)} products to {filename}")
    
    def save_to_csv(self, products, filename='woolworths_products.csv'):
        if not products: return
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'price', 'image'])
            writer.writeheader()
            writer.writerows(products)
        print(f"✓ Saved {len(products)} products to {filename}")