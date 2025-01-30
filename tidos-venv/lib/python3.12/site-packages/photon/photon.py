#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Let's import what we need
import tld
import sys
import time
import json
import random
import warnings
import threading
from math import log
from re import search, findall
from requests import get, post

try:
    from urllib.parse import urlparse # for python3
except ImportError:
    from urlparse import urlparse # for python2

warnings.filterwarnings('ignore') # Disable SSL related warnings

# Variables we are gonna use later to store stuff
keyss = set() # high entropy strings, prolly secret keys
files = set() # pdf, css, png etc.
intel = set() # emails, website accounts, aws buckets etc.
robots = set() # entries of robots.txt
custom = set() # string extracted by custom regex pattern
failed = set() # urls that photon failed to crawl
scripts = set() # javascript files
external = set() # urls that don't belong to the target i.e. out-of-scope
fuzzable = set() # urls that have get params in them e.g. example.com/page.php?id=2
endpoints = set() # urls found from javascript files
processed = set() # urls that have been crawled
storage = set() # urls that belong to the target i.e. in-scope

everything = []
bad_intel = set() # unclean intel urls
bad_scripts = set() # unclean javascript file urls

####
# This function makes requests to webpage and returns response body
####

def requester(url, delay, domain_name, user_agents, cookie, timeout):
    processed.add(url) # mark the url as crawled
    time.sleep(delay) # pause/sleep the program for specified time
    headers = {
    'Host' : domain_name, # ummm this is the hostname?
    'User-Agent' : random.choice(user_agents), # selecting a random user-agent
    'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language' : 'en-US,en;q=0.5',
    'Accept-Encoding' : 'gzip',
    'DNT' : '1',
    'Connection' : 'close'}
    # make request and return response
    response = get(url, cookies=cookie, headers=headers, verify=False, timeout=timeout, stream=True)
    if 'text/html' in response.headers['content-type']:
        if response.status_code != '404':
            return response.text
        else:
            response.close()
            failed.add(url)
            return 'dummy'
    else:
        response.close()
        return 'dummy'

####
# This function extracts links from robots.txt and sitemap.xml
####

def zap(main_url):
    response = get(main_url + '/robots.txt', verify=False).text # makes request to robots.txt
    if '<body' not in response: # making sure robots.txt isn't some fancy 404 page
        matches = findall(r'Allow: (.*)|Disallow: (.*)', response) # If you know it, you know it
        if matches:
            for match in matches: # iterating over the matches, match is a tuple here
                match = ''.join(match) # one item in match will always be empty so will combine both items
                if '*' not in match: # if the url doesn't use a wildcard
                    url = main_url + match
                    storage.add(url) # add the url to storage list for crawling
                    robots.add(url) # add the url to robots list
    response = get(main_url + '/sitemap.xml', verify=False).text # makes request to sitemap.xml
    if '<body' not in response: # making sure robots.txt isn't some fancy 404 page
        matches = findall(r'<loc>[^<]*</loc>', response) # regex for extracting urls
        if matches: # if there are any matches
            for match in matches:
                storage.add(match.split('<loc>')[1][:-6]) #cleaning up the url & adding it to the storage list for crawling

####
# This functions checks whether a url matches a regular expression
####

def remove_regex(urls, regex):
    """
    Parses a list for non-matches to a regex

    Args:
        urls: iterable of urls
        custom_regex: string regex to be parsed for

    Returns:
        list of strings not matching regex
    """

    if not regex:
        return urls

    # to avoid iterating over the characters of a string
    if not isinstance(urls, (list, set, tuple)):
        urls = [urls]

    try:
        non_matching_urls = [url for url in urls if not search(regex, url)]
    except TypeError:
        return []

    return non_matching_urls


####
# This functions checks whether a url should be crawled or not
####

def is_link(url):
    # file extension that don't need to be crawled and are files
    conclusion = False # whether the the url should be crawled or not

    if url not in processed: # if the url hasn't been crawled already
        if '.png' in url or '.jpg' in url or '.jpeg' in url or '.js' in url or '.css' in url or '.pdf' in url or '.ico' in url or '.bmp' in url or '.svg' in url or '.json' in url or '.xml' in url:
            files.add(url)
        else:
            return True # url can be crawled
    return conclusion # return the conclusion :D

####
# This function extracts string based on regex pattern supplied by user
####

supress_regex = False
def regxy(pattern, response):
    try:
        matches = findall(r'%s' % pattern, response)
        for match in matches:
            custom.add(match)
    except:
        supress_regex = True

####
# This function extracts intel from the response body
####

def intel_extractor(response):
    matches = findall(r'''([\w\.-]+s[\w\.-]+\.amazonaws\.com)|([\w\.-]+@[\w\.-]+\.[\.\w]+)''', response)
    if matches:
        for match in matches: # iterate over the matches
            bad_intel.add(match) # add it to intel list
####
# This function extracts js files from the response body
####

def js_extractor(response):
    matches = findall(r'src=[\'"](.*?\.js)["\']', response) # extract .js files
    for match in matches: # iterate over the matches
        bad_scripts.add(match)

####
# This function extracts stuff from the response body
####

def extractor(url, delay, domain_name, user_agents, cookie, timeout, regex, keys, only_urls, main_url):
    response = requester(url, delay, domain_name, user_agents, cookie, timeout) # make request to the url
    matches = findall(r'<[aA].*href=["\']{0,1}(.*?)["\']', response)
    for link in matches: # iterate over the matches
        link = link.split('#')[0] # remove everything after a "#" to deal with in-page anchors
        if is_link(link): # checks if the urls should be crawled
            if link[:4] == 'http':
                if link.startswith(main_url):
                    storage.add(link)
                else:
                    external.add(link)
            elif link[:2] == '//':
                if link.split('/')[2].startswith(domain_name):
                    storage.add(schema + link)
                else:
                    external.add(link)
            elif link[:1] == '/':
                storage.add(main_url + link)
            else:
                storage.add(main_url + '/' + link)

    if not only_urls:
        intel_extractor(response)
        js_extractor(response)
    if regex and not supress_regex:
        regxy(regex, response)
    if keys:
        matches = findall(r'\b[\w-]{16,45}\b', response)
        for match in matches:
            keyss.add(url + ': ' + match)

####
# This function extracts endpoints from JavaScript Code
####

def jscanner(url, delay, domain_name, user_agents, cookie, timeout, regex, keys, only_urls, main_url):
    response = requester(url, delay, domain_name, user_agents, cookie, timeout) # make request to the url
    matches = findall(r'[\'"](/.*?)[\'"]|[\'"](http.*?)[\'"]', response) # extract urls/endpoints
    for match in matches: # iterate over the matches, match is a tuple
        match = match[0] + match[1] # combining the items because one of them is always empty
        if not search(r'[}{><"\']', match) and not match == '/': # making sure it's not some js code
            endpoints.add(match) # add it to the endpoints list

####
# This function starts multiple threads for a function
####

def threader(function, delay, threads, domain_name, user_agents, cookie, timeout, regex, keys, only_urls, main_url, *urls):
    threadss = [] # list of threads
    urls = urls[0] # because urls is a tuple
    for url in urls: # iterating over urls
        task = threading.Thread(target=function, args=(url, delay, domain_name, user_agents, cookie, timeout, regex, keys, only_urls, main_url))
        threadss.append(task)
    # start threads
    for thread in threadss:
        thread.start()
    # wait for all threads to complete their work
    for thread in threadss:
        thread.join()
    # delete threads
    del threadss[:]

####
# This function processes the urls and sends them to "threader" function
####

def flash(function, links, threads, delay, domain_name, user_agents, cookie, timeout, regex, keys, only_urls, main_url): # This shit is NOT complicated, please enjoy
    links = list(links) # convert links (set) to list
    for begin in range(0, len(links), threads): # range with step
        end = begin + threads
        splitted = links[begin:end]
        threader(function, delay, threads, domain_name, user_agents, cookie, timeout, regex, keys, only_urls, main_url, splitted)

###
# Extracts top level domain
###

def topLevel(url):
    ext = tld.get_tld(url, fix_protocol=True)
    toplevel = '.'.join(urlparse(url).netloc.split('.')[-2:]).split(ext)[0] + ext
    return toplevel

def crawl(main_inp, delay = 0, timeout = 6, regex = False, cookie = None, keys = False, level = 2, threads = 2, only_urls = False, exclude = False, seeds = [], user_agent = False, format = False):

    if main_inp.endswith('/'): # if the url ends with '/'
        main_inp = main_inp[:-1] # we will remove it as it can cause problems later in the code

    # If the user hasn't supplied the root url with http(s), we will handle it
    if main_inp.startswith('http'):
        main_url = main_inp
    else:
        try:
            get('https://' + main_inp)
            main_url = 'https://' + main_inp
        except:
            main_url = 'http://' + main_inp

    domain_name = topLevel(main_url) # Extracts domain out of the url

    storage.add(main_url) # adding the root url to storage for crawling

    for url in seeds:
        storage.add(url)

    if user_agent:
        user_agents = user_agent
    else:
        from .user_agents_db import user_agents_list
        user_agents = user_agents_list()

    # Step 1. Extract urls from robots.txt & sitemap.xml
    zap(main_url)

    # Step 2. Crawl recursively to the limit specified in "level"
    for level in range(level):
        links = remove_regex(storage - processed, exclude) # links to crawl = all links - already crawled links
        if not links: # if links to crawl are 0 i.e. all links have been crawled
            break
        elif len(storage) <= len(processed): # if crawled links are somehow more than all links. Possible? ;/
            if len(storage) > 2 + len(seeds): # if you know it, you know it
                break
        flash(extractor, links, threads, delay, domain_name, user_agents, cookie, timeout, regex, keys, only_urls, main_url)

    if not only_urls:
        for match in bad_scripts:
            if match.startswith(main_url):
                scripts.add(match)
            elif match.startswith('/') and not match.startswith('//'):
                scripts.add(main_url + match)
            elif not match.startswith('http') and not match.startswith('//'):
                scripts.add(main_url + '/' + match)
    # Step 3. Scan the JavaScript files for enpoints
    flash(jscanner, scripts, threads, delay, domain_name, user_agents, cookie, timeout, regex, keys, only_urls, main_url)
    for url in storage:
        if '=' in url:
            fuzzable.add(url)
    for match in bad_intel:
        for x in match: # because "match" is a tuple
            if x != '': # if the value isn't empty
                intel.add(x)
    for url in external:
        if 'github.com' in url or 'facebook.com' in url or 'instagram.com' in url or 'youtube.com' in url:
            intel.add(url)
    if format == 'json':
        return result(format='json')
    else:
        return result()

def clear():
    sets = [keyss, files, intel, robots, custom, failed, scripts, external, fuzzable, endpoints, processed, storage, bad_intel, bad_scripts]
    for i in sets:
        i.clear()

def result(format = False):
    datasets = {
    'files': list(files), 'intel': list(intel), 'robots': list(robots), 'custom': list(custom), 'failed': list(failed), 'internal': list(storage),
    'scripts': list(scripts), 'external': list(external), 'fuzzable': list(fuzzable), 'endpoints': list(endpoints), 'keys' : list(keyss)
    }
    if format == 'json':
        return json.dumps(result(), indent=4)
    else:
        return datasets