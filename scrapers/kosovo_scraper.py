import re
import csv
from bs4 import BeautifulSoup
from urllib.request import urlopen
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


base_url = 'https://gzk.rks-gov.net'
law_list = 'https://gzk.rks-gov.net/LawInForceList.aspx'
WEB_DRIVER_PATH = '/usr/local/bin/chromedriver'

links = []
metadata = []
metadata_path = 'scraper_metadata.csv'

def GetLinksAndNext(atags):
    for atag in atags:
        link = atag.get_attribute('href')
        if link == None:
            continue
        if 'https' in link:
            links.append(link)
        class_attr = atag.get_attribute('class')
        id = atag.get_attribute('id')
        if class_attr != None and class_attr == 'Linkbutton' and 'Next' in id:
            return atag
    return None

def GetLawText(driver, law_link):
    print('Getting text for link: ' + law_link)
    driver.get(law_link)

    # Click button for english
    driver.find_elements_by_xpath('/html/body/form/div[3]/div[1]/div[1]/div[2]/div[2]/ul/li[2]/a')[0].click()

    # Collect metadata
    type_of_act = driver.find_elements_by_xpath('/html/body/form/div[3]/div[1]/div[2]/div[2]/div[2]/div/div[2]/div[1]/table/tbody/tr[1]/td[3]/span')[0].text
    act_number = driver.find_elements_by_xpath('/html/body/form/div[3]/div[1]/div[2]/div[2]/div[2]/div/div[2]/div[1]/table/tbody/tr[2]/td[3]/span')[0].text
    main_law_page_button = driver.find_elements_by_xpath('/html/body/form/div[3]/div[1]/div[2]/div[2]/div[2]/div/div[1]/div/div/div[1]/a')

    main_law_title = main_law_page_button[0].text
    is_abolished = driver.find_elements_by_xpath('//*[@id="MainContent_lblAct_Ne_Fuqi_Txt"]')
    if len(is_abolished) > 0 and 'ABOLISHED' in is_abolished[0].text:
        print('Law is abolished. Returning.')
        return

    # Open the page of the main law and grab the text
    main_law_page_button[0].click()
    law_text = driver.find_elements_by_xpath('//*[@id="MainContent_txtDocument"]')[0].text

    title = main_law_title.strip().replace(' ', '-').replace('/','-')[:250]
    filename = 'txt/' + title + '.txt'
    metadata.append({'title': main_law_title, 'link': law_link, 'download_path': filename})
    file = open(filename,"a")
    file.write(law_text)
    file.close()

def WriteMetadataCsv():
    print('Writing scraper metadata csv')
    with open(metadata_path, 'w', newline='') as csvfile:
        fields = ['title', 'country', 'link', 'date_scraped', 'download_path']
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()
        for d in metadata:
            writer.writerow({'title': d['title'],
                            'country': 'Kosovo',
                            'link': d['link'],
                            'date_scraped': '2021/03/30',
                            'download_path': d['download_path']})

def main():
    options = Options()
    options.headless = True
    options.add_argument("--window-size=1920,1200")

    driver = webdriver.Chrome(options=options, executable_path=WEB_DRIVER_PATH)
    driver.get(law_list)

    atags = driver.find_elements_by_tag_name('a')
    res = GetLinksAndNext(atags)
    while (res != None):
        res.click()
        atags = driver.find_elements_by_tag_name('a')
        res = GetLinksAndNext(atags)

    print('Finished getting links. Found ' + str(len(links)))

    done = 1
    for link in links:
        print('Processing link: ' + str(done) + '/' + str(len(links)))
        GetLawText(driver, link)
        done += 1

    WriteMetadataCsv()
    driver.quit()


if __name__ == '__main__':
  main()
