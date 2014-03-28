#!/usr/bin/python
from urllib2 import urlopen, URLError
import re
import os
import json
from roman import fromRoman
import time
from random import random
import time

SITE_ROOT_URL = 'http://ebooks.library.cornell.edu'
MAGAZINE_ROOT_URL = '/n/nora'
VOLUME_URL_FILE = 'nora-volume-urls-clean.txt'

vol_urls = []

# load text file with urls of each volume (i.e. year)
try:
    with open(VOLUME_URL_FILE, 'r') as f:
        for url in f:
            vol_urls.append((SITE_ROOT_URL + MAGAZINE_ROOT_URL + "/"+ url).strip('\n'))
except IOError as e:
    print "I/O error({0}): {1}".format(e.errno, e.strerror)
    exit()

page_nums_readable = True

# loop through all urls
for vol_url in vol_urls:
    print "volume " + vol_url
    # make directory for volume
    vol_dir = re.search(r'.*/(.*).html$', vol_url).group(1)
    try:
        print "creating new directory: {0}".format(vol_dir)
        os.mkdir(vol_dir)
    except OSError:
        print "ERROR: can't create directory {0}".format(vol_dir)
        exit()
        
    # for each volume url, get the urls for each issue
    # first request the page
    try:
        u = urlopen(vol_url)
        page = u.read()
    except URLError, e:
        print "ERROR: URL error({0}): {1}".format(e.errno, e.strerror)
            
    # then extract the issue URLs
    # example: "/cgi/t/text/text-idx?c=nora;cc=nora;view=toc;subview=short;idno=nora0001-1"
    iss_urls = []
    matches = re.finditer(r'"/cgi/t/text/text-idx.*"', page)
    if matches:
        for m in matches:
            iss_urls.append(SITE_ROOT_URL + m.group(0).strip(r'"'))

        # loop through issues
        for iss_url in iss_urls:
            print "... issue " + iss_url
            # make subdirectory for this issue
            iss_dir = re.search(r'.*=(.*)$', iss_url).group(1)
            try:
                print "... creating new directory: {0}".format(vol_dir + "/" + iss_dir)
                os.mkdir(vol_dir + "/" + iss_dir)
            except OSError:
                print "ERROR: can't create directory {0}".format(vol_dir + "/" + iss_dir)
                exit()
        
            # get page
            try:
                u = urlopen(iss_url)
                page = u.read()
            except URLError, e:
                print "ERROR: URL error({0}): {1}".format(e.errno, e.strerror)
        
            # extract article URLs
            # loop through article URLs
            art_urls = []
            art_auths = []
            art_pages = []
            art_titles = []
            matches = re.finditer(r'"http://ebooks.library.cornell.edu/cgi/t/text/pageviewer-idx.*?</div></span></div>', page)
            if matches:
                for m in matches:
                    # print m.group(0)
                    art_urls.append(re.search(r'"(.*?)"', m.group(0)).group(1).strip(r'"')) # extract just the URL part
                    art_auths.append(re.search(r'articleauthor">(.*)pp.', m.group(0)).group(1).strip(' ,')) # extract author nanme
                    p = re.search(r'\W([-\w]*?)</div>', m.group(0)).group(1).strip()
                    # print "pages " + p
                    art_pages.append(p) # extract page number string
                    art_titles.append(re.search(r'articletitle">(.*)</a', m.group(0)).group(1).strip(' ,')) # extract title

                for i in range(0,len(art_urls)):
                    art_url = art_urls[i]
                    art_page = art_pages[i]
                    art_auth = art_auths[i]
                    art_title = art_titles[i]

                    print '... ... article ' + art_url

                    # make a sub-subdirectory for the article                    
                    art_dir = re.search(r'.*%3(.*)$', art_url).group(1)
                    try:
                        print "... ... creating new directory: {0}".format(vol_dir + "/" + iss_dir + "/" + art_dir)
                        os.mkdir(vol_dir + "/" + iss_dir + "/" + art_dir)
                    except OSError:
                        print "ERROR: can't create directory {0}".format(vol_dir + "/" + iss_dir + "/" + art_dir)
                        exit()

                    # get number of pages, which might be in roman numerals, and night be only a single page rather than page range
                    page_nums_readable = True
                    if '-' in art_page:    
                        s = art_page.split('-')
                        start_page = s[0].strip()
                        end_page = s[1].strip()
                    else:           # just a single page
                        start_page = art_page.strip()
                        end_page = art_page.strip()
                    try:
                        temp_start_page = int(start_page)
                        temp_end_page = int(end_page)
                        start_page = temp_start_page
                        end_page = temp_end_page                        
                    except ValueError:
                        try:
                            start_page = int(fromRoman(start_page.upper())) # fromRoman expects upper case roman numerals
                            end_page = int(fromRoman(end_page.upper()))
                        except:
                            print "WARNING: page numbers {0} couldn't be processed, skipping attempt to read article contents".format(art_page)
                            page_nums_readable = False
                            num_pages = None

                    # print "art_page " , art_page, " start ", start_page, " end ", end_page   

                    # print "num_pages ",  num_pages
                    
                    # loop through pages, downloading
                    
                    content = {}
                    if page_nums_readable:
                        num_pages = 1 + end_page - start_page
                        start_seq = int(re.search(r'seq=([0-9]*?);', art_url).group(1))
                        # print "seq ", start_seq           
                        for p in range(0,num_pages):
                            # generate URL for page by substituting in proper number for seq
                            seq_int = start_seq + p
                            if seq_int > 999: # add leading zeros so it's 4 digits
                                seq_str = str(seq_int)
                            elif seq_int > 99:
                                seq_str = "0" + str(seq_int)
                            elif seq_int > 9:
                                seq_str = "00" + str(seq_int)
                            else:
                                seq_str = "000" + str(seq_int)                                           
                            page_url = re.sub(r'view=image;', r'view=text;', art_url)
                            page_url = re.sub(r'seq=([0-9]*?);', "seq="+seq_str+";", page_url)
                            print '... ... ... page {0}/{1} {2}'.format(p+1, num_pages, page_url)
                            # get page                  
                            try:
                                u = urlopen(page_url)
                                page = u.read()
                            except URLError, e:
                                print "ERROR: URL error({0}): {1}".format(e.errno, e.strerror)
                            
                            match = re.search(r'pvdoccontent">(.*?)</div', page, re.DOTALL)
                            if match:
                                content[str(p)] = match.group(1)
                                # print content[str(p)]
                            else:
                                print "... ... ... no match found in page {0}".format(p)

                            # time.sleep(1 + random() * 2)
 
                    # assemble structure that will be output as json in article file
                    out = {"title": art_title, "author":art_auth,  "page_range":art_page, "num_pages": num_pages,
                           "url": art_url, "volume": vol_dir, "issue": iss_dir, "id":art_dir}                          
                    out['pages'] = content
                    art_filename = '{0}.json'.format(art_dir)  
                    # print out
          
                    # write file as json                   
                    try:
                        with open(vol_dir + "/" + iss_dir + "/" + art_dir + "/" + art_filename,'w') as f:
                            f.write(json.dumps(out))
                    except IOError as e:
                        print "ERROR: I/O error({0}): {1}".format(e.errno, e.strerror)

                    time.sleep(5 + random() * 5)


