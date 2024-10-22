import time
import os
import re
import logging
import requests
from urllib.parse import urlparse, urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ImageScraper:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.downloads_folder = self.base_dir / 'downloads'
        self.raw_folder = self.downloads_folder / 'raw'
        self.processed_folder = self.downloads_folder / 'processed'
        self._setup_folders()
        
    def _setup_folders(self):
        """Create necessary folders if they don't exist."""
        self.downloads_folder.mkdir(exist_ok=True)
        self.raw_folder.mkdir(exist_ok=True)
        self.processed_folder.mkdir(exist_ok=True)

    def download_image(self, url, filename):
        """Download image with improved headers and error handling."""
        max_retries = 3
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://newimage-plasticsurgery.com/',
            'Connection': 'keep-alive',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Dest': 'image',
        }
        
        for attempt in range(max_retries):
            try:
                session = requests.Session()
                # First make a HEAD request to the main site
                session.head('https://newimage-plasticsurgery.com/', headers=headers)
                time.sleep(0.5)  # Small delay between requests
                
                # Then get the image
                response = session.get(url, timeout=15, headers=headers)
                response.raise_for_status()
                
                if int(response.headers.get('content-length', 0)) < 1000:  # Check if response is too small
                    raise ValueError("Response too small, likely an error page")
                
                filepath = self.raw_folder / filename
                filepath.write_bytes(response.content)
                return True
                
            except Exception as e:
                if attempt == max_retries - 1:
                    logging.error(f"Failed to download {url}: {str(e)}")
                    return False
                time.sleep(2)  # Longer wait between retries

    def process_image(self, input_path, base_filename, crop_height=50):
        """Process image with error handling."""
        try:
            with Image.open(input_path) as img:
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                width, height = img.size
                
                if width < 100 or height < 100:
                    logging.warning(f"Image {input_path} too small to process")
                    return False
                
                left_half = img.crop((0, 0, width // 2, height))
                right_half = img.crop((width // 2, 0, width, height))
                
                safe_crop_height = min(crop_height, height // 4)
                
                for side, half in [("left", left_half), ("right", right_half)]:
                    cropped = half.crop((0, 0, half.width, height - safe_crop_height))
                    output_path = self.processed_folder / f"{base_filename}_{side}_cropped.jpg"
                    cropped.save(output_path, "JPEG", quality=95)
                
                return True
                
        except Exception as e:
            logging.error(f"Error processing {input_path}: {str(e)}")
            return False

    @staticmethod
    def clean_filename(filename):
        """Create a clean, safe filename."""
        safe_filename = re.sub(r'[^\w\-_\. ]', '_', filename)
        if len(safe_filename) > 255:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:240] + ext
        return safe_filename

    @staticmethod
    def extract_case_number(src):
        """Extract case number from image source URL."""
        patterns = [
            r'case[_-]?(\d+)',
            r'cases[_-]?(\d+)',
            r'case(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, src.lower())
            if match:
                return match.group(1)
        return 'unknown'

    def scrape_images(self, url, driver):
        """Main scraping function with improved image collection."""
        logging.info(f"Scraping URL: {url}")
        driver.get(url)
        time.sleep(3)  # Allow more time for initial page load

        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        procedure_name = parsed_url.path.split('/')[-2].replace('-', ' ').title()
        
        try:
            wait = WebDriverWait(driver, 10)
            # Wait for owl-stage to be present and visible
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'owl-stage')))
            
            # Get all owl-items using JavaScript
            script = """
            return Array.from(document.querySelectorAll('.owl-item')).map(item => {
                const img = item.querySelector('img');
                return img ? img.getAttribute('src') : null;
            }).filter(src => src);
            """
            image_srcs = driver.execute_script(script)
            
            total_images = 0
            processed_images = 0
            processed_urls = set()
            
            for src in image_srcs:
                try:
                    if not src or src in processed_urls:
                        continue
                        
                    processed_urls.add(src)
                    full_src = urljoin(base_url, src)
                    case_number = self.extract_case_number(src)
                    base_name = os.path.basename(full_src)
                    filename = f"{procedure_name}_case_{case_number}_{base_name}"
                    filename = self.clean_filename(filename)
                    
                    raw_path = self.raw_folder / f"raw_{filename}"
                    
                    logging.info(f"Attempting to download: {full_src}")
                    if self.download_image(full_src, f"raw_{filename}"):
                        total_images += 1
                        base_filename = Path(filename).stem
                        
                        if self.process_image(raw_path, base_filename):
                            processed_images += 1
                        
                        raw_path.unlink(missing_ok=True)
                        logging.info(f"Successfully processed: {filename}")
                    else:
                        logging.error(f"Failed to download: {full_src}")
                        
                except Exception as e:
                    logging.error(f"Error processing image: {str(e)}")
                    continue

            logging.info(f"Procedure: {procedure_name}")
            logging.info(f"Total images attempted: {total_images}")
            logging.info(f"Successfully processed: {processed_images}")
            logging.info(f"Images saved in: {self.processed_folder}")
            
        except Exception as e:
            logging.error(f"Error during scraping: {str(e)}")

def main():
    url = "https://newimage-plasticsurgery.com/before-after/breast-augmentation/"  # Updated URL for testing
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    scraper = ImageScraper()

    try:
        scraper.scrape_images(url, driver)
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()