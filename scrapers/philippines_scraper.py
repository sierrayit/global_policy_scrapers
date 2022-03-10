"""
Scraper for the Philippines' laws found in https://www.officialgazette.gov.ph/masterlist-generator.

Process:
1. Gather a list of urls - each url accounts for the combination of a law category and a president. Only keep the url if the num of documents > 0.
2. Loop through the rows of the table of law documents (pdf and txt, if both exist) available in the masterlist generator, going down each combination, going through each page. Items per page = 100 and Order = Descending.
3. Write metadata after each combi of laws have been scraped. Metadata: [‘title’, ‘link’, ‘download_path’, ‘download_date’, ‘language’, ‘country’, ‘date_enacted’, ‘category’, ‘president’]

If you want to do a quick test, comment out the dictionaries 'categories' and 'presidents', and replace them with:

categories = {
    "Performance-Based Bonus": "performance-based-bonus"
}

presidents = {
    "Rodrigo Roa Duterte": "rodrigo-roa-duterte",
    "Benigno S. Aquino III": "benigno-s-aquino-iii"
}

Notes:
1. The txt file of a law is not necessarily equivalent to its pdf. From the website, some txts include only the law name and resources (i.e. link to the pdf). Pdfs contain the full document, unless only the txt version exists.
2. metadata.json file gets rewritten with each new run of this py script.

"""

from datetime import date, datetime
import pathlib
import requests
import re
import json
import os
from bs4 import BeautifulSoup

HOME_DIR = os.path.dirname(os.path.dirname(__file__))
DOWNLOAD_PATH = os.path.join(HOME_DIR, "data", "philippines")
METADATA_PATH = os.path.join(DOWNLOAD_PATH, "metadata.json")

COUNTRY = "Philippines"
BASE_URL = "https://www.officialgazette.gov.ph/masterlist-generator/page/"
URLS = []
METADATA = []

categories = {
    "Executive Issuances": "executive-issuances", 
    "Proclamations": "proclamations",
    "Executive Orders": "executive-orders", 
    "Memorandum Orders": "memorandum-orders",
    "Memorandum Circulars": "memorandum-circulars", 
    "Republic Acts": "republic-acts", 
    "Implementing Rules and Regulations of Republic Acts": "implementing-rules-and-regulations", 
    "Implementing Rules and Regulations of Executive Orders": "implementing-rules-and-regulations-executive-orders", 
    "Presidential Decrees": "presidential-decrees-executive-issuances", 
    "Letters of Instruction": "letters-of-instruction", 
    "Letters of Implementation": "letters-of-implementation", 
    "Administrative Orders": "administrative-orders", 
    "Speeches": "speeches", 
    "Special Orders": "special-orders", 
    "General Orders": "general-orders", 
    "Other Issuances": "other-issuances", 
    "Performance-Based Bonus": "performance-based-bonus", 
    "Inter-Agency Task Force for the Management of Emerging Infectious Disease Resolutions": "inter-agency-task-force-for-the-management-of-emerging-infectious-diseases-resolutions"
}

presidents = {
    "Manuel L. Quezon": "manuel-l-quezon", 
    "Sergio Osmeña": "sergio-osmena",
    "Manuel Roxas": "manuel-roxas", 
    "Elpidio Quirino": "elpidio-quirino", 
    "Ramon Magsaysay": "ramon-magsaysay", 
    "Carlos P. Garcia": "carlos-p-garcia", 
    "Diosdado Macapagal": "diosdado-macapagal", 
    "Ferdinand E. Marcos": "ferdinand-e-marcos", 
    "Corazon C. Aquino": "corazon-c-aquino", 
    "Fidel V. Ramos": "fidel-v-ramos", 
    "Joseph Ejercito Estrada": "joseph-ejercito-estrada", 
    "Gloria Macapagal Arroyo": "gloria-macapagal-arroyo", 
    "Benigno S. Aquino III": "benigno-s-aquino-iii", 
    "Rodrigo Roa Duterte": "rodrigo-roa-duterte"
}

def gather_links():
    """Gather link per category & president if the combination has documents to scrape"""

    print("gathering urls")

    for i in categories.items():
        for j in presidents.items():
            ext = f"/?category={i[1]}&president={j[1]}&per_page=100&on_order=DESC"
            url = "".join([BASE_URL, "1", ext])

            page = requests.get(url)
            soup = BeautifulSoup(page.content, "html.parser")
            content = soup.find("div", class_="alert-box info radius").get_text()
            ndocs = int(content.strip().split()[2]) # get number of documents in this combi

            if ndocs > 0:
                try:
                    npages = int(soup.find_all("a", class_="page-numbers")[-2].get_text()) # get number of pages to loop through in this combi
                except:
                    npages = 1
                URLS.append((ext, npages, i[0], j[0]))
    return

def scrape():
    """Loop through pages, scrape info from tables and write metadata to json file"""

    with open(METADATA_PATH, "w", encoding="utf-8") as f: # create empty json metadata file
        json.dump(METADATA, f)

    for t in URLS:
        ext, npages, cat, pres = t[0], t[1], t[2], t[3]

        for p in range(npages):

            print("\n============ Scraping", cat, "- President", pres, "- Page", "".join([str(p + 1), "/", str(npages)]), "============")

            url = "".join([BASE_URL, str(p + 1), ext])
            page = requests.get(url)
            soup = BeautifulSoup(page.content, "html.parser")
            table = soup.find_all("td")

            for i in range(0, len(table), 5):

                title, link_to_txt, date_enacted = table[i].get_text(), table[i+1].get_text(), table[i+3].get_text()

                # download in txt format first
                download_path = get_law_txt(title, link_to_txt)
                metadata_dict = {
                    "title": title,
                    "link": link_to_txt,
                    "download_path": download_path,
                    "download_date": date.today().strftime("%Y-%m-%d"),
                    "language": "english",
                    "country": COUNTRY,
                    "date_enacted": date_enacted,
                    "category": cat,
                    "president": pres
                }
                METADATA.append(metadata_dict)

                # check if pdf link works, and if so, download in pdf too
                link_to_pdf = table[i+4].find("a")["href"]

                if link_to_pdf != "":
                    download_path = get_law_pdf(title, link_to_pdf)

                    if download_path is not None:
                        metadata_dict = {
                            "title": title,
                            "link": link_to_pdf,
                            "download_path": download_path,
                            "download_date": date.today().strftime("%Y-%m-%d"),
                            "language": "english",
                            "country": COUNTRY,
                            "date_enacted": date_enacted,
                            "category": cat,
                            "president": pres
                        }
                        METADATA.append(metadata_dict)

        with open(METADATA_PATH, "w", encoding="utf-8") as f: # replace metadata json file with updated content per combi
            json.dump(METADATA, f)
            print("metadata written for", cat, "-", pres)

    return

def get_law_pdf(title, url):
    """Download law text in pdf format if it exists (status code: 200) and return the download path"""

    r = requests.get(url)

    if r.status_code == 200:
        fname = create_filename(title, "english", "pdf")
        with open(fname, "wb") as f:
            f.write(r.content)
        print("downloaded pdf for", title)
        return fname

    return None

def get_law_txt(title, url):
    """Download law text in .txt format and return the download path"""

    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    text = soup.find("article").get_text()

    fname = create_filename(title, "english", "txt")
    with open(fname, "w", encoding = "utf-8") as f:
        f.write(text)
    print("downloaded txt for", title)
    return fname

def create_filename(title, language, ext):
    """Create string from a document title for use in its filename."""

    dir_path = os.path.join(DOWNLOAD_PATH, language, ext)
    pathlib.Path(dir_path).mkdir(parents = True, exist_ok = True)
    fname = re.sub(r"[\/\s]", "_", title) + "." + ext
    return os.path.join(dir_path, fname)

def scrape_philippines_laws():
    gather_links()
    scrape()

if __name__ == '__main__':
    scrape_philippines_laws()