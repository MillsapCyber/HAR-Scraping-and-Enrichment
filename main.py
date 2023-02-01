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
    if "view" in retval.keys():
        del retval['view']
    if "page" in retval.keys():
        del retval['page']
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
            print("Harvesting listings from page: {}".format(page_number), end="\x1b[1K\r")

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
            # and "Stories" in row.text
            and "Building Size" in row.text
            and "Year Built" in row.text
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
    if "Zip Code" not in evaluated_listing.keys():
        print("Listing may not have been scraped correctly.\n\t{}".format(evaluated_listing["link"]))
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
        print("evaluated listing {} of {}".format(i, len(links)), end="\x1b[1K\r")

        i = i + 1
    print()
    return evaluated_listings


def print_listings(evaluated_listings):
    """print_listings a print function for arrays of json objects

    Args:
        evaluated_listings (json[]): jsonp[] returned by evaluate_listings
    """
    if len(evaluated_listings) == 0:
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

    error_listings = []

    for listing in evaluated_listings:
        url = "https://www.att.com/services/shop/model/ecom/shop/view/unified/qualification/service/CheckAvailabilityRESTService/invokeCheckAvailability?userInputZip={}&userInputAddressLine1={}&mode=fullAddress".format(
            listing["Zip Code"], listing["Address"]
        )
        print("Fetching AT&T Fiber Data for: {}".format(listing["Address"]), end="\x1b[1K\r")

        response = requests.request("GET", url, headers=headers, data=payload)
        if response.status_code == 200:
            response_data = json.loads(response.text)
        else:
            print("Error fetching AT&T Fiber data for {}".format(listing['link']))
            error_listings.append(listing)
        listing["Fiber"] = response_data["profile"]["isGIGAFiberAvailable"]
        retval.append(listing)
        # artifical wait to avoid api rate limiting
        time.sleep(5)

    # ToDo: make this more elegant
    # retry errors once
    for listing in error_listings:
        print("Retrying fiber data fetch: {}".format(listing['link']))
        time.sleep(5)
        url = "https://www.att.com/services/shop/model/ecom/shop/view/unified/qualification/service/CheckAvailabilityRESTService/invokeCheckAvailability?userInputZip={}&userInputAddressLine1={}&mode=fullAddress".format(
            listing["Zip Code"], listing["Address"]
        )
        print("Fetching AT&T Fiber Data for: {}".format(listing["Address"]), end="\x1b[1K\r")

        response = requests.request("GET", url, headers=headers, data=payload)
        if response.status_code == 200:
            response_data = json.loads(response.text)
        else:
            print("Error fetching AT&T Fiber data for {}".format(listing['link']))
        listing["Fiber"] = response_data["profile"]["isGIGAFiberAvailable"]
        retval.append(listing)
        # artifical wait to avoid api rate limiting
        time.sleep(5)
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
        if listing["Fiber"] == True:
            retval.append(listing)
    return retval


if __name__ == "__main__":
    # set your filters up in har, then pass that link into extract_har_filters, like the following
    # example which searches every listing in texas for a 3 bed 2 bath <= $100,000
    # arguments = extract_har_filters(
    #     "https://www.har.com/search/dosearch?for_sale=1&listing_price_max=100000&bedroom_min=3&full_bath_min=2&all_status=A&sort=listdate%20desc&view=list"
    # )
    arguments = extract_har_filters("https://www.har.com/search/dosearch?map_tools_polygon=POLYGON((-95.7360863685608%2030.0864028930664,-95.7268810272217%2030.0818753242493,-95.7002735137939%2030.0796222686768,-95.6977200508118%2030.0587439537048,-95.667507648468%2030.0503540039063,-95.6619071960449%2030.0569415092468,-95.6742882728577%2029.9772477149963,-95.6731295585632%2029.9551463127136,-95.6717991828918%2029.9539875984192,-95.6590962409973%2029.9457263946533,-95.6546759605408%2029.9402761459351,-95.6436038017273%2029.9322724342346,-95.6362652778625%2029.9273586273193,-95.6298494338989%2029.9238181114197,-95.6512856483459%2029.896502494812,-95.6495475769043%2029.8957085609436,-95.654354095459%2029.8791646957397,-95.6453633308411%2029.8798084259033,-95.6452989578247%2029.8761391639709,-95.6340765953064%2029.867684841156,-95.6451272964478%2029.8633503913879,-95.6450414657593%2029.857234954834,-95.6455135345459%2029.8513126373291,-95.6411576271057%2029.8413133621216,-95.6149363517761%2029.8361420631409,-95.6456208229065%2029.830584526062,-95.6103444099426%2029.8203706741333,-95.6165671348572%2029.8135471343994,-95.6175541877747%2029.8099851608276,-95.5684804916382%2029.7850298881531,-95.5803680419922%2029.78520154953,-95.60626745224%2029.7748804092407,-95.6080269813538%2029.7700309753418,-95.6207513809204%2029.7719192504883,-95.6438827514648%2029.7670912742615,-95.6374025344849%2029.7559332847595,-95.6445479393005%2029.7476291656494,-95.6445479393005%2029.7474789619446,-95.685510635376%2029.7748589515686,-95.6955528259277%2029.7759318351746,-95.6688165664673%2029.7278237342834,-95.6659197807312%2029.7092413902283,-95.6782150268555%2029.7084259986877,-95.6843090057373%2029.707932472229,-95.6945013999939%2029.7070741653442,-95.7043075561523%2029.7061944007874,-95.7069039344788%2029.6426582336426,-95.7146716117859%2029.6521425247192,-95.7379746437073%2029.6551036834717,-95.7418370246887%2029.6628713607788,-95.7566857337952%2029.6749091148376,-95.7650542259216%2029.679479598999,-95.785825252533%2029.6834921836853,-95.796103477478%2029.6845436096191,-95.8043217658997%2029.6836423873901,-95.8161234855652%2029.6857023239136,-95.8283758163452%2029.689028263092,-95.8459496498108%2029.6928477287292,-95.8459496498108%2029.6938347816467,-95.8461427688599%2029.7116446495056,-95.8797240257263%2029.6965169906616,-95.8812046051025%2029.7090697288513,-95.916759967804%2029.7075462341309,-95.9178972244263%2029.7094988822937,-95.9382820129395%2029.7219657897949,-95.929913520813%2029.7312998771667,-95.9436893463135%2029.7505044937134,-95.9879350662231%2029.7404193878174,-95.9803605079651%2029.75745677948,-96.0440468788147%2029.7638940811157,-96.0644745826721%2029.772047996521,-95.975489616394%2029.8068952560425,-95.9760689735413%2029.8073244094849,-95.8901309967041%2029.8309707641602,-95.8902168273926%2029.8398327827454,-95.9073400497437%2029.848780632019,-95.8903455734253%2029.8532009124756,-95.9599757194519%2029.8741221427917,-95.9104299545288%2029.8741865158081,-95.8906030654907%2029.8743367195129,-95.8907532691956%2029.8888421058655,-95.8739948272705%2029.8887991905212,-95.8619999885559%2029.8889923095703,-95.8198356628418%2029.8748087882996,-95.8241057395935%2029.8893141746521,-95.8334612846375%2029.9038195610046,-95.8242344856262%2029.9038410186768,-95.8199214935303%2029.9038624763489,-95.8127760887146%2029.9039483070374,-95.8076691627502%2029.9157285690308,-95.9167385101318%2030.0666618347168,-95.8863544464111%2030.0555038452148,-95.8525371551514%2030.0368356704712,-95.8418297767639%2030.0731205940247,-95.8363151550293%2030.0693011283875,-95.8174967765808%2030.0695157051086,-95.7816410064697%2030.0418782234192,-95.7722425460815%2030.0276947021484,-95.753231048584%2030.078763961792,-95.7360863685608%2030.0864028930664))&drivetime_address=4239%20Monticello%20Terrace%20Lane,%20Katy,%20Texas%2077449&drivetime_arrival_time=18:00&drivetime_travel_time=30&drivetime_center=29.835755,-95.74777&for_sale=0&prop_type=SGL&lease_price_max=2000&pets=Yes&all_status=A&sort=listprice%20asc&view=list")
    # apply filters and gather listings
    listings = get_listings(arguments)
    # scrape data from gathered listings
    processed_listings = evaluate_listings(listings)
    # enrich data with fiber availability
    processed_listings = enrich_listings_with_fiber_data(processed_listings)

    print_listings(processed_listings)
