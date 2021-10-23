"""
Web scraper for downloading French laws ("Codes") as PDF from www.legifrance.gouv.fr 
using a Selenium Chrome bot.
"""
from datetime import date
import json
from os import path
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os

START_URL = 'https://www.legifrance.gouv.fr/'
DOWNLOAD_PATH = '../data/france/pdf/'
METADATA = []
METADATA_PATH = '../data/france/metadata.json'
COUNTRY = 'France'

### Fake user agent to bypass anti-robot walls
FAKE_USER_AGENT = 'Mozilla/5.0 (Windows NT 4.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36'

### REUSABLE CODE

class ChromeBot:
    def __init__(self, headless=False):
        options = Options()
        options.headless = headless
        options.add_argument(f'user-agent={FAKE_USER_AGENT}')

        # Add custom profile to disactivate PDF viewer
        profile = {
            "plugins.plugins_list": [{"enabled": False,
                                         "name": "Chrome PDF Viewer"}],
        }
        options.add_experimental_option("prefs", profile)

        self.driver = webdriver.Chrome(options=options)
        print('Chrome bot initialized!')
    
    def navigate_to(self, url):
        try:
            self.driver.get(url)
            print(f'Loaded page: {url}')
        except:
            print(f'Could not access this page: {url}')
    
    def find_xpath(self, xpath):
        try:
            return self.driver.find_elements_by_xpath(xpath)
        except IndexError:
            print('FAILED: Chrome bot could not find specified xpath.')
    
    def find_class(self, class_name):
        try:
            return self.driver.find_elements_by_class_name(class_name)
        except IndexError:
            print('FAILED: Chrome bot could not find elements of that class: {class_name}.')
    
    def find_id(self, id_name):
        try:
            return self.driver.find_elements_by_id(id_name)
        except IndexError:
            print('FAILED: Chrome bot could not find elements with that id: {id_name}.')
    
    def find_tag(self, tag_name):
        try:
            return self.driver.find_elements_by_tag_name(tag_name)
        except IndexError:
            print('FAILED: Chrome bot could not find elements with that tag name: {tag_name}.')
            
    def switch_to_tab(self, tab_id):
        tab = self.driver.window_handles[tab_id]
        self.driver.switch_to.window(tab)
        
    def wait_sec(self, time_sec):
        self.driver.implicitly_wait(time_sec)


def collect_response(url: str, trials=10, timeout=10):
    for _ in range(trials):
        try:
            response = requests.get(url, timeout=timeout, stream=True)
        except:
            print('Page failed to load. Trying again...')
            continue
        break
    return response


def filename_maker(law_name: str) -> str:
    """Returns a lowercase, 250 characters max version of law_name 
    to be used as filename (also, removes special characters)."""
    return re.sub(' ', '-', re.sub('\W+',' ', law_name)).lower()[:250]


def generate_pdf_file_name(title: str) -> str:
    title = filename_maker(title)
    return DOWNLOAD_PATH + title + '.pdf'


def create_pdf_destination_file(title):
    pdf_destination_file = os.path.join(
        os.path.dirname(__file__), 
        generate_pdf_file_name(title)
    )
    if path.exists(pdf_destination_file):
        print(pdf_destination_file + " already downloaded")
        return
    return pdf_destination_file


def write_response(response, pdf_destination_file):
    with open(pdf_destination_file, 'wb') as file:
        for chunk in response.iter_content(1024 * 1024):
            file.write(chunk)
    print("Saved file as binary.")


def append_to_metadata(law_name: str, pdf_link: str, filename: str):
    """Appends an item to the METADATA list."""
    METADATA.append({'title': law_name,
                     'link': pdf_link,
                     'download_path': filename,
                     'download_date': date.today().strftime('%Y-%m-%d'),
                     'country': COUNTRY,})
    print('Added item to METADATA.')


def write_metadata_json():
    """Writes the metadata to a json file."""
    dirname = os.path.dirname(__file__)
    metadata_path = os.path.join(dirname, METADATA_PATH)
    with open(metadata_path, 'w') as file:
        json.dump(METADATA, file)
    print('\nWrote metadata to JSON.')


### COUNTRY-SPECIFIC CODE (Here, France; from legifrance.gouv.fr)

def scrape_france_laws(headless=True):
    """Scrapes all French laws from legifrance.gouv.fr."""
    
    # Initialize Selenium Chrome bot and navigate to start url.
    bot = ChromeBot(headless)
    bot.navigate_to(START_URL)
    bot.wait_sec(5)
    
    # Navigate to "Codes" (=Laws) page. /!\ Sometimes it hits an anti-robot wall..
    laws_list_link = bot.find_xpath(
        '//*[@id="main"]/div/div[2]/div/div/div[1]/div/ul/li[1]/p/span/a'
    )
    if laws_list_link is None:
        return  # Stop if a problem occured
    laws_list_link[0].click()
    bot.wait_sec(2)
    
    # Find references to download links for all laws on the page
    all_download_links = bot.find_class('picto-download')
    print(f'Laws to download on the page: {len(all_download_links)}\n')
    
    # Iterate over all download links; click on it, scrape the law, come back to previous page
    for k, link in enumerate(all_download_links):
        link.click()
        bot.wait_sec(2)
        bot.switch_to_tab(1)
        
        # Scrape law title
        law_title = bot.find_class('pdf-title')[0].text
        print(f'\nFound law ({k+1}/{len(all_download_links)}): ', law_title)
        
        # Create destination file from law title name
        pdf_destination_file = create_pdf_destination_file(law_title)

        if pdf_destination_file is not None:  # Unless file was already downloaded      
            # Get a link to the PDF from the hidden "object" element of the DOM
            pdf_source_url = bot.find_tag('object')[0].get_attribute('data')

            # Get HTML response (pdf content)
            response = collect_response(pdf_source_url)

            # Write response as binary file
            write_response(response, pdf_destination_file)
            bot.wait_sec(2)

            # Add entry to metadata
            append_to_metadata(law_title, pdf_source_url, pdf_destination_file)
        
        bot.wait_sec(2)

        # Close active tab and move on
        bot.driver.close()
        bot.switch_to_tab(0)
        bot.wait_sec(1)
    
    # Write all metadata to JSON
    write_metadata_json()

    print('\nCode finished running!')

if __name__ == '__main__':
    scrape_france_laws(headless=True)
