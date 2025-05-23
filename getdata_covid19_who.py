import re
import os
import time
import json
from loguru import logger
from utils import FireCrawl
from pymongo import MongoClient
from datetime import datetime, timezone

def get_who_covid19():
    TIME_SLEEP = 60
    TIME_RUN = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H-%M-%S')
    TIME_NOW = datetime.now(timezone.utc)
    WHO_URL_LIST = [
        'https://data.who.int/dashboards/covid19/summary',
        'https://data.who.int/dashboards/covid19/circulation',
        'https://data.who.int/dashboards/covid19/cases',
        'https://data.who.int/dashboards/covid19/deaths',
        'https://data.who.int/dashboards/covid19/hospitalizations',
        'https://data.who.int/dashboards/covid19/vaccines',
        'https://data.who.int/dashboards/covid19/variants'
    ]
    
    # 0. summary
    # 0.1 实时：新冠疫情概况
    who_summary_soup = FireCrawl(WHO_URL_LIST[0]).crawl()
    time.sleep(TIME_SLEEP)
    p1_soup = who_summary_soup.find_all('div', attrs={'id': 'PageContent_C493_Col00', 'class': 'sf_colsIn col-md-12'})[0]
    p2_soup = who_summary_soup.find_all('div', attrs={'id': 'PageContent_C629_Col00', 'class': 'sf_colsIn col-md-9'})[0]
    WHO_realtime_summary = [
        {
            'date': str(TIME_NOW.replace(tzinfo=timezone.utc)),
            'summary_circulation': p1_soup.find_all('p')[0].text,
            'summary_cases': p1_soup.find_all('p')[10].text,
            'summary_variant': p1_soup.find_all('div', class_ = 'sfContentBlock sf-Long-text')[9].text,
            'summary_severity': p2_soup.find_all('p')[0].text,
            'summary_death': p2_soup.find_all('p')[10].text
        }
    ]
    

    # 1. circulation
    # 1.1 实时：上周各国新冠阳性率
    who_cirulation_soup = FireCrawl(WHO_URL_LIST[1]).crawl()
    time.sleep(TIME_SLEEP)
    WHO_realtime_7d_countries_positivity_rate = [
        {
            'date': str(datetime.now(timezone.utc)),
            'country': i['aria-label'].split(':')[0].strip(),
            'covid19_positivity_rate': float(i['aria-label'].split(':')[1].strip()[:-1])
        }
        for i in who_cirulation_soup
        .find_all(attrs={"data-testid": "dataDotViz-choroplethMap-borders"})[0]
        .find_all(attrs={"role": "button"})
    ]

    # 1.2 历史：每周全球新冠阳性率变化
    tmp_history_rawlist = [
        [re.sub(r'[:,]', '', j.strip()) for j in i.text.split('\n')]
        for i in who_cirulation_soup.find_all(attrs={"id": "PageContent_C481_Col00"})[0].find_all(attrs={"role": "listitem"})
    ]
    x = int(len(tmp_history_rawlist) / 3)
    WHO_weekly_positivity_rate_world_history = [
        {
            'date': str(datetime.strptime(tmp_history_rawlist[0][0], '%d %b %Y').replace(tzinfo=timezone.utc)),
            'Number_of_specimens_tested_for_SARS-CoV-2': int(tmp_history_rawlist[0][1]),
            'Number_of_specimens_tested_Positive_for_SARS-CoV-2': int(tmp_history_rawlist[x][1]),
            'Percentage_of_samples_testing_positive_for_SARS-CoV-2': float(tmp_history_rawlist[2*x][1])
        }
        for n_specimens, n_positive, n_percentage in zip(tmp_history_rawlist[:x], tmp_history_rawlist[x:2*x], tmp_history_rawlist[2*x:])
    ]

    # 1.3 实时：上月新冠突变株占比情况
    WHO_realtime_28d_variants_prevalence = [
        {
            'date': str(datetime.now(timezone.utc)),
            'variant': v_line.find_all('td', class_ = 'inline-border value-column svelte-1hj6lq3')[0].text,
            'prevalence': float(v_line.find_all('td', class_ = 'value-column align-end svelte-1hj6lq3')[0].text[:-1]),
            'change': v_line.find_all('td', class_ = 'value-column align-end svelte-1hj6lq3')[1].text
        }
        for v_line in who_cirulation_soup
        .find_all('table', class_ = 'data-table svelte-1hj6lq3')[0]
        .find_all('tr', class_ = 'svelte-1hj6lq3')[1:]
    ]

    # 1.4  实时：上月提交GISAID新冠突变株序列条数
    WHO_realtime_28d_GISAID_variants_submitted = [
        {
            'date': str(datetime.now(timezone.utc)),
            'variant': v_line.find_all('td', class_ = 'inline-border value-column svelte-szsgy')[0].text,
            'countries': int(v_line.find_all('td', class_ = 'inline-border value-column align-end svelte-szsgy')[0].text),
            'sequences_submitted_to_GISAID': int(v_line.find_all('td', class_ = 'value-column align-end svelte-szsgy')[0].text.replace(',', ''))
        }
        for v_line in who_cirulation_soup
        .find_all('table', class_ = 'data-table svelte-szsgy')[0]
        .find_all('tr', class_ = 'svelte-szsgy')[1:]
    ]

    # 1.5 历史：每周主要新冠突变株占比变化
    WHO_history_weekly_variants_prevalence = []
    for x in range(len(['VOIs', 'VUMs'])):
        flag = False
        for i in who_cirulation_soup.find_all('svg', class_ = 'touch-action-pan-y svelte-4havvh dataDotViz-chart')[x].find_all('text', role = 'cell'):
            if i['data-testid'] == 'dataDotViz-line-summary':
                variant = i.text.split('In')[1].split(',')[0].strip()
                time_start = i.text.split('week')[1].split('to')[0].strip()
                time_end = i.text.split('week')[2].split('.')[0].strip()
            try:
                if i['data-test-time-dim'] == time_start:
                    flag = True
                if i['data-test-time-dim'] == time_end:
                    prevalence, flag = float(i.text), False
                    WHO_history_weekly_variants_prevalence.append({
                        'date': str(datetime.strptime(i['data-test-time-dim'], '%Y-%m-%d').replace(tzinfo=timezone.utc)),
                        'variant': variant,
                        'prevalence': prevalence
                    })
                if flag:
                    prevalence = float(i.text)
                    WHO_history_weekly_variants_prevalence.append({
                        'date': str(datetime.strptime(i['data-test-time-dim'], '%Y-%m-%d').replace(tzinfo=timezone.utc)),
                        'variant': variant,
                        'prevalence': prevalence
                    })
                continue
            except:
                pass
    
    # 2. cases
    # 2.1 实时：上月全球总的新冠病例数量
    who_cases_soup = FireCrawl(WHO_URL_LIST[2]).crawl()
    time.sleep(TIME_SLEEP)
    WHO_realtime_28d_world_reported_cases = [
        {
            'date': str(datetime.strptime(who_cases_soup.find_all('span', class_ = 'end-date svelte-aejddw')[0].text, 'World, 28 days to %d %B %Y').replace(tzinfo=timezone.utc)),
            'Number_of_cases_reported_to_WHO_in_the_past_28_days': int(who_cases_soup.find_all('strong', class_ = 'value svelte-aejddw')[0].text.replace(',', '')),
            'Number_of_cases_reported_to_WHO_in_the_past_28_days_change': who_cases_soup.find_all('strong', class_ = 'change-value svelte-aejddw')[0].text[1:].replace(',', '')
        }
    ]

    # 2.2 历史：全球总的新冠病例数量
    WHO_history_weekly_world_reported_cases = [
        {
            'date': str(datetime.strptime(i.text.split(':')[0], '%d %b %Y').replace(tzinfo=timezone.utc)),
            'Number_of_cases_reported_to_WHO': int(i.text.split(':')[1].replace(',', ''))
        }
        for i in who_cases_soup.find_all('div', attrs={'id': 'PageContent_C014_Col01', 'class': 'sf_colsIn col-md-6'})[0].find_all('text', attrs={'role': 'listitem'})
    ]

    # 2.3 历史：全球各洲上报的病例数量
    WHO_history_weekly_region_reported_cases = [
            {
                'date': str(datetime.strptime(j.text.split(':')[0], '%d %b %Y').replace(tzinfo=timezone.utc)),
                'WHO_region': i.find_all('h3', attrs={'data-testid': 'dataDotViz-covid19-groups-spatialDimName'})[0].text,
                'Number_of_cases_reported_to_WHO': int(j.text.split(':')[1].replace(',', ''))
            }
            for i in who_cases_soup.find_all('div', attrs={'id': 'PageContent_C033_Col00', 'class': 'sf_colsIn col-md-12'})[0].find_all('section', class_ = 'covid19-groups-row svelte-sfsmwu')
            for j in i.find_all('text', role = 'listitem')
    ]

    # 2.4 历史：全球各国上报的病例数量
    WHO_history_weekly_countries_reported_cases = [
            {
                'date': str(datetime.strptime(j['data-test-time-dim'], '%Y-%m-%d').replace(tzinfo=timezone.utc)),
                'country': i.text.split('Reported')[0].strip(),
                'Number_of_cases_reported_to_WHO': j.text
            }
        for i in who_cases_soup.find_all('div', attrs={'id': 'PageContent_C040_Col00', 'class': 'sf_colsIn col-md-12'})[0].find_all('div', attrs={'data-testid': 'dataDotViz-small-multiple'})
        for j in i.find_all('text', role = 'cell')[1:]
    ]

    # 3. deaths
    # 3.1 实时：上月全球总的新冠死亡数量
    who_deaths_soup = FireCrawl(WHO_URL_LIST[3]).crawl()
    time.sleep(TIME_SLEEP)
    WHO_realtime_28d_world_reported_deaths = [
        {
            'date': str(datetime.strptime(who_deaths_soup.find_all('span', class_ = 'end-date svelte-aejddw')[0].text, 'World, 28 days to %d %B %Y').replace(tzinfo=timezone.utc)),
            'Number_of_deaths_reported_to_WHO_in_the_past_28_days': int(who_deaths_soup.find_all('strong', class_ = 'value svelte-aejddw')[0].text.replace(',', '')),
            'Number_of_deaths_reported_to_WHO_in_the_past_28_days_change': who_deaths_soup.find_all('strong', class_ = 'change-value svelte-aejddw')[0].text[1:].replace(',', '')
        }
    ]

    # 3.2 历史：全球总的新冠死亡案例数量
    WHO_history_weekly_world_reported_deaths = [
        {
            'date': str(datetime.strptime(i.text.split(':')[0], '%d %b %Y').replace(tzinfo=timezone.utc)),
            'Number_of_deaths_reported_to_WHO': int(i.text.split(':')[1].replace(',', ''))
        }
        for i in who_deaths_soup.find_all('div', attrs={'id': 'PageContent_C014_Col01', 'class': 'sf_colsIn col-md-6'})[0].find_all('text', attrs={'role': 'listitem'})
    ]

    # 3.3 历史：全球各洲上报的死亡案例数量
    WHO_history_weekly_region_reported_deaths = [
        {
            'date': str(datetime.strptime(j.text.split(':')[0], '%d %b %Y').replace(tzinfo=timezone.utc)),
            'WHO_region': i.find_all('h3', attrs={'data-testid': 'dataDotViz-covid19-groups-spatialDimName'})[0].text,
            'Number_of_deaths_reported_to_WHO': j.text.split(':')[1].replace(',', '').strip()
        }
        for i in who_deaths_soup.find_all('div', attrs={'id': 'PageContent_C033_Col00', 'class': 'sf_colsIn col-md-12'})[0].find_all('section', class_ = 'covid19-groups-row svelte-sfsmwu')
        for j in i.find_all('text', role = 'listitem')
    ]

    # 3.4 历史：全球各国上报的死亡案例数量
    WHO_history_weekly_countries_reported_deaths = [
        {
            'date': str(datetime.strptime(j['data-test-time-dim'], '%Y-%m-%d').replace(tzinfo=timezone.utc)),
            'country': i.text.split('Reported')[0].strip(),
            'Number_of_deaths_reported_to_WHO': j.text
        }
        for i in who_deaths_soup.find_all('div', attrs={'id': 'PageContent_C040_Col00', 'class': 'sf_colsIn col-md-12'})[0].find_all('div', attrs={'data-testid': 'dataDotViz-small-multiple'})
        for j in i.find_all('text', role = 'cell')[1:]
    ]

    # 3.5 历史：死亡案例年龄占比
    WHO_history_weekly_age_distribution_reported_deaths = [
        {
            'date': str(datetime.strptime(j['data-test-time-dim'], '%Y-%m-%d').replace(tzinfo=timezone.utc)),
            'age_group': i.find_all('h3', class_ = 'headline svelte-1g6zpbj')[0].text,
            'Percentage_of_deaths_reported_to_WHO': float(j.text[:-1])
        }
        for i in who_deaths_soup.find_all('div', attrs={'class': 'dataDotViz-jsonChartConfig dataDotViz-theme dataDotViz-reset dataDotViz-dynamic dataDotViz-chartConfig dataDotViz-ChartRenderer dataDotViz-chartMode-l'})[0].find_all('div', attrs = {'data-testid': 'dataDotViz-small-multiple'})
        for j in i.find_all('text', role = 'cell')[1:]
    ]

    # 4. hospitalizations
    # 4.1 实时：上月全球总的新冠住院数量
    who_hospitalizations_soup = FireCrawl(WHO_URL_LIST[4]).crawl()
    time.sleep(TIME_SLEEP)
    WHO_realtime_28d_world_reported_hospitalizations = [
        {
            'date': str(datetime.strptime(who_hospitalizations_soup.find_all('span', class_ = 'end-date svelte-aejddw')[0].text, 'World, 28 days to %d %B %Y').replace(tzinfo=timezone.utc)),
            'Number_of_hospitalizations_reported_to_WHO_in_the_past_28_days': int(who_hospitalizations_soup.find_all('strong', class_ = 'value svelte-aejddw')[0].text.replace(',', '')),
            'Number_of_hospitalizations_reported_to_WHO_in_the_past_28_days_change': who_hospitalizations_soup.find_all('strong', class_ = 'change-value svelte-aejddw')[0].text[1:].replace(',', '')
        }
    ]

    # 4.2 历史：全球每月新冠住院人数
    WHO_history_monthly_world_reported_hospitalizations = [
        {
            'date': str(datetime.strptime(i.text.split(':')[0], '%d %b %Y').replace(tzinfo=timezone.utc)),
            'Number_of_hospitalizations_reported_to_WHO': int(i.text.split(':')[1].replace(',', ''))
        }
        for i in who_hospitalizations_soup.find_all('div', attrs={'id': 'PageContent_C014_Col01', 'class': 'sf_colsIn col-md-6'})[0].find_all('text', attrs={'role': 'listitem'})
    ]

    # 4.3 实时：上月全球总的由新冠导致的ICU住院数量
    WHO_realtime_28d_world_reported_ICU = [
        {
            'date': str(datetime.strptime(who_hospitalizations_soup.find_all('span', class_ = 'end-date svelte-aejddw')[0].text, 'World, 28 days to %d %B %Y').replace(tzinfo=timezone.utc)),
            'Number_of_ICU_hospitalizations_reported_to_WHO_in_the_past_28_days': int(who_hospitalizations_soup.find_all('strong', class_ = 'value svelte-aejddw')[1].text.replace(',', '')),
            'Number_of_ICU_hospitalizations_reported_to_WHO_in_the_past_28_days_change': who_hospitalizations_soup.find_all('strong', class_ = 'change-value svelte-aejddw')[1].text[1:].replace(',', '')
        }
    ]

    # 4.4 历史：全球每月新冠ICU住院人数
    WHO_history_monthly_world_reported_ICU = [
        {
            'date': str(datetime.strptime(i.text.split(':')[0], '%d %b %Y').replace(tzinfo=timezone.utc)),
            'Number_of_ICU_hospitalizations_reported_to_WHO': int(i.text.split(':')[1].replace(',', ''))
        }
        for i in who_hospitalizations_soup.find_all('div', attrs={'id': 'PageContent_C181_Col01', 'class': 'sf_colsIn col-md-6', 'data-sf-element': 'Column 2'})[0].find_all('text', attrs={'role': 'listitem'})
    ]

    # 4.5 历史：全球每月新冠重症人数
    WHO_history_monthly_world_reported_severity = [
        {
            'date': str(datetime.strptime(i.text.split(':')[0], '%d %b %Y').replace(tzinfo=timezone.utc)),
            'Number_of_ICU_admissions_per_1000_hospitalizations_reported_to_WHO': int(i.text.split(':')[1].replace(',', '')),
            'Number_of_death_per_1000_hospitalizations_reported_to_WHO': int(j.text.split(':')[1].replace(',', ''))
        }
        for i, j in zip(
            who_hospitalizations_soup.find_all('div', attrs={'id': 'PageContent_C190_Col00', 'class': 'sf_colsIn col-md-6', 'data-sf-element': 'Column 1'})[0].find_all('text', attrs={'role': 'listitem'}),
            who_hospitalizations_soup.find_all('div', attrs={'id': 'PageContent_C190_Col01', 'class': 'sf_colsIn col-md-6', 'data-sf-element': 'Column 2'})[0].find_all('text', attrs={'role': 'listitem'})
        )
    ]

    # 5. vaccines
    # 5.1 实时：全球接种新冠疫苗总剂数、第一针和加强针覆盖率
    who_vaccines_soup = FireCrawl(WHO_URL_LIST[5]).crawl()
    time.sleep(TIME_SLEEP)
    sub_soup = who_vaccines_soup.find_all('div', attrs={'id': 'PageContent_C001_Col00', 'class': 'sf_colsIn container--contrast'})[0]
    WHO_realtime_total_world_vaccines = [
        {
            'date': str(TIME_NOW.replace(tzinfo=timezone.utc)),
            'Total_COVID-19_vaccine_doses_administered': sub_soup.find_all('strong', class_ = 'data-value svelte-phjb1n')[0].text,
            'Date_of_first_COVID-19_vaccine_product_introduction': sub_soup.find_all('strong', class_ = 'data-value svelte-phjb1n')[1].text,
            'Percentage_of_total_population_vaccinated_with_a_complete_primary_series_of_a_COVID-19_vaccine': float(sub_soup.find_all('span', class_ = 'value svelte-1jx75w7')[0].text[:-1]),
            'Percentage_of_total_population_vaccinated_with_at_least_one_booster_dose_of_a_COVID-19_vaccine': float(sub_soup.find_all('span', class_ = 'value svelte-1jx75w7')[1].text[:-1])
        }
    ]

    # 5.2 实时：各国新冠疫苗覆盖率
    WHO_realtime_vaccine_coverage = [
        {
            'date': str(datetime.now(timezone.utc)),
            'country': i['aria-label'].split(':')[0].strip(),
            'Percentage_of_total_population_vaccinated_with_at_least_one_dose_of_a_COVID-19_vaccine': float(i['aria-label'].split(':')[1].strip()[:-1]) if i['aria-label'].split(':')[1].strip() != 'No data' else None
        }
        for i in who_vaccines_soup
        .find_all('div', attrs={'id': 'PageContent_C013_Col00', 'class': 'sf_colsIn container'})[0]
        .find_all('use', attrs={"role": "button"})
    ]

    # 6. variants
    # 6.1 历史：VOI & VUM 相关信息
    who_variants_soup = FireCrawl(WHO_URL_LIST[6]).crawl()
    time.sleep(TIME_SLEEP)
    voi_information = [
        {
            'pango_lineage': i.find_all('th')[0].text.split('Pango lineage')[1].split('Excludes')[0].strip(),
            'nextstrain_clade': i.find_all('p')[0].text.split('Nextstrain clade')[1].strip(),
            'genetic_features': i.find_all('p')[1].text.split('Genetic features')[1].strip(),
            'earliest_documented_samples': i.find_all('p')[2].text.split('Earliest documented samples')[1].strip(),
            'date_of_designation': i.find_all('p')[3].text.split('Date of designation')[1].strip(),
            'risk_assessments_reports': [j['href'] for j in i.find_all('a')]
        }
        for i in who_variants_soup.find_all('div', attrs={'id': 'PageContent_C085_Col00', 'class': 'table-container table--contrast sf_colsIn', 'data-sf-element': 'Table'})
    ]
    vum_information = [
        {
            'pango_lineage': i.find_all('th')[0].text.split('Pango lineage')[1].split('Excludes')[0].strip(),
            'nextstrain_clade': i.find_all('p')[0].text.split('Nextstrain clade')[1].strip(),
            'genetic_features': i.find_all('p')[1].text.split('Genetic features')[1].strip(),
            'earliest_documented_samples': i.find_all('p')[2].text.split('Earliest documented samples')[1].strip(),
            'date_of_designation': i.find_all('p')[3].text.split('Date of designation')[1].strip(),
            'risk_assessments_reports': [j['href'] for j in i.find_all('a')]
        }
        for i in who_variants_soup.find_all('div', attrs={'id': 'PageContent_C095_Col00', 'class': 'table-container table--contrast sf_colsIn', 'data-sf-element': 'Table'})[0].find_all('tr')
    ]
    WHO_variants_information = voi_information + vum_information

    result_data = {
        'WHO_realtime_summary': WHO_realtime_summary,
        'WHO_realtime_7d_countries_positivity_rate': WHO_realtime_7d_countries_positivity_rate,
        'WHO_weekly_positivity_rate_world_history': WHO_weekly_positivity_rate_world_history,
        'WHO_realtime_28d_variants_prevalence': WHO_realtime_28d_variants_prevalence,
        'WHO_realtime_28d_GISAID_variants_submitted': WHO_realtime_28d_GISAID_variants_submitted,
        'WHO_history_weekly_variants_prevalence': WHO_history_weekly_variants_prevalence,
        'WHO_realtime_28d_world_reported_cases': WHO_realtime_28d_world_reported_cases,
        'WHO_history_weekly_world_reported_cases': WHO_history_weekly_world_reported_cases,
        'WHO_history_weekly_region_reported_cases': WHO_history_weekly_region_reported_cases,
        'WHO_history_weekly_countries_reported_cases': WHO_history_weekly_countries_reported_cases,
        'WHO_realtime_28d_world_reported_deaths': WHO_realtime_28d_world_reported_deaths,
        'WHO_history_weekly_world_reported_deaths': WHO_history_weekly_world_reported_deaths,
        'WHO_history_weekly_region_reported_deaths': WHO_history_weekly_region_reported_deaths,
        'WHO_history_weekly_countries_reported_deaths': WHO_history_weekly_countries_reported_deaths,
        'WHO_history_weekly_age_distribution_reported_deaths': WHO_history_weekly_age_distribution_reported_deaths,
        'WHO_realtime_28d_world_reported_hospitalizations': WHO_realtime_28d_world_reported_hospitalizations,
        'WHO_history_monthly_world_reported_hospitalizations': WHO_history_monthly_world_reported_hospitalizations,
        'WHO_realtime_28d_world_reported_ICU': WHO_realtime_28d_world_reported_ICU,
        'WHO_history_monthly_world_reported_ICU': WHO_history_monthly_world_reported_ICU,
        'WHO_history_monthly_world_reported_severity': WHO_history_monthly_world_reported_severity,
        'WHO_realtime_total_world_vaccines': WHO_realtime_total_world_vaccines,
        'WHO_realtime_vaccine_coverage': WHO_realtime_vaccine_coverage,
        'WHO_variants_information': WHO_variants_information
    }

    return result_data

def save_to_mongodb(data, time_run):
    """Save data to MongoDB with time series collections"""
    client = MongoClient('mongodb://localhost:27017')
    
    # Create database if not exists
    db = client['covid19_WHO']
    
    # Create time series collections for data with dates
    time_series_collections = [
        'WHO_realtime_summary',
        'WHO_realtime_7d_countries_positivity_rate',
        'WHO_weekly_positivity_rate_world_history',
        'WHO_realtime_28d_variants_prevalence',
        'WHO_realtime_28d_GISAID_variants_submitted',
        'WHO_history_weekly_variants_prevalence',
        'WHO_realtime_28d_world_reported_cases',
        'WHO_history_weekly_world_reported_cases',
        'WHO_history_weekly_region_reported_cases',
        'WHO_history_weekly_countries_reported_cases',
        'WHO_realtime_28d_world_reported_deaths',
        'WHO_history_weekly_world_reported_deaths',
        'WHO_history_weekly_region_reported_deaths',
        'WHO_history_weekly_countries_reported_deaths',
        'WHO_history_weekly_age_distribution_reported_deaths',
        'WHO_realtime_28d_world_reported_hospitalizations',
        'WHO_history_monthly_world_reported_hospitalizations',
        'WHO_realtime_28d_world_reported_ICU',
        'WHO_history_monthly_world_reported_ICU',
        'WHO_history_monthly_world_reported_severity',
        'WHO_realtime_total_world_vaccines',
        'WHO_realtime_vaccine_coverage'
    ]
    
    # Convert string dates to datetime objects for MongoDB time series
    for collection_name, collection_data in data.items():
        if not collection_data:
            continue
            
        if isinstance(collection_data, list):
            for item in collection_data:
                if 'date' in item and isinstance(item['date'], str):
                    try:
                        # Try to parse date string to datetime
                        item['date'] = datetime.fromisoformat(item['date'].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        # If parsing fails, use current time
                        item['date'] = datetime.now(timezone.utc)
    
    # Save each data set to its own collection
    for collection_name, collection_data in data.items():
        if not collection_data:
            continue
            
        # Create time series collection if needed
        if collection_name in time_series_collections:
            # Check if collection exists
            if collection_name not in db.list_collection_names():
                # Create time series collection
                db.create_collection(
                    collection_name,
                    timeseries={
                        'timeField': 'date',
                        'metaField': 'country' if 'countries' in collection_name else None,
                        'granularity': 'hours'
                    }
                )
        
        # Insert data
        collection = db[collection_name]
        if isinstance(collection_data, list) and collection_data:
            collection.insert_many(collection_data)
        elif isinstance(collection_data, dict):
            collection.insert_one(collection_data)
    
    # Also save a historical record of the entire dataset
    history_collection = db['history']
    history_collection.insert_one({
        'time_run': time_run,
        'data': data
    })
    
    return True

def save_to_json(data, time_run):
    """Save data as JSON file"""
    # Create history directory if it doesn't exist
    if not os.path.exists('history'):
        os.makedirs('history')
    
    # Create filename
    filename = f"history/covid19_WHO_{time_run}.json"
    
    # Save data as JSON
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    return filename

if __name__ == '__main__':
    # try:
    # Get WHO COVID-19 data
    time_run = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H-%M-%S')
    who_data = get_who_covid19()
    
    # Save to JSON file
    json_file = save_to_json(who_data, time_run)
    print(f"Data saved to JSON file: {json_file}")
    
    # Save to MongoDB
    mongodb_saved = save_to_mongodb(who_data, time_run)
    print(f"Data saved to MongoDB: {mongodb_saved}")
    # except Exception as e:
    #     print(f"Error: {e}")