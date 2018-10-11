from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import scraperwiki
import sqlite3
import os
from   bs4 import BeautifulSoup
import sys
import time
import re
from datetime import datetime, timedelta
from re import sub
from decimal import Decimal
from dateutil.parser import parse
import math

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")

chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("start-maximized")
chrome_options.add_argument("disable-infobars")
chrome_options.add_argument("--disable-extensions")

driver = webdriver.Chrome(chrome_options=chrome_options,executable_path='/usr/local/bin/chromedriver')

def parseAskingPrice(aPrice):
	try:
		value = round(Decimal(sub(r'[^\d.]', '', aPrice)))
	except:
		value = 0
	return value
	
def saveToStore(data):
	scraperwiki.sqlite.execute("CREATE TABLE IF NOT EXISTS 'zpdata' ( 'propId' TEXT, link TEXT, title TEXT, address TEXT, price BIGINT, 'displayPrice' TEXT, image1 TEXT, 'pubDate' DATETIME, 'addedOrReduced' DATE, reduced BOOLEAN, location TEXT, CHECK (reduced IN (0, 1)), PRIMARY KEY('propId'))")
	scraperwiki.sqlite.execute("CREATE UNIQUE INDEX IF NOT EXISTS 'zpdata_propId_unique' ON 'zpdata' ('propId')")
	scraperwiki.sqlite.execute("INSERT OR IGNORE INTO 'zpdata' VALUES (?,?,?,?,?,?,?,?,?,?,?)", (data['propId'], data['link'], data['title'], data['address'], data['price'], data['displayPrice'], data['image1'], data['pubDate'], data['addedOrReduced'], data['reduced'], data['location']))
	
excludeAgents = ['andrew granger']

filtered_dict = {k:v for (k,v) in os.environ.items() if 'MORPH_URL' in k}

sleepTime = 5
domain = ""
if os.environ.get("MORPH_SLEEP") is not None:
	sleepTime = int(os.environ["MORPH_SLEEP"])

if os.environ.get("MORPH_DOMAIN") is not None:
	domain = os.environ["MORPH_DOMAIN"]

for k, v in filtered_dict.items(): 
	checkURL = v
	if os.environ.get('MORPH_DEBUG') == "1":
		print(checkURL)
		
	if os.environ.get('MORPH_MAXDAYS') == "0":
		checkURL = checkURL.replace("&maxDaysSinceAdded=1","")

	driver.get(checkURL)
	try:
		numOfResults = driver.find_element_by_css_selector('.listing-results-utils-count').text.replace(" ", "").split("of")
		numOfResults = int(numOfResults[1])
		numOfPages = math.ceil(float(numOfResults)/25)
	except ValueError:
		numOfPages = 0	

	print("NumberOfPages:"+str(numOfPages))

	page = 0
	while page < numOfPages:
		numResults=0
		numPreFeat=0
		numNormFeat=0
		numFeat=0
		
		html = driver.page_source
		soup = BeautifulSoup(html, 'html.parser')
		
		searchResults = soup.find("ul", {"class" : "listing-results clearfix js-gtm-list"})
		matches = 0
		if searchResults is not None:		
			adverts = searchResults.findAll("li", {"id" : lambda L: L and L.startswith('listing_')})
			numResults = len(adverts)
			
			for advert in adverts:
				reduced=False
				if advert.find("div", {"class" : "listing-results-wrapper"}) is not None:
					advertMatch = {}
					agent = advert.find("p", {"class" : "top-half listing-results-marketed"}).find("span").text
					
					if any(x in agent.lower() for x in excludeAgents):
						continue;

					location = k.replace("MORPH_URL_","").replace("_"," ").title()
					propLink=domain+advert.find("a", {"class" : "listing-results-price text-price"}).get('href')
					propId=re.search('\d+',propLink.split("?")[0])
					if propId:
						propId=propId.group(0)
					title = advert.find("h2", {"class" : "listing-results-attr"}).text
					address = advert.find("a", {"class" : "listing-results-address"}).text
					price = parseAskingPrice(advert.find("a", {"class" : "listing-results-price text-price"}).text.strip())
					displayPrice = advert.find("a", {"class" : "listing-results-price text-price"})
					unwanted = displayPrice.find('span')
					if unwanted is not None:
						unwanted = displayPrice.find('span').extract()
						displayPrice = displayPrice.text.strip()+" "+unwanted.text.strip()
					else:
						displayPrice = displayPrice.text.strip()
					image1 = advert.find("a", {"class" : "photo-hover"}).find("img").get('src')
					addedOrReduced = advert.find("p", {"class" : "top-half listing-results-marketed"}).find("small").text.replace("Listed on","").replace("by","").strip()
					if addedOrReduced != None and addedOrReduced != "":
						addedOrReduced = parse(addedOrReduced)
					else:
						addedOrReduced = datetime.now().date()
					advertMatch['propId'] = propId
					advertMatch['link'] = propLink
					advertMatch['title'] = title
					advertMatch['address'] = address
					advertMatch['price'] = price
					advertMatch['displayPrice'] = displayPrice
					advertMatch['image1'] = image1
					advertMatch['pubDate'] = datetime.now()
					advertMatch['addedOrReduced'] = addedOrReduced
					advertMatch['reduced'] = reduced
					advertMatch['location'] = location
					
					saveToStore(advertMatch)
					
					matches += 1
			print("Found "+str(matches)+" Matches from "+str(numResults)+" Items of which "+str(numFeat)+" are Featured")
			if matches == 0 or (numResults-numFeat-2)>matches:
				break		
		else:
			print('No Search Results\n')
		
		if page < (numOfPages-1):
			next_page = driver.find_element_by_link_text('Next')
			next_page.click()
			time.sleep(sleepTime)
		page +=1 
	time.sleep(sleepTime)
driver.quit()
sys.exit(0)
