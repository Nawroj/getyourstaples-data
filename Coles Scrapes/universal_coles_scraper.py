#!/usr/bin/env python3
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

"""
UNIVERSAL Coles Scraper
Handles Coles HTML structures.
Stays open, uses native Selenium waits, warms cookies, and bypasses bot-blocks safely.
Skips "Deliver Mode" and "Currently unavailable" products.
"""

import random
import time
import csv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup


class UniversalColesScraper:
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

    def scrape_pages(self, base_url, start_page=1, end_page=999, verbose=True):
        """
        Opens a single browser session, scrapes the page, and clicks the 'Next' button safely.
        """
        all_products = []
        
        options = uc.ChromeOptions()
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-popup-blocking')
        
        driver = None
        
        try:
            driver = uc.Chrome(options=options, use_subprocess=True)
            
            if verbose:
                print("  0. Warming cookies on the Coles homepage to bypass Akamai WAF...")
            
            driver.get("https://www.coles.com.au/")
            time.sleep(random.uniform(5.5, 7.5)) 
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(2)
            
            if verbose:
                print(f"  1. Navigating to target category: {base_url}")
            
            driver.get(base_url)
            time.sleep(4) 
            
            for page_num in range(start_page, end_page + 1):
                if verbose:
                    print(f"\n--- Scraping Page {page_num} ---")
                    print("  2. Scrolling to trigger lazy loading...")
                
                # Human-like smooth scrolling
                for _ in range(6):
                    driver.execute_script("window.scrollBy({top: 800, behavior: 'smooth'});")
                    time.sleep(1.5)
                
                if verbose:
                    print("  3. Waiting for products to load...")
                    
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.product__title, [data-testid="product-tile"]'))
                    )
                except:
                    if verbose:
                        print("  ⚠ Timeout waiting for products to render, proceeding anyway...")
                
                time.sleep(random.uniform(2.0, 3.0))
                
                if verbose:
                    print("  4. Extracting data via JavaScript...")
                
                extract_js = """
                var products = [];
                var titles = document.querySelectorAll('.product__title');
                var seen = new Set();
                
                titles.forEach(function(titleEl) {
                    var tile = titleEl.closest('section, article, div[data-testid*="product"], li');
                    if (!tile) tile = titleEl.parentElement.parentElement;
                    
                    // --- NEW FEATURE: Skip 'Deliver Mode' and 'Currently unavailable' items ---
                    var tileText = (tile.textContent || "").toLowerCase();
                    if (tileText.includes("deliver mode") || tileText.includes("currently unavailable")) {
                        return; // Skips to the next iteration of the forEach loop
                    }
                    
                    var priceEl = tile.querySelector('.price__value, .price, .product__pricing');
                    var imgEl = tile.querySelector('img[data-testid="product-image"], .product__image_area img, .product__hero_image img, img');
                    
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
                    current_page_products = self._find_products_auto_detect(soup)
                
                if current_page_products:
                    if verbose:
                        print(f"     ✓ Found {len(current_page_products)} products on this page!")
                    all_products.extend(current_page_products)
                else:
                    if verbose:
                        print("  ✗ No products found. Stopping.")
                    break
                
                if page_num < end_page:
                    if verbose:
                        print("  5. Looking for 'Next' button...")
                    
                    # Store the first product's title in the browser's window object via JS
                    driver.execute_script("window.old_title = document.querySelector('.product__title') ? document.querySelector('.product__title').textContent.trim() : '';")

                    next_btn_js = """
                    var nextButton = document.querySelector(
                        '[aria-label="Go to next page"], ' + 
                        '[aria-label*="next" i], ' + 
                        'nav[data-testid="pagination"] li:last-child a'
                    );
                    
                    if (!nextButton) {
                        var allLinks = document.querySelectorAll('a, button');
                        for (var i=0; i<allLinks.length; i++) {
                            var aria = allLinks[i].getAttribute('aria-label') || '';
                            if (aria.toLowerCase().includes('next')) {
                                nextButton = allLinks[i];
                                break;
                            }
                        }
                    }
                    if (nextButton) {
                        if (nextButton.disabled || 
                            nextButton.hasAttribute('disabled') || 
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
                            print("  ✓ Clicking 'Next' page using human-like ActionChains...")
                            
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_btn)
                        time.sleep(1.5)
                        
                        ActionChains(driver).move_to_element(next_btn).click().perform()
                        
                        if verbose:
                            print("  ✓ Click successful. Waiting for new products to load...")
                            
                        try:
                            # Safe Javascript check that completely avoids StaleElementReferenceExceptions
                            WebDriverWait(driver, 15).until(
                                lambda d: d.execute_script("var el = document.querySelector('.product__title'); return el && el.textContent.trim() !== window.old_title;")
                            )
                        except:
                            if verbose:
                                print("  ⚠ Timed out waiting for products to change. Continuing anyway...")
                        
                        time.sleep(random.uniform(2.5, 4.5))
                    else:
                        if verbose:
                            print("  ✗ No 'Next' button found. Stopping.")
                        break

        except Exception as e:
            if verbose:
                print(f"  ✗ Fatal Error: {e}")
                
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                
        return all_products

    def _find_products_auto_detect(self, soup):
        products = []
        seen_names = set()
        
        titles = soup.select('.product__title')
        for title_el in titles:
            try:
                parent = title_el.find_parent('section') or title_el.find_parent('article') or title_el.find_parent('div')
                if not parent: 
                    continue
                
                # --- NEW FEATURE: Skip 'Deliver Mode' and 'Currently unavailable' items in Fallback ---
                parent_text = parent.get_text(separator=' ').lower()
                if 'deliver mode' in parent_text or 'currently unavailable' in parent_text:
                    continue
                
                price_el = parent.select_one('.price__value, .price, .product__pricing')
                img_el = parent.select_one('img')
                
                if price_el:
                    name = title_el.get_text(strip=True)
                    price = price_el.get_text(strip=True)
                    image = img_el.get('src', 'N/A') if img_el else 'N/A'
                    
                    if name not in seen_names:
                        seen_names.add(name)
                        products.append({'name': name, 'price': price, 'image': image})
            except:
                continue
                
        return products
    
    def save_to_csv(self, products, filename='coles_products.csv'):
        if not products: 
            return
            
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'price', 'image'])
            writer.writeheader()
            writer.writerows(products)
        print(f"✓ Saved {len(products)} products to {filename}")