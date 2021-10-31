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
import time

START_URL = "https://www.fedlex.admin.ch"
DOWNLOAD_PATH = '../data/switzerland/pdf/'
METADATA = []
METADATA_PATH = '../data/switzerland/metadata.json'
COUNTRY = 'Switzerland'

### Fake user agent to bypass anti-robot walls
FAKE_USER_AGENT = 'Mozilla/5.0 (Windows NT 4.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36'

### REUSABLE CODE (common to all scrapers)

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

    def find_text(self, text):
        try:
            return self.driver.find_element_by_link_text(text)
        except IndexError:
            print('FAILED: Chrome bot could not find elements with that text: {text}.')
            
    def find_css(self, css_selector):
        try:
            return self.driver.find_elements_by_css_selector(css_selector)
        except IndexError:
            print('FAILED: Chrome bot could not find elements with that CSS: {css_selector}.')

    def switch_to_tab(self, tab_id):
        tab = self.driver.window_handles[tab_id]
        self.driver.switch_to.window(tab)
        
    def wait_sec(self, time_sec):
        time.sleep(time_sec)
        # Not sure why; this doesn't seem to work with the Swiss website.
        ### self.driver.implicitly_wait(time_sec)


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
        print("Already downloaded!")
        return
    return pdf_destination_file


def write_response(response, pdf_destination_file):
    with open(pdf_destination_file, 'wb') as file:
        for chunk in response.iter_content(1024 * 1024):
            file.write(chunk)
    print("Saved file as binary.")


def append_to_metadata(law_name: str, law_version_date: str, pdf_link: str, filename: str):
    """Appends an item to the METADATA list."""
    METADATA.append({'title': law_name,
                     'law validity': law_version_date,
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
    bot.wait_sec(3)
    
    # Click on Fr button; laws only exist in French, German or Italian
    fr_button = bot.find_xpath(
        '/html/body/app-root/div/app-header/header/div[1]/section/app-language/nav/ul/li[2]/a'
    )
    if fr_button is None:
        return  # Stop if a problem occured
    fr_button[0].click()
    bot.wait_sec(2)

    # Get all links under section "Textes choisis" (=Selected Texts)
    div_section_xpath = '/html/body/app-root/div/app-home/div/div/div/app-editable-links/section/div[4]/ul'
    all_text_a_tags = bot.find_xpath(f"{div_section_xpath}//li//a")
    all_text_links = list(map(lambda x: x.get_attribute('href'), all_text_a_tags))
    all_law_titles = list(map(lambda x: x.text, all_text_a_tags))
    print(f'Law texts found: {len(all_text_a_tags)}')

    # Loop over all law text links; download a PDF for each
    for k, (link, law_title) in enumerate(zip(all_text_links, all_law_titles)):
        print(f'\nAttempting to download: ({k + 1}/{len(all_text_links)}) | ', law_title)
        pdf_destination_file = create_pdf_destination_file(law_title)
        if pdf_destination_file is not None:  # Unless file was already downloaded      
            # Navigate to law page
            bot.navigate_to(link)
            bot.wait_sec(4)
            # Target most recent version WITH a PDF link
            table_versions = bot.find_xpath('//*[@id="versionContent"]/tbody//tr')  # All table rows
            found = False
            for row in range(1, len(table_versions) + 1):
                version_xpath = f'//*[@id="versionContent"]/tbody/tr[{row}]'
                version_tds = bot.find_xpath(f'{version_xpath}//td')
                td_links = bot.find_xpath(f'{version_xpath}//td//a')
                for td_link in td_links: # There can be links to HTML, PDF and/or DOC versions... or no links at all
                    if re.match('PDF', td_link.text):
                        td_link.click()  # Should display pdf viewer in <iframe>
                        bot.wait_sec(4)
                        pdf_reader_target = bot.find_css('.pdf-reader iframe')
                        pdf_source_url = pdf_reader_target[0].get_attribute('src')
                        # Download PDF file
                        response = collect_response(pdf_source_url)
                        bot.wait_sec(4)
                        write_response(response, pdf_destination_file)
                        # Scrape date
                        law_version_date = version_tds[1].text
                        append_to_metadata(law_title, law_version_date, pdf_source_url, pdf_destination_file)
                        bot.wait_sec(4)
                        found = True
                        break
                if found:
                    break
            if not found:
                print(f"Warning: Could not download this law: {law_title}")
    
    # Wrap-up
    write_metadata_json()
    print("Program ran successfully.")

if __name__ == '__main__':
    scrape_swiss_laws(headless=True)
