import requests
import pdfkit
from bs4 import BeautifulSoup
import os
import logging
from datetime import date
import json

class Config(object):
    def __init__(self, download_path, metadata_path=None, test_run=False, log_level=logging.INFO):
        self.download_path = download_path
        self.test_run = test_run
        self.log_level = log_level
        self.metadata_path = metadata_path or f'{download_path}/../metadata.json'

    def __str__(self):
        return f'Config: test_run: {self.test_run} log_level: {self.log_level}, download_path: {self.download_path}, metadata_path: {self.metadata_path}'

def init_scrapper(config):
    os.makedirs(config.download_path, exist_ok=True)
    logging.basicConfig(level=config.log_level)

def pdfkit_options():
	return {
        'no-images': None,
        'disable-javascript': None,
        'disable-local-file-access': None,
    }

def htmlurl_to_pdf(url, pdf_path, verbose=False):
    return pdfkit.from_url(url, pdf_path, options=pdfkit_options(), verbose=verbose)

# underlying api returns true on success
def htmlstring_to_pdf(string, pdf_path, verbose=False):
    return pdfkit.from_string(string, pdf_path, options=pdfkit_options(), verbose=verbose)

def http_get(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f'Request {url} failed with http error code: {response.status_code}')
    return response

def get_html_elements(html, element, attrs={}):
    soup = BeautifulSoup(html, features="lxml")
    return soup.find_all(element,  attrs=attrs)

class Metadata:
    def __init__(self):
        self.metadata = []

    def append_to_metadata(self, law_name: str, file_link: str, filename: str, language: str, country: str):
        """Append a new entry to the METADATA list."""
        self.metadata.append({'title': law_name,
                         'link': file_link,
                         'download_path': filename,
                         'download_date': date.today().strftime('%Y-%m-%d'),
                         'language': language,
                         'country': country})

    def write_json(self, path):
        """Write the metadata to a json file."""
        with open(path, 'w') as file:
            json.dump(self.metadata, file)
