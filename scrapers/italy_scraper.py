"""
Summary of the scraping process:

1. Visit https://www.normattiva.it/staticPage/codici, and click on all the links under Costituzione e Codici.
2. For each link (example: https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1930-10-19;1398), 
   click on "atto completo" in the right side Approfondimenti menu.
3. On this page, leave all the options default, and click on Visualizza.
4. Write the text of the code to a txt file.

The server likes to reject requests that don't look like a real browser, and requires an active session to load
most pages, so we use Selenium for everything.
"""

from datetime import date, datetime
import json
from pathlib import Path
import re
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager

DOWNLOAD_PATH = '../data/italy/txt'
METADATA_PATH = '../data/italy/metadata.json'
# The server doesn't send the full certificate chain, so we have to provide it ourselves to avoid
# SSL errors. Downloaded from https://www.ssllabs.com/ssltest/analyze.html?d=www.normattiva.it.
CERTIFICATE_PATH = 'italy_certificate.pem'
BASE_URL = 'https://www.normattiva.it/'
CODES_LIST_URL = f'{BASE_URL}staticPage/codici'
# The server rejects any requests that look like scraping, so we need to use a fake user agent.
# Anything should work as long as it looks like a real browser.
FAKE_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
DATE_FORMAT = '%Y-%m-%d'

def collect_code_urls(driver: WebDriver) -> List[Tuple[str, str]]:
    """Returns a list of (code URL, name of code)"""
    driver.get(CODES_LIST_URL)
    html = BeautifulSoup(driver.page_source, 'lxml')
    return list(map(lambda x: (x['href'], x.text.strip()), html.find_all('a', href=re.compile('uri-res'))))

def download_code(driver: WebDriver, code: Tuple[str, str]) -> Optional[dict]:
    url = code[0]
    # One link is a full URL, the rest are relative
    if not url.startswith('http'):
        url = BASE_URL + url
    metadata = {'title': code[1], 'link': url, 'download_date': date.today().strftime(DATE_FORMAT), 'country': 'Italy'}
    print(f'Downloading {code[1]}')
    driver.get(url)
    try:
        last_updated = re.search("Ultimo aggiornamento all'atto pubblicato il (.*)\)", driver.page_source)
        if last_updated is not None:
            metadata['last_updated'] = datetime.strptime(last_updated.group(1), '%d/%m/%Y').strftime(DATE_FORMAT)
        date_enacted = re.search(r':(\d{4}-\d{2}-\d{2});', driver.current_url)
        if date_enacted is not None:
            metadata['date_enacted'] = date_enacted.group(1)
        else:
            date_enacted = re.search('Entrata in vigore del provvedimento: (.*)\.', driver.page_source)
            metadata['date_enacted'] = datetime.strptime(date_enacted.group(1), '%d/%m/%Y').strftime(DATE_FORMAT)
    except (re.error, ValueError) as e:
        print('Error parsing dates', e.msg)
    # Click on Complete Act, which takes us to a page where we can select which elements of the code to include.
    # It opens in a new tab, so we switch to that.
    try:
        complete_act = driver.find_element_by_link_text('atto completo')
    except NoSuchElementException as e:
        print(e.msg)
        print(f'No Complete Act button, failed to download {code[1]}')
        return None
    complete_act.click()
    driver.switch_to.window(driver.window_handles[-1])
    # All elements of the code are already selected, so we click View to go to the full text.
    view = driver.find_element_by_xpath('//input[@value="Visualizza"]')
    view.click()
    text = driver.find_element_by_class_name('wrapper_pre').text
    name = f'{code[1].replace(" ", "_")}.txt'
    metadata['download_path'] = f'txt/{name}'
    with open(f'{DOWNLOAD_PATH}/{name}', 'w') as file:
        file.write(text)
    return metadata


def scrape_italy_laws():
    Path(DOWNLOAD_PATH).mkdir(parents=True, exist_ok=True)

    options = Options()
    options.headless = True
    options.add_argument(f'user-agent={FAKE_USER_AGENT}')
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

    codes = collect_code_urls(driver)
    print(f'Found {len(codes)} codes')
    metadata = list(filter(None, map(lambda x: download_code(driver, x), codes)))
    print('Writing metadata')
    with open(METADATA_PATH, 'w') as jsonfile:
        json.dump(metadata, jsonfile)

if __name__ == '__main__':
    scrape_italy_laws()
