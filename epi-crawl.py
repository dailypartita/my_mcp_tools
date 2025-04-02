import os
import json
import logging

from datetime import datetime
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from firecrawl import FirecrawlApp
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

mcp = FastMCP("epi-crawl")

@mcp.tool()
async def firecrawl_crawl(url):
    
    firecrawl_app = FirecrawlApp(api_key=os.getenv('FIRECRAWL_API_KEY'))
    
    fc = firecrawl_app.crawl_url(
        url,
        params={
            'limit': 100,
            'scrapeOptions': {
                'formats': ['html']
            }
        },
    poll_interval=30
    )
    
    if fc['success'] == False:
        print(f"Error: {fc['error']}")
        return None
    
    soup = BeautifulSoup(fc['data'][0]['html'], 'html.parser')
    
    return soup

@mcp.tool()
async def get_data_us():
    logger.info("[mcp_server.get_data_us] called")
    logger.info("[mcp_server.get_data_us] fetching trends data from CDC...")
    url_01 = "https://www.cdc.gov/respiratory-viruses/data/activity-levels.html"
    soup_01 = await firecrawl_crawl(url_01)
    summary_us = soup_01.find('div', class_='update-snapshot').text.strip()
    trends_us = []
    for row in soup_01.find_all('div', class_='table-container')[-1].find('tbody').find_all('tr'):
        cells = row.find_all('td')
        tmp_dic = {
            'Date': datetime.strptime(cells[0].text.strip(), '%B %d, %Y').strftime('%Y-%m-%d'),
            'COVID-19_Percent_of_Tests_Positive': float(cells[1].text.strip()),
            'Influenza_Percent_of_Tests_Positive': float(cells[2].text.strip()),
            'RSV_Percent_of_Tests_Positive': float(cells[3].text.strip())
        }
        trends_us.append(tmp_dic)
    
    logger.info("[mcp_server.get_data_us] fetching trends data from NWSS...")
    url_02 = "https://www.cdc.gov/nwss/rv/COVID19-nationaltrend.html"
    soup_02 = await firecrawl_crawl(url_02)
    for row in soup_02.find('div', class_='table-container').find('tbody').find_all('tr'):
        for i in trends_us:
            if i['Date'] == datetime.strptime(row.find('td').text.strip(), '%m/%d/%y').strftime('%Y-%m-%d'):
                i.update({'COVID-19_NWSS_Wastewater_Viral_Activity_Levels': float(row.find_all('td')[1].text.strip())})
    
    logger.info("[mcp_server.get_data_us] fetching variants data from NWSS...")
    url_03 = "https://www.cdc.gov/nwss/rv/COVID19-variants.html"
    soup_03 = await firecrawl_crawl(url_03)
    variants_soup_cov_ww = soup_03.find('div', class_='table-container')
    variants_head_cov_ww = [i.text.split('Press')[0].strip() for i in variants_soup_cov_ww.find('thead').find_all('th')]
    variants_head_cov_ww[0] = 'Date'
    variants_us_cov_ww = []
    for row in soup_03.find('div', class_='table-container').find('tbody').find_all('tr'):
        cells = row.find_all('td')
        variants_us_cov_ww.append(dict(zip(variants_head_cov_ww, [i.text.strip() for i in cells])))
    
    data_us = {
        'summary': summary_us,
        'trends': trends_us,
        'variants_cov_ww': variants_us_cov_ww
    }
    
    if not os.path.exists('history'):
        os.makedirs('history')
        
    with open(f'history/data_us_{datetime.now().strftime("%Y-%m-%d")}.json', 'w') as f:
        json.dump(data_us, f, indent=4)
    
    return data_us

AVAILABLE_TOOLS = [
    {"name": "firecrawl_crawl", "description": "This tool uses FireCrawl to scrape a given URL and returns the HTML content."},
    {"name": "get_data_us", "description": "This tools utilizes FireCrawl to fetch real-time data on respiratory viruses such as COVID-19, Influenza, and RSV from various global sources. It provides structured data in JSON formats."},
    {"name": "list_tools", "description": "This tool lists all available tools."}
]

@mcp.tool()
async def list_tools():
    logger.info("[mcp_server.list_tools] called")
    return AVAILABLE_TOOLS

if __name__ == "__main__":
    mcp.run()
