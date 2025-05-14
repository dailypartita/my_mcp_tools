import os
import json
import time
import pymongo
import asyncio
import logging
import aiohttp
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()
mcp = FastMCP("epi-crawl")
TIMEGEP_SEC = 30

class FireCrawlRateLimitExceeded(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message
    def __str__(self):
        return f"FireCrawlRateLimitExceeded: {self.message}"

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
                "formats": ["html"],
                "waitFor": 1
            }
        }
        
        self.headers = {
            "Authorization": f"Bearer {self.FIRECRAWL_API_KEY}",
            "Content-Type": "application/json"
        }
    
    def crawl(self) -> BeautifulSoup:
        
        #POST
        response = requests.request("POST", self.FIRECRAWL_ENDPOINT, json=self.payload, headers=self.headers) # type: ignore
        response_json = json.loads(response.text)
        
        while True:
            if response_json['success']:
                res_url = response_json['url']
                self.logger.info(f"Submitted: {self.url_snap};")
                break
            elif 'Rate limit exceeded' in response_json['error']:
                self.logger.info('⚠️ FireCrawl Rate limit exceeded, retrying in 60 seconds...')
                raise FireCrawlRateLimitExceeded(f"{response_json['error']}")
            else:
                self.logger.error(f"{self.url_snap}; {response_json['error']}, retrying in {TIMEGEP_SEC} seconds...")
                time.sleep(TIMEGEP_SEC)
        
        #GET
        while True:
            response = requests.request("GET", res_url, headers=self.headers)
            response_json = json.loads(response.text)
            if response_json['status'] == 'completed':
                self.logger.info(f"Completed: {self.url_snap};")
                break
            elif response_json['status'] == 'scraping':
                self.logger.info(f"Scraping: {self.url_snap};")
                time.sleep(TIMEGEP_SEC)
        soup = BeautifulSoup(response_json['data'][0]['html'], 'html.parser')
        return soup

    async def crawl_async(self, session) -> BeautifulSoup:
        
        # POST
        async with session.post(self.FIRECRAWL_ENDPOINT, json=self.payload, headers=self.headers) as response:
            response_json = await response.json()
            
            while True:
                if response_json['success']:
                    res_url = response_json['url'].replace("https:", self.FIRECRAWL_ENDPOINT.split('//')[0]) # type: ignore
                    self.logger.info(f"Submitted: {self.url_snap}")
                    break
                elif 'Rate limit exceeded' in response_json['error']:
                    raise Exception(f"{response_json['error']}")
                else:
                    self.logger.error(f"{self.url_snap}; {response_json['error']}, retrying in {TIMEGEP_SEC} seconds...")
                    time.sleep(TIMEGEP_SEC)

        # GET
        while True:
            async with session.get(res_url, headers=self.headers) as response:
                response_json = await response.json()
                if response_json['status'] == 'completed':
                    self.logger.info(f"Completed: {self.url_snap}; {response_json['status']}")
                    break
                elif response_json['status'] == 'scraping':
                    self.logger.info(f"Scraping: {self.url_snap}, retrying in {TIMEGEP_SEC} seconds...")
                    await asyncio.sleep(TIMEGEP_SEC)
        soup = BeautifulSoup(response_json['data'][0]['html'], 'html.parser')
        return soup

@mcp.tool()
async def crawl_2_url(url_1, url_2):
    async with aiohttp.ClientSession() as session:
        tasks = [FireCrawl(url).crawl_async(session) for url in [url_1, url_2]]
        soup_list = await asyncio.gather(*tasks)
    return soup_list
