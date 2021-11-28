"""
Scraper for Vietnam's laws found in http://vbpl.vn/TW/Pages/vbpqen.aspx. 

Step 1: Gather base links.
Collect a set of base urls, where each url corresponds to a type of document. Each document is associated with an index, i:
f"https://vbpl.vn/TW/Pages/vanbanTA.aspx?idLoaiVanBan={i}".

Step 2: Access each base link, which may contain multiple pages, and scrape metadata and law document(s) page by page.
- Metadata: [title, link, download_date, country, date_enacted, date_effective, document_type, status, description, download_path, language]
  Not all will exist, esp. for date_enacted and date_effective.
- Law document(s): Look for and download all valid file attachments first. If absent, scrape the text and save as txt.
  Download English content first, then if Vietnamese docs are present, download those too. Metadata for Vietnamese docs is in English, only the docs
  are in Vietnamese.

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
    """Gather link per type of document. Each max_index value corresponds to a document type. 24 seems to be the max."""

    print("gathering baselinks")
    
    # gather all links
    for i in range(1, max_index + 1, 1):
        url = f"https://vbpl.vn/TW/Pages/vanbanTA.aspx?idLoaiVanBan={i}"
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
        print("==========", doctype, base_url, "==========")
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
            if len(table) > 0:
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
        published_date = validated_date(pubdates[i])
        effective_date = validated_date(effdates[i])

        # enter document url, gather additional info and append to metadata - only for English
        language = "english"
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")

        if soup.find("div", class_ = "fulltext") is None: # if document page is empty, skip the law entierely
            continue

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


def validated_date(date_string):
    """Return a reformatted datetime object and None if original date_string doesn't follow the strptime format."""

    try:
        return datetime.strptime(date_string, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError as e:
        return None


def find_download_links(soup, title, language):
    """Examine all download links per law document and create respective filepaths."""

    vbfile = soup.find("div", "vbFile")
    fulltext = soup.find("div", "fulltext")

    # check if file attachment elements exist
    if vbfile is not None:
        attach = vbfile.select("ul li a")
        metadata_list = [] # collect metadata for link and download_path

        # some laws have multiple doc links, so we want to alter the saved doc's filename to prevent overwriting
        multiple = len(attach) > 1
        if multiple:
            title += "__"
            i = 1

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

            # some laws have multiple doc links, so we alter the saved doc's filename to prevent overwriting
            if multiple:
                title = title[:-1] + str(i)
                i += 1

            fname = create_filename(title, language, ext)
            with open(fname, "wb") as f:
                for chunk in doc.iter_content(1024 * 1024):
                    f.write(chunk)
            
            print("downloaded", ext, "for", title)
            metadata_list.append({"link": url, "download_path": fname, "language": language}) # alternative for "download_path": [fname.index("data"):]

        return metadata_list

    # if file attachment elements don't exist, scrape the text off the page and save as txt
    elif fulltext is not None:
        doc = fulltext.get_text()
        fname = create_filename(title, language, "txt")
        with open(fname, "w", encoding = "utf-8") as f:
            f.write(doc)

        print("downloaded txt for", title)
        return [{"download_path": fname, "language": language}] # alternative for "download_path": [fname.index("data"):]

    # if neither exists, don't save law document
    else:
        return None


def create_filename(title, language, ext):
    """Create string from a document title for use in its filename."""

    dir_path = os.path.join(DOWNLOAD_PATH, language, ext)
    pathlib.Path(dir_path).mkdir(parents = True, exist_ok = True)
    fname = re.sub(r"[\/\s]", "_", title) + "." + ext
    return os.path.join(dir_path, fname)


def append_metadata(mdict, metadata_list):
    """Add other key-value pairs to the metadata dictionary, mdict, and append mdict to METADATA."""

    if metadata_list is None:
        return
    
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
    gather_baselinks()         # run gather_baselinks(1) for quick sample of results
    loop_through_paging()        
    write_metadata_json()

if __name__ == '__main__':
    scrape_vietnam_laws()