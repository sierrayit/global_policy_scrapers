"""Download all laws from a China policy website."""

from datetime import date
import json
from os import link, path
from pathlib import Path
import re

from bs4 import BeautifulSoup, SoupStrainer
import requests

START_URL = 'http://www.gov.cn/flfg/index.htm'
BASE_URL = 'http://www.gov.cn'
METADATA = []
METADATA_PATH = '../data/china/metadata.json'
DOWNLOAD_DIR = '../data/china/'

def collect_links_from_main_page():
    """Create a list of links from the START_URL."""
    law_pages = []
    print('Starting to request...')
    response = requests.get(START_URL)
    print('Got response!')
    response.encoding = 'utf-8' # assign encoding for Simplified Chinese character
    html = BeautifulSoup(response.text, 'html.parser')

    for link in html.find_all('a'):
        if link.has_attr('href'):
            search = re.search('/flfg/', link['href'])
            if search is not None:
                full_link = BASE_URL + link['href']
                law_title = link.text
                if full_link == START_URL:
                    continue
                law_pages.append((full_link, law_title))
    return law_pages

def download_multiple_pdf(pdf_path, link_list):
    """Use if a law page contains more than one pdf links"""
    print('Found multiple pdf in one page...')
    for iter, link in enumerate(link_list):
        filename = pdf_path[:-4] + '_' + str(iter) + '_' + link.text + '.pdf'
        http_link = link['title']
        print('Saving pdf from ', http_link, ' to ', filename)

        for _ in range(1,10):
            try:
                request = requests.get(http_link, timeout=10, stream=True)
            except Exception as e:
                print(e)
                continue
            break

        # Open output file. Write in binary mode
        with open(filename, 'wb') as file_handle:
            for chunk in request.iter_content(1024 * 1024):
                file_handle.write(chunk) 

def download_pdf(pdf_path, page_soup):
    """Search for pdf in the page, download pdf. Return true if found, else return false."""
    link = page_soup.find_all(href=re.compile('pdf'))
    if link != []:
        if len(link) == 1:
            filename = pdf_path
            http_link = link[0]['title']
            print('Saving pdf from ', http_link, ' to ', filename)

            for _ in range(1,10):
                try:
                    request = requests.get(http_link, timeout=10, stream=True)
                except Exception as e:
                    print(e)
                    continue
                break

            # Open the output file. Write in binary mode
            with open(filename, 'wb') as file_handle:
                for chunk in request.iter_content(1024 * 1024):
                    file_handle.write(chunk)
        else:
            download_multiple_pdf(pdf_path, link)
        return True
    return False

def download_text(page, filename):
    """Parse page to get law text (p tag only) and write to txt file."""
    print('Saving law text from page')
    soup_p = BeautifulSoup(page.text, 'html.parser', parse_only=SoupStrainer('p'))
    law_text = soup_p.get_text()
    with open(filename, 'a', encoding='utf-8') as file:
        file.write(law_text)
        file.close()

def write_metadata_json():
    """Write the metadata file."""
    print('Writing metadata to json.')
    with open(METADATA_PATH, 'w', encoding='utf-8') as file:
        json.dump(METADATA, file, ensure_ascii=False)

def scrape_china_laws():
    """Download all laws from the China Policy webpage."""
    Path(f'{DOWNLOAD_DIR}pdf').mkdir(parents=True, exist_ok=True)
    Path(f'{DOWNLOAD_DIR}txt').mkdir(parents=True, exist_ok=True)

    law_pages = collect_links_from_main_page()

    for link, law_title in law_pages:
        print('Scraping law from link ' + link)

        for _ in range(1, 10):
            try:
                page = requests.get(link, timeout=10)
            except Exception as e:
                print(e)
                continue
            break
        
        # Indicate encoding for Simplified Chinese characters
        page.encoding = 'utf-8'
        soup = BeautifulSoup(page.text, 'html.parser')
        pdf_path = DOWNLOAD_DIR + 'pdf/' + law_title + '.pdf'
        txt_path = DOWNLOAD_DIR + 'txt/' + law_title + '.txt'

        if path.exists(pdf_path) or path.exists(txt_path):
            print('Already downloaded.')
            continue

        # First search if pdf file exists. If yes, download pdf.
        # Otherwise download the text on the page.
        is_pdf = download_pdf(pdf_path, soup)        
    
        if is_pdf:
            download_path = pdf_path
        else:
            download_path = txt_path
            download_text(page, txt_path)

        METADATA.append({'title': law_title,
                         'link': link,
                         'download_path': download_path,
                         'download_date': date.today().strftime('%Y-%m-%d'),
                         'country': 'China'})

    write_metadata_json()

if __name__ == '__main__':
    scrape_china_laws()


