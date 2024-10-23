import requests
import csv
from urllib.parse import urlparse

def check_url_status(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        return response.status_code, response.url
    except requests.RequestException:
        return None, url

def main():
    input_file = 'urls.csv'  # Assume the URLs are in a CSV file
    output_file = 'url_status_results.csv'

    with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        writer.writerow(['Original URL', 'Status Code', 'Final URL'])

        for row in reader:
            url = row[0].strip()
            status_code, final_url = check_url_status(url)
            
            writer.writerow([url, status_code, final_url])
            print(f"Checked: {url} - Status: {status_code}")

    print(f"Results have been saved to {output_file}")

if __name__ == "__main__":
    main()