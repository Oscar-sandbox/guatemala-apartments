# -*- coding: utf-8 -*-
"""
Created on Sun Mar  9 22:31:31 2025
@author: oscar
"""

import json
import time
import re

import numpy as np
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import Select

driver = webdriver.Chrome()
main_url = 'https://citymap.com.gt'

# XPath locations of web elements to find. 
locs = {
    'project_url': f'//a[starts-with(@href, "{main_url}/propiedades")]',
    'apartment_type': '//div[@class="info-90"]//h2',
    'apartment_info': '//div[@class="info-90"]//table[@class="info-tab-table"]',
    'project_description': '//meta[@name="description"]',
    'project_graph': '//script[@class="yoast-schema-graph"]',
    'project_zone': '//a[starts-with(@href, "/property_area")]',
    'project_status': '//div[@class="lanzamiento lanzamientoTabs"]//a',
    'project_latlon': '//a[@id="view_in_maps"]',
}

info_list = []
visited_urls = set()

# If execution is interrupted, load already visited urls. 
info_list = [pd.read_csv('citymap_apartments_20230318.csv')]
visited_urls = set(info_list[0]['project_url'].tolist())
visited_urls.add('https://citymap.com.gt/propiedades/n-americas/')

for i_page in range(1,9):
    
    # Iterate over every project in every page in the website. 
    driver.get(main_url + f'/proyectos-de-apartamentos-en-guatemala/?sf_paged={i_page}')
    projects = driver.find_elements(By.XPATH, locs['project_url'])
    project_urls = set([e.get_attribute('href') for e in projects])
    
    for u in project_urls:
        
        # Check if the project current has been visited before. 
        if u in visited_urls: continue
        visited_urls.add(u)
        driver.get(u)
        print(len(visited_urls), u)
        time.sleep(3)

        # Read apartment types and their info tables. 
        info_e = driver.find_elements(By.XPATH, locs['apartment_info'])
        type_e = driver.find_elements(By.XPATH, locs['apartment_type'])
        
        assert len(info_e) == len(type_e), 'Could not read apartment info.'
        if not len(info_e): continue
        
        info = []
        for j in range(len(info_e)):
            df = pd.read_html(info_e[j].get_attribute('outerHTML'))[0]
            df = df\
                .drop(columns=0)\
                .set_index(1)\
                .transpose()\
                .assign(apartment_type=type_e[j].get_attribute('innerHTML'))
            info.append(df)
        info = pd.concat(info, ignore_index=True)
        
        # Append the project's name and URL. 
        info['project_name'] = re.search('propiedades/(.+)/', u).group(1)
        info['project_url'] = u
        
        # Append the project's description.
        try: 
            info['project_description'] = driver\
                .find_element(By.XPATH, locs['project_description'])\
                .get_attribute('content')    
        except NoSuchElementException: 
            print('No description found.')
        
        # Append the published and modified dates of the webpage. 
        # Append the thumbnail image of the webpage. 
        try: 
            graph = driver\
                .find_element(By.XPATH, locs['project_graph'])\
                .get_attribute('innerHTML')
            graph = json.loads(graph)
            info['project_c_time'] = graph['@graph'][0]['datePublished']
            info['project_m_time'] = graph['@graph'][0]['dateModified']
            info['project_img_url'] = graph['@graph'][0]['thumbnailUrl']
        except NoSuchElementException: 
            print('No dates or image found.')
           
        # Append the project's zone.
        try: 
            zone = driver\
                .find_element(By.XPATH, locs['project_zone'])\
                .get_attribute('href')    
            info['project_zone'] = re.search('/property_area/(.+)', zone).group(1)
        except NoSuchElementException: 
            print('No zone found.')
        
        # Append the project's status. 
        try:  
            info['project_status'] = driver\
                .find_element(By.XPATH, locs['project_status'])\
                .get_attribute('innerHTML')
        except NoSuchElementException: 
            print('No status found.')
        
        # Append the project's latitude and longitude.  
        try: 
            latlon = driver\
                .find_element(By.XPATH, locs['project_latlon'])\
                .get_attribute('href')
            lat, lon = re.search('query=(.+?),(.+)', latlon).groups()
            info['project_lat'], info['project_lon'] = lat, lon
        except NoSuchElementException: 
            print('No location found.')
            
        info_list.append(info)  
        pd\
            .concat(info_list, ignore_index=True)\
            .to_csv('citymap_apartments_20230318.csv', index=False)          
        
driver.close()