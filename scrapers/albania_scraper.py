"""Downloads all laws from the Albanian website."""
from datetime import date
import json
from os import path
import re

from bs4 import BeautifulSoup
import requests

START_URL = 'https://euralius.eu/index.php/en/library/albanian-legislation/category/360-laws'
BASE_URL = 'https://euralius.eu'
DOWNLOAD_PATH = '../data/albania/pdf'
METADATA = []
METADATA_PATH = '../data/albania/metadata.json'

def collect_links_from_main_page():
    """Gathers a list of links from the starting page."""
    law_pages = []
    response = requests.get(START_URL)
    html = BeautifulSoup(response.text, features="lxml")

    for link in html.find_all('a'):
        if link.has_attr('href'):
            search = re.search('/index.php/en/library/albanian-legislation/category/[0-9a-zA-z-]+',
                               link['href'])
            if search is not None:
                full_link = BASE_URL + link['href']
                if full_link == START_URL:
                    continue
                law_pages.append(link['href'])
    return law_pages

def find_pdf(soup):
    """Given a beautiful soup object, finds the first pdf 'Download' link."""
    for link in soup.find_all('a'):
        if link.has_attr('href') and link.has_attr('title') and link['title'] == 'Download':
            title = link.text.replace(' ', '-')
            return title, BASE_URL + link['href']

def download_pdf_from_page(link):
    """Parses a page and downloads the pdf from it."""
    # Sometimes requests can fail or time out, so try getting the page multiple times.
    for _ in range(1,10):
        try:
            page = requests.get(BASE_URL + link, timeout=10)
        except:
            continue
        break

    # Parse the title and download link
    soup = BeautifulSoup(page.text, 'html.parser')
    title, pdf_link = find_pdf(soup)
    filename = DOWNLOAD_PATH + '/' + title + '.pdf'
    METADATA.append({'title': title,
                     'link': pdf_link,
                     'download_path': filename,
                     'download_date': date.today().strftime('%Y-%m-%d'),
                     'country': 'Albania',})
    if path.exists(filename):
        print(filename + " already downloaded")
        return

    print("Saving pdf from ", pdf_link, " to ", filename)
    for _ in range(1,10):
        try:
            request = requests.get(pdf_link, timeout=10, stream=True)
            with open(filename, 'wb') as file:
                for chunk in request.iter_content(1024 * 1024):
                    file.write(chunk)
        except:
            continue
        break

def write_metadata_json():
    """Writes the metadata json file."""
    print('Writing metadata to json')
    with open(METADATA_PATH, 'w') as file:
        json.dump(METADATA, file)

def scrape_albania_laws():
    """Scrapes all laws from the START_URL."""
    law_pages = collect_links_from_main_page()
    for link in law_pages:
        print("Scraping law for link " + BASE_URL + link)
        download_pdf_from_page(link)

    write_metadata_json()


if __name__ == '__main__':
    scrape_albania_laws()
