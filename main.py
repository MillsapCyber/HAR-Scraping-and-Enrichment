from copy import deepcopy
import re
import time
import json
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options


def extract_har_filters(link):
    """extract_har_filters parses filters out of a har link

    Args:
        link (string): Generate a search on har.com and copy the link from the browser

    Returns:
        json: a json representation of all the get parameters from the har search
    """
    retval = {}
    if not link.startswith("https://www.har.com/search/dosearch?"):
        print("Incorrect base link provided. Your link should resemble the following: https://www.har.com/search/dosearch?argument=value")
        print("You may be searching by city, try searching by map bounds instead")
        print("Trying to continue")
    
    # try to continue anyway
    link = re.sub("https:\/\/www\.har\.com\/.*\?", "", link)
    args = link.split("&")
    for arg in args:
        tmp = arg.split("=")
        retval[tmp[0]] = tmp[1]
    return retval


def get_listings(args):
    """get_listings Scrapes a har search page for the links to each listing.
    It also traverses multi-page searches.

    Args:
        args (json): a json representation of a har.com filter

    Returns:
        string[]: all the links of each listing withing the specified search.
    """
    links = []
    page_number = 1

    options = Options()
    options.add_argument("--headless")
    browser = webdriver.Firefox(options=options)

    while True:
        target_url = "https://www.har.com/search/dosearch?view=list&page={}".format(
            str(page_number)
        )

        # build url with desired querys
        args_list = list(args.keys())
        for arg in args_list:
            target_url = target_url + "&" + arg + "=" + args[arg]

        # call HAR
        browser.get(target_url)

        # check if there are any listings available
        if browser.find_element(
            By.XPATH, '//*[@id="noresults_message"]'
        ).is_displayed():
            break
        else:
            print("Harvesting listings from page: {}".format(page_number), end="\r")

            elements = browser.find_elements(By.CLASS_NAME, "listing-card-item")
            for element in elements:
                current_link = element.find_element(By.CLASS_NAME, "photolink")
                # print(current_link.get_attribute("href"))
                links.append(current_link.get_attribute("href"))
        page_number = page_number + 1
    browser.close()
    if len(links) == 0:
        print(
            "There are no listings within your criteria. Please adjust filters and try again."
        )
        exit(1)
    print()
    return links


def evaluate_listing(link):
    """evaluate_listing Scrapes data from an individual listing on har.com into json

    Args:
        link (string): the link of an individual listing on har.com

    Returns:
        json: all the json data for the listing
    """
    options = Options()
    options.add_argument("--headless")
    browser = webdriver.Firefox(options=options)

    browser.get(link)

    # get rows
    rows = browser.find_elements(By.CLASS_NAME, "row")

    evaluated_listing = {}
    evaluated_listing["link"] = link
    for row in rows:
        if (
            "MLS#" in row.text
            and "List Price" in row.text
            and "Listing Status" in row.text
            and "Address" in row.text
            and "City" in row.text
            and "State" in row.text
            and "Zip Code" in row.text
            and "County" in row.text
            and "Subdivision" in row.text
            and "Legal Description" in row.text
            and "Property Type" in row.text
            and "Bedroom" in row.text
            and "Bath" in row.text
            and "Garages" in row.text
            and "Stories" in row.text
            and "Building Size" in row.text
            and "Architecture Style" in row.text
            and "Year Built" in row.text
            and "Lot Size" in row.text
            and "Key Map©" in row.text
            and "Market Area" in row.text
        ):
            data = row.text.split("\n")
            i = 0
            for i in range(0, len(data) - 1):

                if i % 2 == 0:
                    evaluated_listing[data[i]] = ""
                else:
                    evaluated_listing[data[i - 1]] = data[i]
        if re.search("[0-9]+x[0-9]+", row.text):
            data = row.text.replace(", ", "\n").replace(" ", "\n").split("\n")
            i = 0
            for i in range(0, len(data) - 1):

                if i + 1 % 3 == 2:
                    evaluated_listing[data[i - 1] + " " + data[i]] = ""
                if (i + 1) % 3 == 0:
                    evaluated_listing[data[i - 2] + " " + data[i - 1]] = data[i]
        if (
            "Roof" in row.text
            and "Foundation" in row.text
            and "Private Pool" in row.text
            and "Exterior Type" in row.text
            and "Water Sewer" in row.text
            and "Area Pool" in row.text
        ):
            data = row.text.split("\n")
            i = 0
            for i in range(0, len(data) - 1):

                if i % 2 == 0:
                    evaluated_listing[data[i]] = ""
                else:
                    evaluated_listing[data[i - 1]] = data[i]
            # print(evaluated_listing)
        if (
            "Fireplace" in row.text
            and "Floors" in row.text
            and "Bathroom Description" in row.text
            and "Bedroom Description" in row.text
            and "Room Description" in row.text
            and "Cooling" in row.text
            and "Heating" in row.text
            and "Dishwasher" in row.text
            and "Disposal" in row.text
            and "Oven" in row.text
            and "Appliances" in row.text
        ):
            data = row.text.split("\n")
            i = 0
            for i in range(0, len(data) - 1):

                if i % 2 == 0:
                    evaluated_listing[data[i]] = ""
                else:
                    evaluated_listing[data[i - 1]] = data[i]

    browser.close()
    return evaluated_listing


def evaluate_listings(links):
    """evaluate_listings Calls evaluate_listing on an array of links

    Args:
        links (string[]): An array of strings containing har.com listing links

    Returns:
        json array: a json array of all listings that were passed in the links array
    """
    evaluated_listings = []
    i = 1
    for link in links:
        evaluated_listings.append(deepcopy(evaluate_listing(link)))
        print("evaluated listing {} of {}".format(i, len(links)), end="\r")

        i = i + 1
    print()
    return evaluated_listings


def print_listings(evaluated_listings):
    """print_listings a print function for arrays of json objects

    Args:
        evaluated_listings (json[]): jsonp[] returned by evaluate_listings
    """
    if len(evaluate_listings) == 0:
        print("No listings found.")
    for listing in evaluated_listings:
        print(json.dumps(listing, indent=2))


def enrich_listings_with_fiber_data(evaluated_listings):
    """enrich_listings_with_fiber_data add a bool to each listings json indicating wether or not the listing has fiber internet available

    Args:
        evaluated_listings (json[]): json[] returned by evaluate_listings

    Returns:
        _type_: _description_
    """
    retval = []
    payload = {}
    headers = {}

    for listing in evaluated_listings:
        url = "https://www.att.com/services/shop/model/ecom/shop/view/unified/qualification/service/CheckAvailabilityRESTService/invokeCheckAvailability?userInputZip={}&userInputAddressLine1={}&mode=fullAddress".format(
            listing["Zip Code"], listing["Address"]
        )
        response_data = json.loads(
            requests.request("GET", url, headers=headers, data=payload).text
        )
        listing["Fiber"] = response_data["profile"]["isGIGAFiberAvailable"]
        retval.append(listing)
        # artifical wait to avoid api rate limiting
        time.sleep(1)

    return retval


def filter_listings_by_fiber(evaluated_listings):
    """filter_listings_by_fiber only returns listings that have fiber service, disgards the rest.

    Args:
        evaluated_listings (json[]): an array of json objects generated by evaluate_listings

    Returns:
        json[]: the same as the passed argument but without any listings that don't have fiber
    """
    retval = []
    for listing in evaluated_listings:
        if listing["Fiber"]:
            retval.append(listing)
    return retval


if __name__ == "__main__":
    # set your filters up in har, then pass that link into extract_har_filters 
    # which searches every listing in texas for a 3 bed 2 bath <= $250,000
    arguments = extract_har_filters(
        "https://www.har.com/katy/realestate/for_sale?listing_price_max=250000&bedroom_min=3&full_bath_min=2&all_status=A&sort=listdate%20desc&view=list"
    )
    # apply filters and gather listings
    listings = get_listings(arguments)
    # scrape data from gathered listings
    processed_listings = evaluate_listings(listings)
    # enrich data with fiber availability
    processed_listings = enrich_listings_with_fiber_data(processed_listings)

    print_listings(processed_listings)
