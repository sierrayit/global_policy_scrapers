"""Download all laws from the Indian website."""
from datetime import date
import re
import csv
import json
from os import path

from bs4 import BeautifulSoup

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

START_URL = 'https://www.indiacode.nic.in/handle/123456789/1362/browse?type=actno'
BASE_URL = 'https://www.indiacode.nic.in/'
DOWNLOAD_PATH = '../data/india/pdf'
WEB_DRIVER_PATH = '/usr/local/bin/chromedriver'

ACT_PAGES = []
PDF_PAGES = []

METADATA = []
METADATA_PATH = '../data/india/metadata.json'

def collect_links_from_main_page(link_page):
    """Collects links from the main page."""
    response = requests.get(link_page)
    print("Gathering links from page " + link_page)
    html = BeautifulSoup(response.text, features="lxml")

    next_page = ''
    for link in html.find_all('a'):
        if link.has_attr('href'):
            act_search = re.search(
                r'/handle/123456789/1362/browse\?type=actno&order=ASC&rpp=20&value=[0-9]+',
                link['href'])
            if act_search is not None:
                ACT_PAGES.append(link['href'].replace('rpp=20','rpp=100'))
                continue

            # check if this is the link to the next page of results
            if link.has_attr('class') and link['class'][0] == "pull-right":
                next_page = BASE_URL + link['href']
    return next_page


def collect_links_from_act_page(driver, act_page):
    """Collects links on individual act pages."""
    print("gathering pdf page links from act page " + act_page)
    driver.get(act_page)

    atags = driver.find_elements_by_tag_name('a')
    for atag in atags:
        href = atag.get_attribute('href')
        if href is None:
            continue
        href_search = re.search(
            r'https://www.indiacode.nic.in/handle/123456789/[0-9]+\?'
            'view_type=browse&sam_handle=123456789/1362', href)
        if href_search is not None:
            PDF_PAGES.append(href)


def write_pdf(link, dest):
    """Saves the pdf."""
    if path.exists(dest):
        print("already downloaded")
        return

    print("Saving pdf from ", link, " to ", dest)
    success = False
    for _ in range(1,10):
        try:
            request = requests.get(link, timeout=10, stream=True)
            success = True
        except:
            continue
        break

    if not success:
        print("error getting pdf from link")
        return

    # Open the output file and make sure we write in binary mode
    with open(dest, 'wb') as file_handle:
        # Walk through the request response in chunks of 1024 * 1024 bytes, so 1MiB
        for chunk in request.iter_content(1024 * 1024):
            # Write the chunk to the file
            file_handle.write(chunk)


def download_pdf_from_page(pdf_page):
    """Downloads the pdf from a page."""
    response = requests.get(pdf_page)
    print("gathering pdf from page " + pdf_page)
    html = BeautifulSoup(response.text, features="lxml")

    short_title = ''
    for tag in html.find_all('p'):
        if tag.has_attr('id'):
            if tag['id'] == 'short_title':
                short_title = tag.text.lower().replace(" ", "-").replace(",","")
                break
    download_dest = download_path + '/' + short_title + ".pdf"

    pdf_link = ''
    for tag in html.find_all('a'):
        if tag.has_attr('href'):
            pdf_search = re.search('/bitstream/123456789/.*/.*/.*.pdf', tag['href'])
            if pdf_search is not None:
                pdf_link = BASE_URL + tag['href']
                break

    if pdf_link == '' or short_title == '':
        print("Unable to find short title or pdf link, returning")
    METADATA.append({'title': short_title, 'link': pdf_link, 'download_path': download_dest,
                     'download_date':date.today().strftime('%Y-%m-%d')})
    write_pdf(pdf_link, download_dest)


def scrape_intermediate_links_to_csv():
    """Writes all links to follow to a csv file."""
    link_page = START_URL
    while link_page != '':
        link_page = collect_links_from_main_page(link_page)

    options = Options()
    options.headless = True
    options.add_argument("--window-size=1920,1200")

    driver = webdriver.Chrome(options=options, executable_path=WEB_DRIVER_PATH)
    for act_page in ACT_PAGES:
        collect_links_from_act_page(driver, BASE_URL + act_page)

    with open('india_pdf_pages.csv', 'w', newline='') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=' ',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for pdf_page in PDF_PAGES:
            spamwriter.writerow([pdf_page])


def download_pdfs_from_links_in_csvfile():
    """Reads the links from the csvfile and downloads all laws from those links."""
    pdf_pages = []
    with open('india_pdf_pages.csv', 'r', newline='') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
        for row in spamreader:
            pdf_pages.append(row[0])

    for pdf_page in pdf_pages:
        download_pdf_from_page(pdf_page)


def write_metadata_json():
    """Write out the metadata file."""
    print('Writing scraper metadata json')
    with open(METADATA_PATH, 'w') as jsonfile:
        json.dump(METADATA)


def scrape_india_laws():
    """Scrapes all laws from the START_URL."""
    # This step takes a long time. Prefer to run this first, then comment out
    # this line and run the Download stage.
    scrape_intermediate_links_to_csv()
    download_pdfs_from_links_in_csvfile()
    write_metadata_json()


if __name__ == '__main__':
    scrape_india_laws()
