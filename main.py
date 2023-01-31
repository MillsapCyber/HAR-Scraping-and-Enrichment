from email.mime import base
from multiprocessing import reduction
from xml.dom.minidom import Element
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from subprocess import Popen
from copy import deepcopy

import sys
import re
import time
import json
import requests

def extractHARFilters(link):
    retval = {}
    if not link.startswith("https://www.har.com/search/dosearch?"):
        print("Incorrect base link provided")
        exit(1)
    link = link.replace("https://www.har.com/search/dosearch?", "")
    args = link.split("&")
    for arg in args:
        tmp = arg.split("=")
        retval[tmp[0]] = tmp[1]
    return retval

def getListings(args):
    links = []
    page_number = 1


    options = Options()
    options.add_argument('--headless')
    browser = webdriver.Firefox(options=options)


    while(True):
        target_url = "https://www.har.com/search/dosearch?view=list&page={}".format(str(page_number))

        # build url with desired querys
        args_list = list(args.keys())
        for arg in args_list:
            target_url = target_url + "&" + arg + "=" + args[arg]

        # call HAR
        browser.get(target_url)
        
        # check if there are any listings available
        if(browser.find_element(By.XPATH, '//*[@id="noresults_message"]').is_displayed()):
            break
        else:
            print("Harvesting listings from page: {}".format(page_number), end='\r')

            elements = browser.find_elements(By.CLASS_NAME, "listing-card-item")
            for element in elements:
                current_link = element.find_element(By.CLASS_NAME, "photolink")
                # print(current_link.get_attribute("href"))
                links.append(current_link.get_attribute("href"))
        page_number = page_number + 1
    browser.close()
    if len(links) == 0:
        print("There are no listings within your criteria. Please adjust filters and try again.")
        exit(1)
    return links

def evaluateListing(link):
    options = Options()
    options.add_argument('--headless')
    browser = webdriver.Firefox(options=options)

    browser.get(link)

    # get rows
    rows = browser.find_elements(By.CLASS_NAME, "row")

    evaluatedListing = {}
    evaluatedListing['link'] = link
    for row in rows:
        if "MLS#" in row.text and "List Price" in row.text and "Listing Status" in row.text and "Address" in row.text and "City" in row.text and "State" in row.text and "Zip Code" in row.text and "County" in row.text and "Subdivision" in row.text and "Legal Description" in row.text and "Property Type" in row.text and "Bedroom" in row.text and "Bath" in row.text and "Garages" in row.text and "Stories" in row.text and "Building Size" in row.text and "Architecture Style" in row.text and "Year Built" in row.text and "Lot Size" in row.text and "Key Map©" in row.text and "Market Area" in row.text: 
            data = row.text.split('\n')
            i = 0
            for i in range(0, len(data) - 1):
                
                if i % 2 == 0:
                    evaluatedListing[data[i]] = ''
                else: 
                    evaluatedListing[data[i - 1]] = data[i]
        if re.search("[0-9]+x[0-9]+", row.text):
            data = row.text.replace(', ', '\n').replace(' ', '\n').split('\n')
            i = 0
            for i in range(0, len(data) - 1):
                
                if i + 1 % 3 == 2:
                    evaluatedListing[data[i - 1] + " " + data[i]] = ''
                if (i + 1) % 3 == 0: 
                    evaluatedListing[data[i - 2] + " " + data[i - 1]] = data[i]
        if "Roof" in row.text and "Foundation" in row.text and "Private Pool" in row.text and "Exterior Type" in row.text and "Water Sewer" in row.text and "Area Pool" in row.text:
            data = row.text.split('\n')
            i = 0
            for i in range(0, len(data) - 1):
                
                if i % 2 == 0:
                    evaluatedListing[data[i]] = ''
                else: 
                    evaluatedListing[data[i - 1]] = data[i]
            # print(evaluatedListing)
        if "Fireplace" in row.text and "Floors" in row.text and "Bathroom Description" in row.text and "Bedroom Description" in row.text and "Room Description" in row.text and "Cooling" in row.text and "Heating" in row.text and "Dishwasher" in row.text and "Disposal" in row.text and "Oven" in row.text and "Appliances" in row.text: 
            data = row.text.split('\n')
            i = 0
            for i in range(0, len(data) - 1):
                
                if i % 2 == 0:
                    evaluatedListing[data[i]] = ''
                else: 
                    evaluatedListing[data[i - 1]] = data[i]

            


    browser.close()
    return evaluatedListing

def evaluateListings(links):
    evaluatedListings = []
    i = 1
    for link in links:
        evaluatedListings.append(deepcopy(evaluateListing(link)))
        print("evaluated listing {} of {}".format(i, len(links)), end='\r')

        i = i + 1
    return evaluatedListings
    
def printListings(evaluated_listings):
    for listing in evaluated_listings:
        print(json.dumps(listing, indent=2))

def enrichListingsWithFiberData(evaluated_listings):
    retval = []
    payload={}
    headers = {}

    for listing in evaluated_listings:
        url = "https://www.att.com/services/shop/model/ecom/shop/view/unified/qualification/service/CheckAvailabilityRESTService/invokeCheckAvailability?userInputZip={}&userInputAddressLine1={}&mode=fullAddress".format(listing['Zip Code'], listing['Address'])
        response_data = json.loads(requests.request("GET", url, headers=headers, data=payload).text)
        listing['Fiber'] = response_data['profile']['isGIGAFiberAvailable']
        retval.append(listing)
        # artifical wait to avoid api rate limiting
        time.sleep(1)
        
    return retval

def filterListingsByFiber(evaluated_listings):
    retval = []
    for listing in evaluated_listings:
        if listing['Fiber'] == True:
            retval.append(listing)
    return retval

if __name__ == "__main__":
    # set your filters up in har, then pass that link into extractHARFilters like in the following example, which searches every listing in texas for a 3 bed 2 bath <= $250,000
    args = extractHARFilters("https://www.har.com/search/dosearch?for_sale=1&listing_price_max=250000&bedroom_min=3&full_bath_min=2&property_class_id=1")    
    # apply filters and gather listings
    listings = getListings(args)
    # scrape data from gathered listings
    evaluated_listings = evaluateListings(listings)
    # enrich data with fiber availability
    evaluated_listings = enrichListingsWithFiberData(evaluated_listings)

    printListings(evaluated_listings)
