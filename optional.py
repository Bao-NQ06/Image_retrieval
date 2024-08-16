from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse 
import urllib.request 
import time 
import os 
from tqdm import tqdm 
import concurrent.futures
import json 
from PIL import Image 

import shutil
from collections import defaultdict

URL = "https://www.flickr.com/search/?text="
term = 'cat'

class UrlScraper:

    def __init__(self, url_template, max_images=50, max_workers=4):
        self.url_template = url_template 
        self.max_images = max_images
        self.max_workers = max_workers
        self.setup_environment()
        
    def setup_environment(self):
        os.environ['PATH'] += ':/usr/lib/chromium-browser/'
        os.environ['PATH'] += ':/usr/lib/chromium-browser/chromedriver/'
        
        
    def get_url_images(self, term):
        """
        Crawl the urls of images by term

        Parameters:
        term (str): The name of animal, plant, scenery, furniture

        Returns:
        urls (list): List of urls of images
        """

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=options)
        url = self.url_template.format(search_term=term)
        driver.get(url) 

        urls = []
        more_content_available = True 

        pbar = tqdm(total=self.max_images, desc=f"Fetching images for {term}")
        
        while len(urls) < self.max_images and more_content_available:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            img_tags = soup.find_all("img")

            # Extract url image from HTML source
            for img in img_tags:
                if len(urls) >= self.max_images:
                    break
                if 'src' in img.attrs:
                    href = img.attrs['src']
                    img_path = urljoin(url, href)
                    img_path = img_path.replace("_m.jpg", "_b.jpg").replace("_n.jpg", "_b.jpg").replace("_w.jpg", "_b.jpg")
                    if img_path == "https://combo.staticflickr.com/ap/build/images/getty/IStock_corporate_logo.svg":
                        continue
                    urls.append(img_path)
                    pbar.update(1)

            # Click load more button or scroll page for more image
            try:
                load_more_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[@id="yui_3_16_0_1_1721642285931_28620"]'))
                )
                load_more_button.click()
                time.sleep(2) # Wait for generating content
            
            except Exception as E:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2) # Wait for generating content

                # Check number of new generating image
                new_soup = BeautifulSoup(driver.page_source, "html.parser")
                new_img_tags = new_soup.find_all("img", loading_="lazy")
                if len(new_img_tags) == len(img_tags):
                    more_content_available = False
                img_tags = new_img_tags
        pbar.close()
        driver.quit()
        return urls
    
    def scrape_urls(self, categories):
        """
        Call get_url_images method to get all urls of any object in categories\

        Parameter:
        categories (dictionary): the dict of all object we need to collect image with format
        tegories{"name_object": [value1, value2, ...]}

        Returns:
        all_urls (dictionary): Dictionary of urls of images
        """
        all_urls = {category: {} for category in categories}

        # Handle multi-threading for efficent installation
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_term = {executor.submit(self.get_url_images, term): (category, term)
            for category, terms in categories.items() for term in terms}

            for future in tqdm(concurrent.futures.as_completed(future_to_term), total=len(future_to_term), desc="Overall Progress"):
                category, term = future_to_term[future]
                try:
                    urls = future.result()
                    all_urls[category][term] = urls
                    print(f"\nNumber of images retrieved for {term}: {len(urls)}")
                except Exception as exc:
                    print(f"\n{term} generated an exception: {exc}")
        return all_urls
    
    
    def save_to_file(self, data, filename):
        """
        Save the data to a JSON file.

        Parameters:
        data (dict): The data to be saved.
        filename (str): The name of the JSON file.

        Returns:
        None
        """
        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)
        print(f"Data saved to {filename}")
        
categories = {"animal": ["Monkey", "Elephant", "cows", "Cat", "Dog", "bear", "fox", "Civet", "Pangolins"
, "Rabbit", "Bats", "Whale", "Cock", "Owl", "flamingo", "Lizard", "Turtle", "Snake", "Frog", "Fish", "shrimp", "Crab", "Snail", "Coral", "Jellyfish", "Butterfly", "Flies",
"Mosquito", "Ants", "Cockroaches", "Spider", "scorpion", "tiger", "bird", "horse", "pig", "Alligator", "Alpaca", "Anteater", "donkey", "Bee", "Buffalo", "Camel", "Caterpillar", 
"Cheetah", "Chicken", "Dragonfly", "Duck", "panda", "Giraffe"],
"plant": ["Bamboo", "Apple", "Apricot", "Banana", "Bean", 
          "Wildflower", "Flower", "Mushroom", "Weed", "Fern", "Reed", "Shrub", "Moss", "Grass", "Palmtree", "Corn", "Tulip", "Rose", "Clove", 
          "Dogwood", "Durian", "Ferns", "Fig", "Flax", "Frangipani", "Lantana", "Hibiscus", "Bougainvillea", "Pea", "OrchidTree", "RangoonCreeper", 
          "Jackfruit", "Cottonplant", "Corneliantree", "Coffeeplant", "Coconut", "wheat", "watermelon", "radish", "carrot"],
"furniture": ["bed", "cabinet", "chair", "chests", "clock", "desks", "table", "Piano", "Bookcase", "Umbrella", "Clothes", "cart", "sofa", "ball", "spoon", "Bowl", "fridge", "pan", "book"],
"scenery": ["Cliff", "Bay", "Coast", "Mountains", "Forests", "Waterbodies", "Lake", "desert", "farmland", "river", "hedges", "plain", "sky", "cave", "cloud", 
            "flowergarden", "glacier", "grassland", "horizon", "lighthouse", "plateau", "savannah", "valley", "volcano", "waterfall"]}


urltopic = {"flickr": "https://www.flickr.com/search/?text={search_term}"}
scraper = UrlScraper(url_template=urltopic["flickr"], max_images=20, max_workers=5)
image_urls = scraper.scrape_urls(categories)
scraper.save_to_file(image_urls, 'image_urls.json')


class ImageDownloader:
    def __init__(self, json_file, download_dir='Dataset', max_workers=4, delay=1):
        self.json_file = json_file 
        self.download_dir = download_dir
        self.max_workers = max_workers
        self.delay = delay

        self.filename = set() 
        self.setup_directory()

    def setup_directory(self):
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
            
    def read_json(self):
        """
        Read the JSON file and return the data.

        Returns:
        data (dict): The data read from the JSON file.
        """
        with open(self.json_file, 'r') as file:
            data = json.load(file)
        return data
    
    
    def is_valid_url(self, url):
        """
        Check if the URL is valid.
        Parameters:
        url (str): The URL to be checked.
        Returns:
        bool: True if the URL is valid, False otherwise.
        """
        try:
            with urllib.request.urlopen(url) as response:
                if response.status == 200 and 'image' in response.info().get_content_type():
                    return True
        except Exception:
            return False
        
        
    def download_image(self, url, category, term, pbar):
        """
        Download the image from the given URL.

        Parameters:
        url (str): The URL of the image to be downloaded.
        category (str): The category of the image.
        term (str): The term or keyword associated with the image.
        pbar (tqdm): The progress bar object.

        Returns:
        str: A message indicating the status of the download.
        """
        if not self.is_valid_url(url):
            pbar.update(1)
            return f"Invalid URL: {url}"
 
        category_dir = os.path.join(self.download_dir, category)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)

        term_dir = os.path.join(category_dir, term)
        if not os.path.exists(term_dir):
            os.makedirs(term_dir)

        filename = os.path.join(term_dir, os.path.basename(urlparse(url).path))

        self.filename.add(filename) # Record the filename directory

        try:
            urllib.request.urlretrieve(url, filename)
            pbar.update(1)
            return f"Downloaded: {url}"
        except Exception as e:
            pbar.update(1)
            return f"Failed to download {url}: {str(e)}"
    
    def export_filename(self):
        """
        Export the filename directories to a text file.

        Returns:
        None
        """
        with open('filename.txt', 'w') as file:
            for filename in sorted(self.filename):
                file.write(f"{filename}\n")
        
    def download_images(self):
        """
        Download images from the JSON file.

        Returns:
        None
        """
        data = self.read_json()
        download_tasks = []

        total_images = sum(len(urls) for terms in data.values() for urls in terms.values())
        with tqdm(total=total_images, desc="Downloading images") as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:       
                for category, terms in data.items():
                    for term, urls in terms.items():
                        for url in urls:
                            download_tasks.append(executor.submit(self.download_image, url,category, term, pbar))       
                            time.sleep(self.delay) # Polite delay
        
                for future in concurrent.futures.as_completed(download_tasks):
                    print(future.result())
        
        self.export_filename()

downloader = ImageDownloader(json_file='image_urls.json', download_dir='Dataset', max_workers=4, delay=1)
downloader.download_images()
downloader.export_filename()



def check_and_preprocess_images(image_dir):
    for root, _, files in os.walk(image_dir):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with Image.open(file_path) as img:
                # Check if image is smaller than 50x50 pixels
                    if img.size[0] < 50 or img.size[1] < 50:
                        os.remove(file_path)
                        print(f"Deleted {file_path}: Image too small ({img.size[0]}x{img.size[1]})")
                        continue

                    # Convert non-RGB images to RGB
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                        img.save(file_path)
                        print(f"Converted {file_path} to RGB")

            except Exception as e:
            # If file is not an image, delete it
                os.remove(file_path)
                print(f"Deleted {file_path}: Not an image or corrupted file ({str(e)})")

check_and_preprocess_images('Dataset')


source_dir = "Dataset"
train_dir = "data/train"
test_dir = "data/test"


os.makedirs(train_dir, exist_ok=True)
os.makedirs(test_dir, exist_ok=True)

# Initialize a dictionary to hold file paths for each class
class_files = defaultdict(list)

# Read the file paths from the text file
with open('filename.txt', 'r') as file:
    lines = file.readlines()
    for line in lines:
        line = line.strip()
        if line:
    # Extract the class name from the path
            parts = line.split('/')
            class_name = parts[2] # Structure Dataset/category/class/image.jpg
            class_files[class_name].append(line)
class_files

# Move images to the train and test directories
for class_name, files in class_files.items():
    # Create the train and test directories for the class
    train_class_dir = os.path.join(train_dir, class_name)
    test_class_dir = os.path.join(test_dir, class_name)
    os.makedirs(train_class_dir, exist_ok=True)
    os.makedirs(test_class_dir, exist_ok=True)

    # Move 19 images to train and 1 image to test
    for i, file_path in enumerate(files):
        if i == 0:
            shutil.copy(file_path, test_class_dir)
        elif i < 20:
            shutil.copy(file_path, train_class_dir)

print("Dataset organization complete!")