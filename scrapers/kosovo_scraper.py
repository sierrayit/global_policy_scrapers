"""Download all laws from the Kosovo website."""
from datetime import date
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


BASE_URL = 'https://gzk.rks-gov.net'
START_URL = 'https://gzk.rks-gov.net/LawInForceList.aspx'
WEB_DRIVER_PATH = '/usr/local/bin/chromedriver'

LINKS = []
METADATA = []
METADATA_PATH = '../data/kosovo/metadata.csv'
DOWNLOAD_PATH = '../data/kosovo/txt'

def get_links_and_next(atags):
    """Populates the list of LINKS to follow."""
    for atag in atags:
        link = atag.get_attribute('href')
        if link is None:
            continue
        if 'https' in link:
            LINKS.append(link)
        class_attr = atag.get_attribute('class')
        tag_id = atag.get_attribute('id')
        if class_attr is not None and class_attr == 'Linkbutton' and 'Next' in tag_id:
            return atag
    return None

def get_law_text(driver, law_link):
    """Get the text of a law."""
    print('Getting text for link: ' + law_link)
    driver.get(law_link)

    # Click button for english
    driver.find_elements_by_xpath(
        '/html/body/form/div[3]/div[1]/div[1]/div[2]/div[2]/ul/li[2]/a')[0].click()

    main_law_page_button = driver.find_elements_by_xpath(
        '/html/body/form/div[3]/div[1]/div[2]/div[2]/div[2]/div/div[1]/div/div/div[1]/a')

    main_law_title = main_law_page_button[0].text
    is_abolished = driver.find_elements_by_xpath('//*[@id="MainContent_lblAct_Ne_Fuqi_Txt"]')
    if len(is_abolished) > 0 and 'ABOLISHED' in is_abolished[0].text:
        print('Law is abolished. Returning.')
        return

    # Open the page of the main law and grab the text
    main_law_page_button[0].click()
    law_text = driver.find_elements_by_xpath('//*[@id="MainContent_txtDocument"]')[0].text

    title = main_law_title.strip().replace(' ', '-').replace('/','-')[:250]
    filename = DOWNLOAD_PATH + title + '.txt'
    METADATA.append({'title': main_law_title,
                     'link': law_link,
                     'download_path': filename,
                     'download_date': date.today().strftime('%Y-%m-%d'),
                     'country': 'Kosovo'})
    with open(filename, "a") as file_handle:
        file_handle.write(law_text)
        file_handle.close()

def write_metadata_json():
    """Write the metadata file."""
    print('Writing metadata to json')
    with open(METADATA_PATH, 'w') as file:
        json.dump(METADATA, file)

def scrape_kosovo_laws():
    """Scrapes all laws from the Kosovo site."""
    options = Options()
    options.headless = True
    options.add_argument("--window-size=1920,1200")

    driver = webdriver.Chrome(options=options, executable_path=WEB_DRIVER_PATH)
    driver.get(START_URL)

    atags = driver.find_elements_by_tag_name('a')
    res = get_links_and_next(atags)
    while res is not None:
        res.click()
        atags = driver.find_elements_by_tag_name('a')
        res = get_links_and_next(atags)

    print('Finished getting links. Found ' + str(len(LINKS)))

    done = 1
    for link in LINKS:
        print('Processing link: ' + str(done) + '/' + str(len(LINKS)))
        get_law_text(driver, link)
        done += 1

    write_metadata_json()
    driver.quit()


if __name__ == '__main__':
    scrape_kosovo_laws()
