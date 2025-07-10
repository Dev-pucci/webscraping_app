#!/usr/bin/env python3
"""
Jumia Web Scraper - Enhanced Version
A Python script to scrape product information from Jumia e-commerce website.
Now includes additional fields expected by the frontend.
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import random
import re
from urllib.parse import urljoin, urlparse
import argparse
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Product:
    """Data class to represent a product with all fields expected by frontend"""
    name: str
    price: str
    original_price: str
    discount: str
    rating: str
    reviews_count: str
    image_url: str
    product_url: str
    brand: str
    category: str
    shipping_info: str = "N/A"
    badges: List[str] = None
    
    def __post_init__(self):
        if self.badges is None:
            self.badges = []

class JumiaScraper:
    def __init__(self, base_url: str = "https://www.jumia.co.ke", delay_range: tuple = (1, 3)):
        self.base_url = base_url
        self.delay_range = delay_range
        self.session = requests.Session()
        
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def _random_delay(self):
        """Add random delay between requests to be respectful"""
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)

    def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """Make HTTP request and return BeautifulSoup object"""
        try:
            self._random_delay()
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def search_products(self, query: str, max_pages: int = 5) -> List[Product]:
        """Search for products and return list of Product objects"""
        products = []
        
        for page in range(1, max_pages + 1):
            search_url = f"{self.base_url}/catalog/?q={query}&page={page}"
            logger.info(f"Scraping page {page}: {search_url}")
            
            soup = self._make_request(search_url)
            if not soup:
                continue
                
            # Find product containers
            product_containers = soup.find_all('article', class_='prd')
            
            if not product_containers:
                logger.info(f"No products found on page {page}")
                break
                
            for container in product_containers:
                product = self._extract_product_info(container)
                if product:
                    products.append(product)
            
            logger.info(f"Found {len(product_containers)} products on page {page}")
        
        return products

    def scrape_category(self, category_url: str, max_pages: int = 5) -> List[Product]:
        """Scrape products from a specific category"""
        products = []
        
        for page in range(1, max_pages + 1):
            if page == 1:
                url = category_url
            else:
                separator = '&' if '?' in category_url else '?'
                url = f"{category_url}{separator}page={page}"
            
            logger.info(f"Scraping category page {page}: {url}")
            
            soup = self._make_request(url)
            if not soup:
                continue
            
            # Try different selectors for category pages
            product_containers = (
                soup.find_all('article', class_='prd') or  # Standard grid
                soup.find_all('div', class_='prd') or     # Alternative layout
                soup.find_all('[data-track-onclick="eecProduct"]')  # Data attribute fallback
            )
            
            if not product_containers:
                logger.info(f"No products found on page {page}")
                break
            
            valid_products_count = 0
            for container in product_containers:
                product = self._extract_product_info(container)
                if product and product.name != "N/A":  # Only add if we got valid data
                    products.append(product)
                    valid_products_count += 1
            
            logger.info(f"Found {len(product_containers)} containers, {valid_products_count} valid products on page {page}")
        
        return products

    def _extract_product_info(self, container) -> Optional[Product]:
        """Extract product information from a product container"""
        try:
            # Product name - from h3.name
            name_elem = container.find('h3', class_='name')
            name = name_elem.get_text(strip=True) if name_elem else "N/A"
            
            # Product URL - from a.core href
            link_elem = container.find('a', class_='core')
            product_url = urljoin(self.base_url, link_elem['href']) if link_elem else "N/A"
            
            # Price information - using exact Jumia structure
            price = "N/A"
            original_price = "N/A"
            discount = "N/A"
            
            # Current price - from div.prc
            price_div = container.find('div', class_='prc')
            if price_div:
                price = price_div.get_text(strip=True)
            
            # Original price (crossed out) - from div.old inside div.s-prc-w
            s_prc_w = container.find('div', class_='s-prc-w')
            if s_prc_w:
                old_price = s_prc_w.find('div', class_='old')
                if old_price:
                    original_price = old_price.get_text(strip=True)
                
                # Discount percentage - from div.bdg._dsct._sm
                discount_elem = s_prc_w.find('div', class_='bdg _dsct _sm')
                if discount_elem:
                    discount = discount_elem.get_text(strip=True)
            
            # Rating and reviews - from div.rev
            rating = "N/A"
            reviews_count = "N/A"
            
            rev_div = container.find('div', class_='rev')
            if rev_div:
                # Rating from div.stars._s text content (e.g. "4.2 out of 5")
                stars_div = rev_div.find('div', class_='stars _s')
                if stars_div:
                    stars_text = stars_div.get_text(strip=True)
                    # Extract rating like "4.2 out of 5" -> "4.2/5"
                    rating_match = re.search(r'([\d.]+)\s+out\s+of\s+5', stars_text)
                    if rating_match:
                        rating = f"{rating_match.group(1)}/5"
                
                # Reviews count from text in parentheses like "(487)"
                reviews_text = rev_div.get_text()
                reviews_match = re.search(r'\((\d+)\)', reviews_text)
                if reviews_match:
                    reviews_count = f"{reviews_match.group(1)} reviews"
            
            # Image URL - from img data-src or src
            img_elem = container.find('img', class_='img')
            image_url = "N/A"
            if img_elem:
                image_url = (img_elem.get('data-src') or 
                           img_elem.get('src'))
                
                if image_url and image_url.startswith('data:image'):
                    # Handle lazy loading placeholder - get data-src instead
                    image_url = img_elem.get('data-src') or "N/A"
                
                if image_url and image_url != "N/A" and not image_url.startswith('http'):
                    image_url = urljoin(self.base_url, image_url)
            
            # Brand extraction - from data attributes or name
            brand = "N/A"
            
            # Try to get brand from data-ga4-item_brand attribute
            if link_elem and link_elem.get('data-ga4-item_brand'):
                brand = link_elem.get('data-ga4-item_brand')
            else:
                # Extract from name if data attribute not available
                if name != "N/A":
                    name_words = name.split()
                    if name_words:
                        potential_brand = name_words[0].upper()
                        known_brands = ['SAMSUNG', 'XIAOMI', 'INFINIX', 'TECNO', 'ITEL', 'OPPO', 'REALME', 
                                      'NOKIA', 'HUAWEI', 'APPLE', 'ONEPLUS', 'VILLAON', 'OALE', 'POCO', 
                                      'BLACKVIEW', 'FREEYOND', 'MAXFONE']
                        if potential_brand in known_brands:
                            brand = potential_brand
            
            # Category - from data attributes or default
            category = "Mobile Phones"
            if link_elem and link_elem.get('data-ga4-item_category4'):
                category = link_elem.get('data-ga4-item_category4')
            
            # Shipping info - look for shipping related elements
            shipping_info = "N/A"
            shipping_elem = container.find('div', class_='bdg _dsc _sm')
            if shipping_elem and 'free' in shipping_elem.get_text().lower():
                shipping_info = "Free shipping"
            elif container.find(string=re.compile(r'free.*ship', re.I)):
                shipping_info = "Free shipping"
            
            # Badges - collect various promotional badges
            badges = []
            
            # Look for discount badges
            if discount != "N/A":
                badges.append(f"Discount: {discount}")
            
            # Look for special offers
            badge_elements = container.find_all('div', class_='bdg')
            for badge_elem in badge_elements:
                badge_text = badge_elem.get_text(strip=True)
                if badge_text and badge_text not in [discount]:  # Don't duplicate discount
                    badges.append(badge_text)
            
            # Look for "Official Store" or similar badges
            if container.find(string=re.compile(r'official.*store', re.I)):
                badges.append("Official Store")
            
            # Look for "Verified" badges
            if container.find(string=re.compile(r'verified', re.I)):
                badges.append("Verified")
            
            # Look for "Best Seller" or "Popular" badges
            if container.find(string=re.compile(r'best.*seller|popular', re.I)):
                badges.append("Best Seller")
            
            return Product(
                name=name,
                price=price,
                original_price=original_price,
                discount=discount,
                rating=rating,
                reviews_count=reviews_count,
                image_url=image_url,
                product_url=product_url,
                brand=brand,
                category=category,
                shipping_info=shipping_info,
                badges=badges
            )
            
        except Exception as e:
            logger.error(f"Error extracting product info: {e}")
            return None

    def debug_page_structure(self, query: str = "phone", max_products: int = 3):
        """Debug method to analyze Jumia's current page structure"""
        search_url = f"{self.base_url}/catalog/?q={query}"
        logger.info(f"Debugging page structure: {search_url}")
        
        soup = self._make_request(search_url)
        if not soup:
            logger.error("Could not fetch page for debugging")
            return
        
        # Find product containers with different possible selectors
        possible_selectors = [
            'article.prd',
            'div.prd', 
            '[data-catalog-product-item]',
            '.product-item',
            '.item',
            '[class*="product"]'
        ]
        
        for selector in possible_selectors:
            containers = soup.select(selector)
            if containers:
                logger.info(f"Found {len(containers)} products with selector: {selector}")
                
                # Analyze first few products
                for i, container in enumerate(containers[:max_products]):
                    logger.info(f"\n--- Product {i+1} Structure ---")
                    
                    # Show all classes and main structure
                    logger.info(f"Container classes: {container.get('class', [])}")
                    
                    # Find potential price elements
                    price_elements = container.find_all(string=lambda text: text and 'KSh' in text)
                    if price_elements:
                        logger.info(f"Price elements found: {len(price_elements)}")
                        for j, price in enumerate(price_elements[:2]):
                            parent = price.parent
                            logger.info(f"Price {j+1}: '{price.strip()}' in tag: {parent.name} with classes: {parent.get('class', [])}")
                    
                    # Find all links
                    links = container.find_all('a', href=True)
                    if links:
                        logger.info(f"Found {len(links)} links")
                        for link in links[:2]:
                            logger.info(f"Link: {link.get('href')} with classes: {link.get('class', [])}")
                    
                    # Find images
                    images = container.find_all('img')
                    if images:
                        logger.info(f"Found {len(images)} images")
                        for img in images[:1]:
                            logger.info(f"Image src: {img.get('src')} data-src: {img.get('data-src')}")
                
                break
        else:
            logger.warning("No product containers found with any selector")
            # Show page structure
            logger.info("Page title:", soup.title.get_text() if soup.title else "No title")
            logger.info("Main content classes:", [div.get('class') for div in soup.find_all('div')[:10]])

    def get_product_details(self, product_url: str) -> Dict[str, Any]:
        """Get detailed information for a specific product"""
        soup = self._make_request(product_url)
        if not soup:
            return {}
        
        details = {}
        
        try:
            # Product description
            desc_elem = soup.find('div', class_='markup')
            if desc_elem:
                details['description'] = desc_elem.get_text(strip=True)
            
            # Specifications
            specs = {}
            spec_section = soup.find('section', class_='card-b')
            if spec_section:
                spec_rows = spec_section.find_all('tr')
                for row in spec_rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        specs[key] = value
            
            details['specifications'] = specs
            
            # Additional images
            img_elements = soup.find_all('img', class_='thumb')
            image_urls = []
            for img in img_elements:
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    image_urls.append(urljoin(self.base_url, img_url))
            details['additional_images'] = image_urls
            
        except Exception as e:
            logger.error(f"Error extracting product details: {e}")
        
        return details

    def save_to_csv(self, products: List[Product], filename: str = "jumia_products.csv"):
        """Save products to CSV file"""
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'price', 'original_price', 'discount', 'rating', 
                         'reviews_count', 'image_url', 'product_url', 'brand', 'category',
                         'shipping_info', 'badges']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for product in products:
                writer.writerow({
                    'name': product.name,
                    'price': product.price,
                    'original_price': product.original_price,
                    'discount': product.discount,
                    'rating': product.rating,
                    'reviews_count': product.reviews_count,
                    'image_url': product.image_url,
                    'product_url': product.product_url,
                    'brand': product.brand,
                    'category': product.category,
                    'shipping_info': product.shipping_info,
                    'badges': '; '.join(product.badges) if product.badges else ''
                })
        
        logger.info(f"Saved {len(products)} products to {filename}")

    def save_to_json(self, products: List[Product], filename: str = "jumia_products.json"):
        """Save products to JSON file"""
        products_dict = []
        for product in products:
            products_dict.append({
                'name': product.name,
                'price': product.price,
                'original_price': product.original_price,
                'discount': product.discount,
                'rating': product.rating,
                'reviews_count': product.reviews_count,
                'image_url': product.image_url,
                'product_url': product.product_url,
                'brand': product.brand,
                'category': product.category,
                'shipping_info': product.shipping_info,
                'badges': product.badges
            })
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(products_dict, jsonfile, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(products)} products to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Scrape products from Jumia')
    parser.add_argument('--search', type=str, help='Search query for products')
    parser.add_argument('--category-url', type=str, help='Category URL to scrape')
    parser.add_argument('--pages', type=int, default=5, help='Number of pages to scrape (default: 5)')
    parser.add_argument('--output', type=str, default='jumia_products', help='Output filename (without extension)')
    parser.add_argument('--format', type=str, choices=['csv', 'json', 'both'], default='csv', 
                       help='Output format (default: csv)')
    parser.add_argument('--delay', type=float, nargs=2, default=[1, 3], 
                       help='Delay range between requests in seconds (default: 1 3)')
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = JumiaScraper(delay_range=tuple(args.delay))
    
    products = []
    
    if args.search:
        logger.info(f"Searching for: {args.search}")
        products = scraper.search_products(args.search, max_pages=args.pages)
    elif args.category_url:
        logger.info(f"Scraping category: {args.category_url}")
        products = scraper.scrape_category(args.category_url, max_pages=args.pages)
    else:
        logger.error("Please provide either --search or --category-url")
        return
    
    if not products:
        logger.info("No products found")
        return
    
    logger.info(f"Total products scraped: {len(products)}")
    
    # Save results
    if args.format in ['csv', 'both']:
        scraper.save_to_csv(products, f"{args.output}.csv")
    
    if args.format in ['json', 'both']:
        scraper.save_to_json(products, f"{args.output}.json")

if __name__ == "__main__":
    main()

# Example usage:
"""
# Search for phones
python jumia_scraper.py --search "smartphone" --pages 3 --format both

# Scrape a specific category
python jumia_scraper.py --category-url "https://www.jumia.co.ke/phones/" --pages 2

# Custom delay and output
python jumia_scraper.py --search "laptop" --delay 2 5 --output my_laptops

# Debug the page structure to find correct selectors
if __name__ == "__main__":
    # Uncomment the lines below to debug page structure
    # scraper = JumiaScraper()
    # scraper.debug_page_structure("phone")
"""