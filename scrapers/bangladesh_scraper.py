from urllib.parse import urlparse, urljoin

from scrapper_util import Config
from scrapper_util import Metadata
import scrapper_util
import logging
import os

def get_volume_acts(base_url, volume):
    acts= []
    response = scrapper_util.http_get(urljoin(base_url, volume.href))
    t_body = scrapper_util.get_html_elements(response.text, "tbody")
    if len(t_body) != 1:
        raise Exception(f'No or multiple act tables found for volume {volume.href}')
    for tr in t_body[0].find_all('tr'):
        a_elem = tr.find_all('td')[1].a
        a = Act(volume, a_elem.string, a_elem.get('href'))
        acts.append(a)
    return acts

def get_all_volumes(url):
    vols = []
    response = scrapper_util.http_get(url)
    vol_elems = scrapper_util.get_html_elements(response.text, "li", {"class": "volume"})
    if not vol_elems:
        raise Exception(f'No volumes found for {url}')
    for v_e in vol_elems:
        v = Volume(v_e.a.string, v_e.a.get('href'))
        vols.append(v)
    return vols

def download_act_pdf(config, act, destination_file, fetch_from_pdfkit=True):
    abs_url = act.print_href(config.base_url)
    logging.info(f'downloading act {act.name} from {abs_url}')
    if fetch_from_pdfkit:
        scrapper_util.htmlurl_to_pdf(abs_url, destination_file, False)
    else:
        # download the html in the scrapper instead of using pdkkit to better handle http errors
        # however this method fails to download css, so use this method if above methd doens't work for some reason
        response = scrapper_util.http_get(abs_url)
        try:
            scrapper_util.htmlstring_to_pdf(response.text, destination_file, False)
        except OSError as e:
            if "Exit with code 1 due to network error: ProtocolUnknownError" in f'{e=}':
                logging.debug("")
            else:
                raise e

def scrape_bangla_laws(config):
    m = Metadata()
    all_vols = get_all_volumes(urljoin(config.base_url, config.all_laws_page))
    vols = all_vols
    if config.test_run:
        vols = [all_vols[0]]

    for v in vols:
        all_acts = get_volume_acts(config.base_url, v)
        acts = all_acts
        if config.test_run:
            acts = [all_acts[0]]

        for a in acts:
            destination_file = os.path.join(config.download_path, f'{a.name}.pdf')
            if os.path.exists(destination_file):
                logging.info(destination_file + " is already downloaded.")
                continue
            try:
                download_act_pdf(config, a, destination_file)
                m.append_to_metadata(a.name, a.print_href(config.base_url), destination_file, 'bangla', 'bangladesh')
            except Exception:
                # https://stackoverflow.com/questions/5191830/how-do-i-log-a-python-error-with-debug-information
                logging.exception(f'unknown error occured while downloading act {a.href} for volume {v.href}. Skipping this act...')

    m.write_json(config.metadata_path)

class Act:
    def __init__(self, volume, name, href):
        self.name = name.strip()
        self.href = href

    def __str__(self):
        return f'name: {self.name} href: {self.href}'

    def print_href(self, base_url):
        return urljoin(base_url, self.href.replace('act', 'act-print'))

class Volume:
    def __init__(self, name, href):
        if not name or not href:
            raise Exception("name or href (or both) are empty")
        self.name = name
        self.href = href

    def __str__(self):
        return f'name: {self.name} href: {self.href}'

class BanglaConfig(Config):
    def __init__(self, download_path, test_run=False):
        self.base_url = "http://bdlaws.minlaw.gov.bd"
        self.all_laws_page = "laws-of-bangladesh.html"
        super().__init__(download_path, test_run=test_run)

# util methods
if __name__ == '__main__':
    download_path = os.path.join(os.path.dirname(__file__), '../../data/bangladesh/eng-bangla')
    c = BanglaConfig(download_path, test_run=False)
    scrapper_util.init_scrapper(c)
    scrape_bangla_laws(c)
