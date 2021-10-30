"""
Web scraper for downloading Swiss laws as PDF from www.fedex.admin.ch
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

START_URL = "https://www.fedlex.admin.ch"#'https://www.fedlex.admin.ch/fr/cc?news_period=last_day&news_pageNb=1&news_order=desc&news_itemsPerPage=50'
DOWNLOAD_PATH = '../data/switzerland/pdf/'
METADATA = []
METADATA_PATH = '../data/switzerland/metadata.json'
COUNTRY = 'Switzerland'

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
        import time
        time.sleep(time_sec)
        # self.driver.implicitly_wait(time_sec)


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


### COUNTRY-SPECIFIC CODE (Here, Switzerland; from www.fedex.admin.ch)

def scrape_swiss_laws(headless=True):
    """Scrapes all French laws from legifrance.gouv.fr."""
    
    # Initialize Selenium Chrome bot and navigate to start page.
    bot = ChromeBot(headless)
    bot.navigate_to(START_URL)
    bot.wait_sec(5)
    
    # Navigate to Fr button
    fr_button = bot.find_xpath(
        '/html/body/app-root/div/app-header/header/div[1]/section/app-language/nav/ul/li[2]/a'
    )
    if fr_button is None:
        return  # Stop if a problem occured
    fr_button[0].click()
    bot.wait_sec(2)

    # Open "Recueil systematique" (=Systematic repository) pannel
    repo_button = bot.find_xpath(
        '//*[@id="main-navigation"]/ul/li[5]/a'
    )
    if repo_button is None:
        return  # Stop if a problem occured
    repo_button[0].click()
    bot.wait_sec(2)

    # Click on "Accueil RS" link
    repo_link = bot.find_xpath(
        '//*[@id="main-navigation"]/ul/li[5]/ul/li/div/app-panel-menu/div/div/div/div/div/div[1]/div/h3/a'

    )
    if repo_link is None:
        return  # Stop if a problem occured
    repo_link[0].click()
    bot.wait_sec(2)

    print("Program finished running.")

    # # Temp
    # bot.navigate_to("https://www.fedlex.admin.ch/fr/cc?news_period=last_day&news_pageNb=1&news_order=desc&news_itemsPerPage=10")
    # bot.wait_sec(3)

    # # Find references to download links for all laws on the page
    # all_download_links = bot.find_class('picto-download')
    # print(f'Number of laws to download on the page: {len(all_download_links)}\n')
    
    # # Iterate over all download links; click on it, scrape the law, come back to previous page
    # for k, link in enumerate(all_download_links):
    #     link.click()
    #     bot.wait_sec(5)
    #     bot.switch_to_tab(1)
        
    #     # Scrape law title
    #     law_title = bot.find_class('pdf-title')[0].text
    #     print(f'\nFound law ({k+1}/{len(all_download_links)}): ', law_title)
        
    #     # Create a file name from law title
    #     filename = generate_pdf_file_name(law_title)
        
    #     # Instead of interacting with the PDF viewer, get a link to the PDF from the hidden "object" element of the DOM
    #     pdf_object = bot.find_tag('object')[0]
    #     pdf_link = pdf_object.get_attribute('data')
    #     print(pdf_link)

    #     # # Save PDF file
    #     # save_pdf_file_as_binary(pdf_link, filename)
    #     # bot.wait_sec(5)

    #     # # Add entry to metadata
    #     # append_to_metadata(law_title, pdf_link, filename)
    #     # bot.wait_sec(1)

    #     bot.driver.close()  # Close the active tab
    #     bot.switch_to_tab(0)
    #     bot.wait_sec(1)
        
    #     break

    # # write_metadata_json()

    # print('Code ran to here.')

if __name__ == '__main__':
    scrape_swiss_laws(headless=True)
