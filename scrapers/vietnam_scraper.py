"""
Scraper for Vietnam's laws found in http://vbpl.vn/TW/Pages/vbpqen.aspx. 
"""

from datetime import date, datetime
import pathlib
import requests
import re
import json
import os
from bs4 import BeautifulSoup

HOME_DIR = os.path.dirname(os.path.dirname(__file__))
DOWNLOAD_PATH = os.path.join(HOME_DIR, "data", "vietnam")
METADATA_PATH = os.path.join(DOWNLOAD_PATH, "metadata.json")

COUNTRY = "Vietnam"
BASE_URL = "http://vbpl.vn"
BASE_URLS = []
METADATA = []


def gather_baselinks(max_index = 24):
    """Gather link per type of document. Each max_index value corresponds to a document type."""

    print("gathering baselinks")
    
    # gather all links
    for i in range(16, max_index + 1, 1):
        url = f"https://vbpl.vn/TW/Pages/vanbanTA.aspx?idLoaiVanBan={i}&dvid=13"
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")

        # grab document type and number of documents
        content = soup.select("a.selected span")[0]
        doctype = re.split("[:.]", content.get_text())[1].strip()
        numdoc = re.findall("\d+|$", content.get_text())[0]
        
        # only include link if num of docs > 0
        if int(numdoc) > 0:
            BASE_URLS.append((url, doctype))
    return 


def loop_through_paging():
    """Navigate page by page based on each url in BASE_URLS and scrape information per page."""

    for base_url, doctype in BASE_URLS:
        print(doctype)
        table_exists = True
        i = 1

        # if the table of documents exists, loop through page numbers with i
        while table_exists:

            # access the page of search results
            base = base_url + f"&Page={i}"
            page = requests.get(base)
            soup = BeautifulSoup(page.content, "html.parser")

            # check if the table of documents exists
            table = soup.select("ul.listLaw li")
            if len(table) > 0 and i < 3:
                print("scraping page", i)
                scrape_documents_info(soup, doctype)
                i += 1
            else:
                print("end")
                table_exists = False
    return


def scrape_documents_info(soup, doctype):
    """Scrape information of documents in one entire page, and enter each document to download its text.
    Assumption: all pages have tables of rows with the same html structure."""

    # gather all available info from the page
    titles = soup.select("p.title a")
    descs = soup.select("div.des p")
    publabels = soup.find_all("label", string = "Published:")
    pubdates = [d.find_parent("p", class_ = "green").get_text().split(":")[1] for d in publabels]
    efflabels = soup.find_all("label", string = "Effective:")
    effdates = [d.find_parent("p", class_ = "green").get_text().split(":")[1] for d in efflabels]

    # enter each document on the page
    for i in range(len(titles)):

        # extract info specific to document
        url = BASE_URL + titles[i]["href"]
        title = titles[i].get_text()
        description = descs[i].get_text()
        published_date = datetime.strptime(pubdates[i], "%d/%m/%Y").strftime("%Y-%m-%d")
        effective_date = datetime.strptime(effdates[i], "%d/%m/%Y").strftime("%Y-%m-%d")

        # enter document url, gather additional info and append to metadata - only for English
        language = "english"
        page = requests.get(url)#, verify = CERTFILE_PATH)
        soup = BeautifulSoup(page.content, "html.parser")
        statusspan = soup.find("span", string = "Effective: ")
        status = statusspan.find_parent("li").get_text().split(":")[1].strip()

        metadata_dict = {
        "title": title,
        "link": url,
        "download_date": date.today().strftime("%Y-%m-%d"),
        "country": COUNTRY,
        "date_enacted": published_date,
        "date_effective": effective_date,
        "document_type": doctype,
        "status": status,
        "description": description
        }

        # download document(s) text
        metadata = find_download_links(soup, title, language)
        append_metadata(metadata_dict, metadata)

        # extract Vietnamese version if available
        viet_button = soup.find("b", "history", string = "Vietnamese Documents")

        if viet_button:
            # parse html of vietnamese site
            viet_url = BASE_URL + viet_button.find_parent("a")["href"]
            page = requests.get(viet_url)
            soup = BeautifulSoup(page.content, "html.parser")

            # gather info for metadata
            language = "vietnamese"
            metadata_dict["link"] = viet_url
            metadata = find_download_links(soup, title, language)
            append_metadata(metadata_dict, metadata)

    return


def find_download_links(soup, title, language):
    """Examine all download links per law document and create respective filepaths."""

    # check if file attachment elements exist
    vbfile = soup.find("div", "vbFile")
    
    if vbfile is not None:
        attach = vbfile.select("ul li a")
        metadata_list = [] # collect metadata for link and download_path

        # loop through every available file attachment
        for a in attach:

            # ignore "Xem nhanh"/Quick View links as they're invalid
            if "iFrame" in a["href"]: 
                continue
            
            # all other links are javascript
            fpath = re.findall(r"([^']*)" , a["href"])[6]
            url = BASE_URL + fpath
            doc = requests.get(url)
            ext = re.split("\.", fpath)[-1]

            fname = create_filename(title, language, ext)
            with open(fname, "wb") as f:
                for chunk in doc.iter_content(1024 * 1024):
                    f.write(chunk)
            
            print("downloaded", ext, "for", title)
            metadata_list.append({"link": url, "download_path": fname, "language": language}) # alternative for "download_path": [fname.index("data"):]

        return metadata_list

    # if file attachment elements don't exist, scrape the text off the page and save as txt
    else:
        doc = soup.find("div", class_ = "fulltext").get_text()
        fname = create_filename(title, language, "txt")
        with open(fname, "w", encoding = "utf-8") as f:
            f.write(doc)

        print("downloaded txt for", title)
        return [{"download_path": fname, "language": language}] # alternative for "download_path": [fname.index("data"):]


def create_filename(title, language, ext):
    """Create string from a document title for use in its filename."""

    dir_path = os.path.join(DOWNLOAD_PATH, language, ext)
    pathlib.Path(dir_path).mkdir(parents = True, exist_ok = True)
    fname = re.sub(r"[\/\s]", "_", title) + "." + ext
    return os.path.join(dir_path, fname)


def append_metadata(mdict, metadata_list):
    """Add other key-value pairs to the metadata dictionary, mdict, and append mdict to METADATA."""
    
    for m in metadata_list:
        mdict["download_path"] = m["download_path"]
        mdict["language"] = m["language"]
        try:
            mdict["link"] = m["link"]
        except KeyError as e:
            continue

    METADATA.append(mdict)
    return


def write_metadata_json():
    """Write metadata into json file."""

    print("writing metadata")
    with open(METADATA_PATH, "w") as f:
        json.dump(METADATA, f)


def scrape_vietnam_laws():
    gather_baselinks()
    loop_through_paging()
    write_metadata_json()

if __name__ == '__main__':
    scrape_vietnam_laws()