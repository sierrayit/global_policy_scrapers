"""
Web scraper for downloading laws as HTML & PDF files from
http://www.leganet.cd/JO.htm
- the national law repository of the Democratic Republic of the Congo (DRC) -
using a Selenium Chrome bot.

Author: Magali de Bruyn
Updated: December 22, 2021
"""

## Install libraries through console
## ! pip install selenium
## ! pip install pdfkit
### ! brew install homebrew/cask/wkhtmltopdf

## Or create a virtual environment:
## pipenv install selenium
## pipenv install pdfkit
## pipenv install wkhtmltopdf / brew install wkhtmltopdf # ! this doesn't work for me
## pipenv run python scraper_tutorial.py

# This code uses a web driver
# Download from https://chromedriver.chromium.org/downloads
# based on Chrome version (version 96.0 for my local machine)

from datetime import date
import json
import os
from os import path
from urllib.parse import urlparse
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


# Define class constants
START_URL = 'http://www.leganet.cd/JO.htm' # 'http://www.ejustice.just.fgov.be/loi/loi.htm'
DOWNLOAD_PATH = './data/DRC/'
METADATA = []
METADATA_PATH = './data/DRC/metadata.json'
COUNTRY = 'DRC'

# Create fake user agent to bypass anti-robot walls
FAKE_USER_AGENT = 'Mozilla/5.0 (Windows NT 4.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36'

### GENERALIZABLE CODE
### Can be reused for other countries' websites

class ChromeBot:
    def __init__(self, headless=False):
        # Specify the driver chromebot
        options = Options()
        # Open chrome window or not?
        options.headless = headless
        # Add fake user agent to bypass anti-robot walls
        options.add_argument(f'user-agent={FAKE_USER_AGENT}')
        # Specify chromedriver location
        s = Service("./chromedriver")
        # Define driver with above specifications
        self.driver = webdriver.Chrome(service=s, options=options)
        print('\nChrome bot initialized!')

    def navigate_to(self, url):
        try:
            self.driver.get(url)
            print(f'\nLoaded page: {url}')
        except:
            print(f'\nCould not access this page: {url}')

    def find_xpath(self, xpath):
        try:
            return self.driver.find_elements(By.XPATH, xpath)
        except IndexError:
            print('FAILED: Chrome bot could not find specified xpath.')

    def find_xpath_solo(self, xpath):
        try:
            return self.driver.find_element(By.XPATH, xpath)
        except IndexError:
            print('FAILED: Chrome bot could not find specified xpath.')

    def get_html(self):
        return self.driver.page_source

    def get_url(self):
        return self.driver.current_url

    def switch_to_default(self):
        self.driver.switch_to.default_content()

    def switch_to_tab(self, tab_id):
        tab = self.driver.window_handles[tab_id]
        self.driver.switch_to.window(tab)

    def switch_to_frame(self, frame_xpath: str):
        frame = self.driver.find_element(By.XPATH, frame_xpath)
        self.driver.switch_to.frame(frame)

    def wait_sec(self, time_sec):
        self.driver.implicitly_wait(time_sec)

def create_destination_file(law_name: str, law_text: str = '', type: str = 'txt', language: str = 'french'):
    """
    Define a name and file path for any law based on title, content, and desired file type
    """
    # Shorten and format the title and sample text
    title = re.sub(' ', '-', re.sub('\W+',' ', law_name+law_text)).lower()[:250]
    ## Some files have the same title but are in fact different laws!
    ## i.e. the content is different. Hence, adding words from the law's text
    ## to differentiate titles & laws
    # Create the path by combining relevant variables
    file_path = DOWNLOAD_PATH + language + '/' + type + '/' + title + '.' + type
    destination_file = os.path.join(os.path.dirname(__file__), file_path)
    print("DOWNLOADING: ", destination_file)
    # Check that the file does not already exist
    if path.exists(destination_file):
        print(destination_file + " is already downloaded. Not re-downloading.")
        return
    return destination_file

def append_to_metadata(law_name: str, file_link: str, filename: str, language: str = 'french'):
    """Append a new entry to the METADATA list."""
    METADATA.append({'title': law_name,
                     'link': file_link,
                     'download_path': filename,
                     'download_date': date.today().strftime('%Y-%m-%d'),
                     'language': language,
                     'country': COUNTRY})
    print('Added item to METADATA.')

def write_metadata_json():
    """Write the metadata to a json file."""
    dirname = os.path.dirname(__file__)
    metadata_path = os.path.join(dirname, METADATA_PATH)
    with open(metadata_path, 'w') as file:
        json.dump(METADATA, file)
    print('\nWrote metadata to JSON.')


### COUNTRY-SPECIFIC CODE
### For DRC (Congo): from www.leganet.cd/JO.htm

def scrape_drc_laws(headless=True):
    """Scrape all DRC laws from http://www.leganet.cd/JO.htm"""

    # Define language
    language = 'french'
    # Initialize Selenium Chrome bot
    bot = ChromeBot(headless)
    # Navigate to start url
    bot.navigate_to(START_URL)
    bot.wait_sec(5)
    # Access laws listing page
    # Access XPath
    laws_list_link = bot.find_xpath_solo("//img[@alt='Législation']")
    # Stop if a problem occured
    if laws_list_link is None:
        return
    # Click on button to acess list of laws
    laws_list_link.click()
    bot.wait_sec(2)
    # Find all the law links
    all_links = bot.find_xpath("//*[contains(text(), 'Texte') or contains(text(), 'texte') or contains(text(), 'pdf')]")
    # Keep track of total laws and listing pages
    laws_ttl = len(all_links)
    print(f'Laws to download on the page: {len(all_links)}')
    print(f'{laws_ttl} laws discovered so far in total')

    # Iterate over all download links; click on it, scrape the law, come back to previous page
    for i in range(len(all_links)): # For testing purposes, use: range(0, 1) or range(len(all_links)-5, len(all_links))
        try:
            # Click on law, access page
            all_links[i].click()
            # Switch (bot) to tab containing the law
            bot.wait_sec(5)
            bot.switch_to_tab(1)
            # Get url of page
            file_source_url = bot.get_url()
            # Some of the links lead to PDFs, some to html files - not consistent
            # Treating them seperably
            if 'pdf' in file_source_url: # If it's a PDF link
                # Get PDF title from url path through parsing
                pdf_path = urlparse(file_source_url).path
                law_title = os.path.splitext(pdf_path)[0][1:]
                # Announce law
                print(f'\nFound law ({i+1}/{len(all_links)}): ', law_title)
                # Create destination file from law title name
                destination_file = create_destination_file(law_name=law_title, type='pdf', language=language)
                # Check if file was already downloaded
                if destination_file is not None:  # Unless file was already downloaded
                    # Get HTML response (pdf content)
                    response = requests.get(file_source_url, stream=True)
                    # Write response as binary file
                    with open(destination_file, 'wb') as f:
                        f.write(response.content)
                    # Add entry to metadata
                    append_to_metadata(law_title, file_source_url, destination_file)
            else: # If it's not a PDF, it's a HTML page (on this website)
                file_source_url = bot.get_url()
                # Get title
                ## Titles are not consistently formatted across html pages
                ## so trying different XPaths
                ## If none of these work, the link is probably broken (404 error)-
                ## a handful of them are, unfortunately
                continue_cond = True
                try:
                    law_title = bot.find_xpath_solo("/html/body/table[2]/tbody/tr/td[3]/p[1]").text[0:250]
                except:
                    try:
                        law_title = bot.find_xpath_solo("/html/body/table[2]/tbody/tr/td[3]/span[1]/p").text[0:250]
                    except:
                        try:
                            law_title = bot.find_xpath_solo("/html/body/table[2]/tbody/tr/td[3]/div[1]/dl[1]").text[0:250]
                        except:
                            try:
                                law_title = bot.find_xpath_solo("/html/body/table[2]/tbody/tr/td[3]/dl/dt[1]").text[0:250]
                            except:
                                try:
                                    law_title = bot.find_xpath_solo("/html/body/table[2]/tbody/tr/td[3]/font[1]/b/p").text[0:250]
                                except:
                                    print(f"\nThe link for this law is probably broken (404 error). You can check manually using the law's link: {file_source_url}")
                                    continue_cond = False
                if continue_cond:
                    # Announce law
                    print(f'\nFound law ({i+1}/{len(all_links)}): ', law_title)
                    # Get box with text
                    bot.find_xpath_solo("/html/body/table[2]/tbody/tr/td[3]") #//td[@valign='top']")
                    # Get html text
                    text_html = bot.get_html()
                    # Use Beautiful Soup to get Unicode string
                    soup = BeautifulSoup(text_html, features="html.parser")
                    text_soup = soup.get_text()
                    text_mid = round(len(text_soup)/2)
                    # Display what it's about
                    content_extract = text_soup[text_mid:text_mid+250]
                    # Create file
                    destination_file = create_destination_file(law_title, content_extract, 'txt', language)
                    # Check if file was already downloaded
                    if destination_file is not None:
                        # Write text file
                        with open(destination_file, 'w') as f:
                            f.write(text_soup)
                        # Add entry metadata for this law
                        append_to_metadata(law_title, file_source_url, destination_file, language)
            # Close active tab and move on
            bot.wait_sec(2)
            bot.driver.close()
            bot.switch_to_tab(0)
            bot.wait_sec(1)
        except:
            print("\nCould not access the link.")

    # Write all metadata to JSON
    write_metadata_json()
    print(f'\n{laws_ttl} laws discovered in total')
    print('\nCode finished running!\n')

if __name__ == '__main__':
    scrape_drc_laws(headless=True)
