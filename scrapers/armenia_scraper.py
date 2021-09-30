"""Downloads all laws from the Armenian website."""
from datetime import date
import re
import json
from os import path
from pathlib import Path
import httplib2
from bs4 import BeautifulSoup, SoupStrainer
import requests

START_URL = 'http://www.parliament.am/legislation.php?sel=alpha&lang=eng'
BASE_URL = 'http://www.parliament.am'
METADATA = []
METADATA_PATH = '../data/armenia/metadata.json'
DOWNLOAD_DIR = '../data/armenia/'

def collect_links_from_main_page():
    """Create a list of links from the START_URL."""
    law_pages = []
    http = httplib2.Http()
    _, response = http.request(START_URL)
    for link in BeautifulSoup(response, parse_only=SoupStrainer('a'), features="lxml"):
        if link.has_attr('href'):
            search = re.search(r'/legislation\.php\?sel=show&ID=[0-9]+&lang=eng', link['href'])
            if search is not None:
                law_pages.append(BASE_URL + link['href'])
    return law_pages

def download_pdf(pdf_path, html):
    """Search for a pdf on the page and download and return true if found, else returns false."""
    for link_tag in BeautifulSoup(html, parse_only=SoupStrainer('a'), features="lxml"):
        if not link_tag.has_attr('href'):
            continue
        pdf_search = re.search(r'/law_docs/[0-9a-zA-Z]+eng\.pdf', link_tag['href'])
        if pdf_search is None:
            continue
        filename = pdf_path
        http_link = BASE_URL + link_tag['href']
        print("Saving pdf from ", http_link, " to ", filename)

        for _ in range(1,10):
            try:
                request = requests.get(http_link, timeout=10, stream=True)
            except Exception as e:
                print(e)
                continue
            break

        # Open the output file and make sure we write in binary mode
        with open(filename, 'wb') as file_handle:
            # Walk through the request response in chunks of 1024 * 1024 bytes, so 1MiB
            for chunk in request.iter_content(1024 * 1024):
                file_handle.write(chunk)
        return True
    return False

def download_text(law_text, filename):
    """Download a text file."""
    with open(filename, "a") as file:
        file.write(law_text)
        file.close()

def write_metadata_json():
    """Write the metadata file."""
    print('Writing metadata to json')
    with open(METADATA_PATH, 'w') as file:
        json.dump(METADATA, file)

def scrape_armenia_laws():
    """Download all laws from the Armenia website."""
    Path(f'{DOWNLOAD_DIR}pdf').mkdir(parents=True, exist_ok=True)
    Path(f'{DOWNLOAD_DIR}txt').mkdir(parents=True, exist_ok=True)
    law_pages = collect_links_from_main_page()
    for link in law_pages:
        print("Scraping law from link " + link)
        for _ in range(1,10):
            try:
                page = requests.get(link, timeout=10)
            except Exception as e:
                print(e)
                continue
            break

        soup = BeautifulSoup(page.text, 'html.parser')
        heading = soup.find_all('h3')
        # the first h3 is the title
        law_title = heading[0].text.replace(" ", "-")
        pdf_path = DOWNLOAD_DIR + "pdf/" + law_title[:200] + ".pdf"
        txt_path = DOWNLOAD_DIR + 'txt/' + law_title[:200] + '.txt'

        if path.exists(pdf_path) or path.exists(txt_path):
            print("Already downloaded.")
            continue

        # First search for a pdf. Otherwise, download the text on the page.
        is_pdf = download_pdf(pdf_path, page.text)
        if is_pdf:
            download_path = pdf_path
            continue
        download_path = txt_path
        download_text(soup.get_text(), txt_path)

        METADATA.append({'title': law_title,
                         'link': link,
                         'download_path': download_path,
                         'download_date': date.today().strftime('%Y-%m-%d'),
                         'country': 'Armenia'})

    write_metadata_json()

if __name__ == '__main__':
    scrape_armenia_laws()
