import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd

# Function to fetch and parse a single sitemap
def fetch_sitemap(sitemap_url):
    response = requests.get(sitemap_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, features='xml')  # Use 'xml' parser
        urls = [loc.text for loc in soup.find_all('loc')]
        return urls
    else:
        print(f"Failed to retrieve sitemap from {sitemap_url}")
        return []

# Function to fetch and parse multiple sitemaps
def fetch_all_sitemaps(base_url, sitemap_urls):
    all_urls = []
    for sitemap_url in sitemap_urls:
        full_sitemap_url = urljoin(base_url, sitemap_url)
        sitemap_urls = fetch_sitemap(full_sitemap_url)
        all_urls.extend(sitemap_urls)
    return all_urls

# List of sitemap URLs
sitemap_urls = [
    'https://drmatlock.com/post-sitemap.xml',
    'https://drmatlock.com/page-sitemap.xml',
    'https://drmatlock.com/press-and-media-sitemap.xml',
    'https://drmatlock.com/metform-form-sitemap.xml',
    'https://drmatlock.com/category-sitemap.xml',
    'https://drmatlock.com/post_tag-sitemap.xml',
    'https://drmatlock.com/author-sitemap.xml'
]

# Base URL of the website
base_url = 'https://drmatlock.com/'

# Fetch the URLs from all sitemaps
all_urls = fetch_all_sitemaps(base_url, sitemap_urls)

# Remove the base URL and categorize
base_to_remove = "https://drmatlock.com/"
categorized_urls = {"body": [], "face": [], "breast": [], "blog": []}

for url in all_urls:
    path = url.replace(base_to_remove, "")
    if "blog" in path:
        categorized_urls["blog"].append(path)
    elif any(keyword in path for keyword in ["body", "liposuction", "mommy-makeover", "tummy-tuck"]):
        categorized_urls["body"].append(path)
    elif any(keyword in path for keyword in ["face", "neck-lift", "blepharoplasty", "rhinoplasty", "brow-lift", "otoplasty", "facelift"]):
        categorized_urls["face"].append(path)
    elif any(keyword in path for keyword in ["breast", "breast-augmentation", "breast-reduction", "breast-lift", "breast-reconstruction"]):
        categorized_urls["breast"].append(path)

# Create a dataframe and set the new URLs
new_base = "/plastic-surgery-los-angeles/"
data = []

for category, paths in categorized_urls.items():
    for path in paths:
        old_url = urljoin(base_url, path)
        new_url = f"{new_base}{category}/{path.strip('/')}"
        data.append({"Category": category.capitalize(), "Old URL": old_url, "New URL": new_url})

df = pd.DataFrame(data)

# Format the Excel output to include categories
with pd.ExcelWriter('categorized_urls.xlsx', engine='openpyxl') as writer:
    for category in df['Category'].unique():
        category_df = df[df['Category'] == category][['Old URL', 'New URL']]
        category_df.to_excel(writer, sheet_name=category, index=False)

print(f"URLs have been categorized and written to categorized_urls.xlsx")
