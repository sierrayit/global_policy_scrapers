from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

import requests

def get_volume_acts(base_url, volume):
	acts= []
	response = http_get(urljoin(base_url, volume.href))
	t_elems = get_html_elements(response.text, "tbody")
	if len(t_elems) != 1:
		raise Exception(f'No or multiple act tables found for volume {volume.href}')
	for tr in t_elems[0].tr:
		a_elem = tr.td.a
		a = Act(a_elem.get('href'), a_elem.string)
		print(a)
		acts.append(a)
	return acts

def get_all_volumes(url):
	vols = []
	response = http_get(url)
	vol_elems = get_html_elements(response.text, "li", {"class": "volume"})
	if not vol_elems:
		raise Exception(f'No Act Volumes found on {url}')
	for v_e in vol_elems:
		v = Volume(v_e.a.string, v_e.a.get('href'))
		vols.append(v)
	return vols

def scrape_bangla_laws(config):
	vols = get_all_volumes(urljoin(config.base_url, config.all_laws_page))
	print(vols)

class Config(object):
	def __init__(self):
		self.base_url = "http://bdlaws.minlaw.gov.bd"
		self.all_laws_page = "laws-of-bangladesh.html"

class Act:
	def __init__(self, volume, name, href):
		self.name = name
		self.href = href

	def __str__(self):
		return f'name: {self.name} href: {self.href}'

class Volume:
	def __init__(self, name, href):
		if not name or not href:
			raise Exception("name or href (or both) are empty")
		self.name = name
		self.href = href

	def __str__(self):
		return f'name: {self.name} href: {self.href}'

# util methods
def http_get(url):
	response = requests.get(url)
	if response.status_code != 200:
		raise Exception(f'Request {url} failed with http error code: {response.status_code}')
	return response

def get_html_elements(html, element, attrs):
	soup = BeautifulSoup(html)
	return soup.find_all(element, attrs=attrs)

if __name__ == '__main__':
	scrape_bangla_laws(Config())
