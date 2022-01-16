"""
Web scraper for downloading laws as HMTL files from
http://www.ejustice.just.fgov.be/cgi/summary.pl
- the national law repository of Belgium -
using a Selenium Chrome bot.

Fun fact: this official website from the Belgian government seems to have been
created in 2002... or earlier! And it doesn't look like it's been revamped since then -
it shows both in its design and code!

Author: Magali de Bruyn
Updated: December 20, 2021
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
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


# Define class constants
START_URL = 'http://www.ejustice.just.fgov.be/cgi/welcome.pl' # 'http://www.ejustice.just.fgov.be/loi/loi.htm'
DOWNLOAD_PATH = './data/belgium/'
METADATA = []
METADATA_PATH = './data/belgium/metadata.json'
COUNTRY = 'Belgium'
LANGUAGES = {'french': 'Français', 'dutch': 'Nederlands', 'german': 'Deutsch'}


# Create fake user agent to bypass anti-robot walls
FAKE_USER_AGENT = 'Mozilla/5.0 (Windows NT 4.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36'

### GENERALIZABLE CODE
### Can be reused for other countries' websites

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
        s = Service("./chromedriver")
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

    def switch_to_default(self):
        self.driver.switch_to.default_content()

    def switch_to_frame(self, frame_xpath: str):
        frame = self.driver.find_element(By.XPATH, frame_xpath)
        self.driver.switch_to.frame(frame)

    def wait_sec(self, time_sec):
        self.driver.implicitly_wait(time_sec)

def create_destination_file(law_name: str = 'Untitled', law_text: str = '', type: str = 'txt', language: str = 'french'):
    """
    Define a name and file path for any law based on title, content, and desired file type
    """
    # Shorten and format the title and first words
    title = re.sub(' ', '-', re.sub('\W+',' ', law_name)).lower()[:200]
    ## Some files have the same title but are in fact different laws!
    ## i.e. the content is different. Hence, adding words from the law's text
    ## to differentiate titles & laws
    law_text = re.sub(' ', '-', re.sub('\W+',' ', law_text)).lower()[:50]
    # Create the path by combining relevant variables
    file_path = DOWNLOAD_PATH + language + '/' + type + '/' + title + law_text + '.' + type
    destination_file = os.path.join( os.path.dirname(__file__), file_path)
    # Check that the file does not already exist
    if path.exists(destination_file):
        print(destination_file + " is already downloaded. Not re-downloading.")
        return
    return destination_file

def append_to_metadata(law_name: str, file_link: str, filename: str, language: str):
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
    with open(metadata_path, 'w') as f:
        json.dump(METADATA, f)
    print('\nWrote metadata to JSON.')


### COUNTRY-SPECIFIC CODE
### For Belgium: from www.ejustice.just.fgov.be

def scrape_belgium_laws(headless=True):
    """Scrape all Belgian laws from www.ejustice.just.fgov.be"""

    # Initialize Selenium Chrome bot
    bot = ChromeBot(headless)

    # Each law page (and corresponding file) has the same source url
    # i.e. each law page is only accessible via navigation from the start url
    # not directly (on this website)
    file_source_url = 'www.ejustice.just.fgov.be/cgi/article.pl'

    for language in list(LANGUAGES):
        print(f'\nSearching for laws in {language}')
        # Navigate to start url
        bot.navigate_to(START_URL)
        # Access language button & corresponding laws listing page
        # Access XPath
        laws_list_link = bot.find_xpath_solo("//input[@type='Submit' and @value='{}']".format(LANGUAGES.get(language))) # dynamic XPath
        # Stop if a problem occured
        if laws_list_link is None:
            return
        # Click on button
        laws_list_link.click()
        # Keep track of total laws and listing pages
        laws_ttl = 0
        listings_num = 0
        # Initialize IDs (use proxy - their date) of listing pages
        this_page = '.'
        old_page = ''
        # Switch to main frame for later navigation
        bot.switch_to_default()

        # Iterate through all the listing pages for this language
        while this_page != old_page: # Next listing page is available
            # Access & collect link to each law on the page
            # Switch to frame
            listings_num += 1
            print(f'\nOn the listing page number {listings_num}')

            try:
                bot.switch_to_frame("//frame[@name='Body']")
                all_links = bot.find_xpath("//input[@type='submit' and @name='numac']")
                laws_ttl = laws_ttl + len(all_links)
                print(f'Laws to download on the page: {len(all_links)}')
                print(f'{laws_ttl} laws discovered so far in total')

                # Iterate over all download links; click on it, scrape the law, come back to previous page
                for i in range(len(all_links)): # For testing purposes, use: range(0, 1):
                    # Click on law, access page
                    all_links[i].click()
                    # Switch to frame containing heading/title
                    bot.switch_to_frame("//frame[@name='Body']")
                    # Get title
                    law_title = bot.find_xpath_solo("/html/body/h3/center/u").text
                    # Announce law
                    print(f'\nFound law ({i+1}/{len(all_links)}): ', law_title)
                    # Write text file
                    # Get html text
                    text_html = bot.get_html()
                    # Use Beautiful Soup to get Unicode string
                    soup = BeautifulSoup(text_html, features="html.parser")
                    text_soup = soup.get_text()
                    # Display what it's about
                    content_extract = text_soup[300:500]
                    print('It is about: ', content_extract)
                    # Create file
                    destination_file = create_destination_file(law_name=law_title, law_text=content_extract, type='txt', language=language)
                    if destination_file is not None:
                        with open(destination_file, 'w') as f:
                            f.write(text_soup)
                        # Add entry metadata for this law
                        append_to_metadata(law_title, file_source_url, destination_file, language)

                    # Exit frame and go back to listing
                    bot.switch_to_default()
                    bot.switch_to_frame("//frame[@name='Foot']")
                    # Click button to go back to listing
                    button_back = bot.find_xpath_solo("/html/body/table/tbody/tr/td[4]/form/input[5]")
                    button_back.click()
                    # Switch to listing frame
                    bot.switch_to_default()
                    bot.switch_to_frame("//frame[@name='Body']")
                    # Recollect all links
                    all_links = bot.find_xpath("//input[@type='submit' and @name='numac']")
            except:
               print("\nNo laws accessible on this listing page. Moving on to the next.\n")
            try:
                # Go to next listing page - click button
                bot.switch_to_default()
                bot.switch_to_frame("//frame[@name='Foot']")
                # Get date of this listing page (also found in the footer)
                old_page = this_page
                this_page = bot.find_xpath_solo("//input[@type='text' and @name='pub_date']").get_attribute("value")
                print('\nThis listing page was published on:', this_page)
                # Navigate to next page
                button_next = bot.find_xpath_solo("//input[@type='Submit' and @value='Sommaire précédent' or @value='Vorige Inhoud' or @value='Voriger Inhalt']")
                button_next.click()
            except:
               print("No next page could be accessed.")
               break
    # Write all metadata to JSON
    write_metadata_json()
    print(f'\n{laws_ttl} laws discovered in total')
    print('\nCode finished running!\n')

if __name__ == '__main__':
    scrape_belgium_laws(headless=True)
