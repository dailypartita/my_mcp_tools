import os
import json
import time
import asyncio
import logging
import aiohttp
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()
mcp = FastMCP("epi-crawl")
time_now = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

class FireCrawl:
    def __init__(self, url):
        
        self.logger = logging.getLogger(__name__)
        self.FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY')
        self.FIRECRAWL_ENDPOINT = os.getenv('FIRECRAWL_ENDPOINT')
        self.url = url
        self.url_snap = url.split('/')[3] + ', ' + url.split('/')[-1].split('.')[0]
        
        self.payload = {
            "url": url,
            "scrapeOptions": {
                "onlyMainContent": True,
                "waitFor": 10,
                "formats": ["html"]
            }
        }
        
        self.headers = {
            "Authorization": f"Bearer {self.FIRECRAWL_API_KEY}",
            "Content-Type": "application/json"
        }
    
    def crawl(self) -> BeautifulSoup:
        
        #POST
        response = requests.request("POST", self.FIRECRAWL_ENDPOINT, json=self.payload, headers=self.headers)
        response_json = json.loads(response.text)
        
        while True:
            if response_json['success']:
                res_url = response_json['url']
                self.logger.info(f"Submitted: {self.url_snap};")
                break
            else:
                self.logger.error(f"{self.url_snap}; {response_json['error']}")
                time.sleep(90)
        
        #GET
        while True:
            response = requests.request("GET", res_url, headers=self.headers)
            response_json = json.loads(response.text)
            if response_json['status'] == 'completed':
                self.logger.info(f"Completed: {self.url_snap};")
                break
            elif response_json['status'] == 'scraping':
                self.logger.info(f"Scraping: {self.url_snap};")
                time.sleep(10)
        soup = BeautifulSoup(response_json['data'][0]['html'], 'html.parser')
        return soup

    async def crawl_async(self, session) -> BeautifulSoup:
        
        # POST
        async with session.post(self.FIRECRAWL_ENDPOINT, json=self.payload, headers=self.headers) as response:
            response_json = await response.json()
            
            while True:
                if response_json['success']:
                    res_url = response_json['url'].replace("https:", self.FIRECRAWL_ENDPOINT.split('//')[0])
                    self.logger.info(f"Submitted: {self.url_snap}")
                    break
                else:
                    self.logger.error(f"{self.url_snap}; {response_json['error']}")
                    await asyncio.sleep(65)

        # GET
        while True:
            async with session.get(res_url, headers=self.headers) as response:
                response_json = await response.json()
                if response_json['status'] == 'completed':
                    self.logger.info(f"Completed: {self.url_snap}; {response_json['status']}")
                    break
                elif response_json['status'] == 'scraping':
                    self.logger.info(f"Scraping: {self.url_snap};")
                    await asyncio.sleep(10)
        soup = BeautifulSoup(response_json['data'][0]['html'], 'html.parser')
        return soup

@mcp.tool()
async def crawl_2_url(url_1, url_2):
    async with aiohttp.ClientSession() as session:
        tasks = [FireCrawl(url).crawl_async(session) for url in [url_1, url_2]]
        soup_list = await asyncio.gather(*tasks)
    return soup_list

@mcp.tool()
async def get_us_epidata():
    
    url_us = {
        'all_respiratory_viruses': {
            'summary': 'https://www.cdc.gov/respiratory-viruses/data/activity-levels.html',
            'trends': 'https://www.cdc.gov/respiratory-viruses/data/activity-levels.html'
        },
        'clinical_cov': {
            'trends': 'same with all_respiratory_viruses > trends > COVID-19_percent_of_tests_positive',
            'variants': 'https://covid.cdc.gov/covid-data-tracker/#variant-proportions'
        },
        'wastewater_cov': {
            'trends': 'https://www.cdc.gov/nwss/rv/COVID19-nationaltrend.html',
            'variants': 'https://www.cdc.gov/nwss/rv/COVID19-variants.html'
        }
    }

    ## all_respiratory_viruses & clinical_cov trends
    arv_soup = FireCrawl(url_us['all_respiratory_viruses']['summary']).crawl()
    arv_summary = arv_soup.find('div', class_='update-snapshot').text.strip()
    arv_trends  = []
    cc_cov_trends = []
    for row in arv_soup.find_all('div', class_='table-container')[-1].find('tbody').find_all('tr'):
        cells = row.find_all('td')
        td = {
            'date': datetime.strptime(cells[0].text.strip(), '%B %d, %Y').strftime('%Y-%m-%d'),
            'COVID-19_percent_of_tests_positive': float(cells[1].text.strip()),
            'Influenza_percent_of_tests_positive': float(cells[2].text.strip()),
            'RSV_percent_of_tests_positive': float(cells[3].text.strip())
        }
        td_cov = {
            'date': datetime.strptime(cells[0].text.strip(), '%B %d, %Y').strftime('%Y-%m-%d'),
            'COVID-19_percent_of_tests_positive': float(cells[1].text.strip())
        }
        arv_trends.append(td)
        cc_cov_trends.append(td_cov)
    time.sleep(30)
    
    ## clinical_cov variants
    cc_cov_variants_soup = FireCrawl(url_us['clinical_cov']['variants']).crawl()
    cc_cov_raw_soup = cc_cov_variants_soup.select('#circulatingVariants')[0]
    cc_cov_variants_list = cc_cov_raw_soup.find_all('div', class_ = 'tab-vizHeaderWrapper')
    cc_cov_variant_name = cc_cov_variants_list[7:24]
    cc_cov_variant_ratio = cc_cov_variants_list[41:58]
    cc_cov_variants = {
        'date': datetime.strptime(cc_cov_variants_list[-1].text, '%m/%d/%y').strftime('%Y-%m-%d'),
        'percentage': ';'.join([f"{voc.text}:{ratio.text}" for voc, ratio in zip(cc_cov_variant_name, cc_cov_variant_ratio)])
    }
    time.sleep(30)
    
    ## wastewater_cov
    ww_cov_soup_list = await crawl_2_url(url_us['wastewater_cov']['trends'], url_us['wastewater_cov']['variants'])
    ww_cov_trends = []
    for row in ww_cov_soup_list[0].find('div', class_='table-container').find('tbody').find_all('tr'):
        td = {
            'date': datetime.strptime(row.find('td').text.strip(), '%m/%d/%y').strftime('%Y-%m-%d'),
            'COVID-19_NWSS_wastewater_viral_activity_levels': float(row.find_all('td')[1].text.strip())
        }
        ww_cov_trends.append(td)

    ww_cov_variants = []
    ww_cov_variants_soup = ww_cov_soup_list[1].find('div', class_='table-container')
    ww_cov_variants_name = [i.text.split('Press')[0].strip() for i in ww_cov_variants_soup.find('thead').find_all('th')]
    ww_cov_variants_name[0] = 'Date'
    for row in ww_cov_variants_soup.find('tbody').find_all('tr'):
        cells = row.find_all('td')
        data = dict(zip(ww_cov_variants_name, [i.text.strip() for i in cells]))
        ww_cov_variants.append({
            'date': data['Date'],
            'percentage': ';'.join([f"{voc}:{partio}" for voc, partio in data.items() if voc != 'Date'])
        })
    time.sleep(30)

    epi_us = {
        'all_respiratory_viruses': {
            'summary': arv_summary,
            'trends': arv_trends
        },
        'clinical_cov': {
            'trends': cc_cov_trends,
            'variants': cc_cov_variants
        },
        'wastewater_cov': {
            'trends': ww_cov_trends,
            'variants': ww_cov_variants
        }
    }
    
    os.makedirs('history') if not os.path.exists('history') else None
    with open(f'history/data_us_{time_now}.json', 'w') as f:
        json.dump(epi_us, f, indent=4)
    
    return epi_us

if __name__ == "__main__":
    async def main():
        while True:
            try:
                us_epidata = await get_us_epidata()
                print(us_epidata)
                break
            except:
                print('Error occurred, retrying in 5 minutes...')
                time.sleep(300)
    asyncio.run(main())