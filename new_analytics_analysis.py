## NOTE - this has an over-reliance on using list indicies.
## Lists should really be reformated into dictionaries at a later date.

import argparse

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools
from pprint import pprint

from selenium import webdriver
from bs4 import BeautifulSoup

from github import Github
import json
import yaml

from datetime import datetime
import calendar

#from dummy_meta import projects, meta_details

YEAR = input('Enter the year you are interested in ')
MONTH = input('Enter the short name of the month ')
START_DATE = datetime.strptime(MONTH + ' ' + YEAR, '%b %Y')
DAYS_IN_MONTH = calendar.monthrange(START_DATE.year, START_DATE.month)
END_DATE = datetime.strptime(str(DAYS_IN_MONTH[1]) + ' ' + MONTH + ' ' + YEAR , '%d %b %Y')


print('Processing analytics from', START_DATE.strftime('%Y-%m-%d'), 'to', END_DATE.strftime('%Y-%m-%d'))

## GOOGLE APIs being used
SCOPES = ['https://www.googleapis.com/auth/analytics.readonly', 'https://www.googleapis.com/auth/spreadsheets']

## Discovery URI for APIs
ANALYTICS_DISCOVERY_URI = ('https://analyticsreporting.googleapis.com/$discovery/rest')
SHEETS_DISCOVERY_URI = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')

## Creds for APIs (should update to json at some point)
KEY_FILE_LOCATION = 'mycreds.p12'
SERVICE_ACCOUNT_EMAIL = 'id-018-analytics@ancient-sandbox-191211.iam.gserviceaccount.com'

## GitHub integration - token is stored in form key: token in github.yml
with open('github.yml', 'r') as f:
    auth = yaml.load(f.read())
git = Github(auth['key'])
org = git.get_organization('raspberrypilearning')


def initialize_api():
    """Initializes an analyticsreporting service object.

    Returns:
      analytics an authorized analyticsreporting service object.
    """

    credentials = ServiceAccountCredentials.from_p12_keyfile(
      SERVICE_ACCOUNT_EMAIL, KEY_FILE_LOCATION, scopes=SCOPES)

    http = credentials.authorize(httplib2.Http())

    # Build the service object.
    analytics = build('analytics', 'v4', http=http, discoveryServiceUrl=ANALYTICS_DISCOVERY_URI)
    sheets = build('sheets', 'v4', http=http, discoveryServiceUrl=SHEETS_DISCOVERY_URI)

    return analytics, sheets


def get_analytics_report(analytics):
    ## View ID for Analytics - https://ga-dev-tools.appspot.com/query-explorer/
    VIEW_ID = '157729614'
    start_date = START_DATE.strftime('%Y-%m-%d')
    end_date = END_DATE.strftime('%Y-%m-%d')
    # Use the Analytics Service Object to query the Analytics Reporting API V4.
    return analytics.reports().batchGet(
        body={
            'reportRequests': [
                ## This report gets total views and views for first project page
                {
                    'viewId': VIEW_ID,
                    'pageSize': 10000,
                    'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                    'metrics': [{'expression': 'ga:pageviews'},
                                {'expression': 'ga:uniquePageviews'},
                                {'expression': 'ga:avgTimeOnPage'},],
                    'dimensions': [{'name': 'ga:pagePathLevel2'},
                                   {'name': 'ga:pagePathLevel3'},

                    ],
                    "orderBys":[{
                        "fieldName": "ga:uniquePageviews",
                        "sortOrder": "ASCENDING"}],
                    'metricFilterClauses':[{
                        'filters':[
                            {'metricName': 'ga:pageviews',
                             'operator': 'GREATER_THAN',
                             'comparisonValue': '5'}]}]

                },
                ## This report gets data on page views after first page
                {
                    'viewId': VIEW_ID,
                    'pageSize': 10000,
                    'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                    'metrics': [{'expression': 'ga:pageviews'},
                                {'expression': 'ga:uniquePageviews'},
                                {'expression': 'ga:avgTimeOnPage'},],
                    'dimensions': [{'name': 'ga:pagePathLevel2'},
                                   {'name': 'ga:pagePathLevel3'},
                                   {'name': 'ga:pagePathLevel4'},
                    ],
                    "orderBys":[{
                        "fieldName": "ga:uniquePageviews",
                        "sortOrder": "ASCENDING"}],
                                        'metricFilterClauses':[{
                        'filters':[
                            {'metricName': 'ga:pageviews',
                             'operator': 'GREATER_THAN',
                             'comparisonValue': '5'}]}]
                }]
        }
    ).execute()


def read_sheets(sheets, range_name):
    spreadsheetId = '1VdqfhNMM66rwBk7VsDoVWeLQbochGRf4S9BsQqH_9is'
    rangeName = range_name
    result = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheetId,
        range=rangeName).execute()
    values = result.get('values', [])
    return values


def write_data(sheets, values, summary):
    spreadsheetId = '1VdqfhNMM66rwBk7VsDoVWeLQbochGRf4S9BsQqH_9is'
    body = {'value_input_option': 'USER_ENTERED',
            'data': {'range' : MONTH,
                     'values' : values},
            'data': {'range' : 'Summary',
                     'values' : summary}
            }

    result = sheets.spreadsheets().values().batchUpdate(
       spreadsheetId=spreadsheetId,
       body=body).execute() 


def fetch_projects():
    '''Use firefox to iterate over projects.raspberrypi.org and return the names of all live projects'''
    ## This is an ugly hack until access to the database can be provided
    driver = webdriver.Firefox()
    base_url = "https://projects.raspberrypi.org/en/projects?page%5Bnumber%5D="
    all_cards = []
    ## Iterate over first 20 pages on site for future proofing
    for i in range(1,20): 
        driver.get("https://projects.raspberrypi.org/en/projects?page%5Bnumber%5D="+str(i))
        cards = driver.find_elements_by_class_name('c-card')
        for card in cards:
            all_cards.append(card.get_attribute('innerHTML'))
    driver.close()

    ## Get the html and look at all the image names, to find project names
    html = ' '.join(all_cards)
    soup = BeautifulSoup(html, 'html.parser')
    images = soup.find_all('img')
    projects = []
    for image in images:
        projects.append(str(image).split('/')[4])
    return projects


def get_meta(repo):
    '''use GH API to fetch curriculum details from project meta'''
    repo = org.get_repo(repo)
    file_contents = repo.get_file_contents('en/meta.yml')
    meta_text = file_contents.decoded_content.decode('utf-8')
    meta_dict = yaml.load(meta_text)
    try:
        curriculum = meta_dict['curriculum'].split()
        curriculum = [curriculum[0][:-1], curriculum[1][-2], curriculum[2][-2], curriculum[3][-2], curriculum[4][-2], curriculum[5][-1]]
    except:
        print(repo, 'is missing Curriculum data')
        curriculum = ['None Provided','0','0','0','0', '0']
    try:
        duration = meta_dict['duration']
    except KeyError:
        print(repo, 'is missing duration data')
        duration = 0
    return curriculum, duration

def collect_meta(projects):
    meta_details = {project : get_meta(project) for project in projects}
    return meta_details

                    
def assemble_data(meta_details):
    '''Assemble data for each resource, and handle past queries where resources are not in analytics'''
    resources = {}
    for resource in projects:
        try:
            resources[resource] = all_pages_dict[resource]
        except KeyError:
            print(resource, 'not found in this date range')

    ##Spreadsheet titles
    values = [['Name',
               'Viewed', 'Views as % Total',
               'Engaged','Enagaged as % Views',
               'Complete', 'Complete as % Views',
               'Final','Print',
               'Curriculum Level', 'Design', 'Programming', 'Phys-comp', 'Manufacture', 'Community',
               'duration',
               'learning_hours']]
    
    for resource in resources:
        resource_data = []
        resource_data.append(resource)
        pages = [resources[resource][str(i)][1] if str(i) in resources[resource].keys() else 0 for i in range(31)]
        ## Get value of those that clicked the tile
        viewed = pages[0]
        viewed_percent = ''
        resource_data.append(viewed)
        resource_data.append(viewed_percent)
        ## Get value of those that progressed through to step 3
        engaged = pages[3]
        engaged_percent = int(engaged)/int(viewed) * 100
        resource_data.append(engaged)
        resource_data.append(engaged_percent)
        ## Get last non-zero value of page views for those that made it to end
        completed = [view for view in pages if view !=0][-1]
        completed_percent = int(completed)/int(viewed) * 100
        resource_data.append(completed)
        resource_data.append(completed_percent)
        ## Get printed and complete
        resource_data += [resources[resource]['complete'][1] if 'complete' in resources[resource].keys() else '0']
        resource_data += [resources[resource]['print'][1] if 'print' in resources[resource].keys() else '0']
        ## Add curriculum from meta
        resource_data += meta_details[resource][0]
        ## add duration from meta
        resource_data.append(meta_details[resource][1])
        ## calc and add learning hours
        if meta_details[resource][1] == 1:
            learning_hours = 0.25 * int(completed)
        elif meta_details[resource][1] == 2:
            learning_hours = 1 * int(completed)
        elif meta_details[resource][1] == 3:
            learning_hours = 2 * int(completed)
        else:
            learning_hours = 0
        resource_data.append(learning_hours)
        values.append(resource_data)

    return values

def find_top_three(processed_data):
    projects = [project[0] for project in processed_data[1:-2]]
    views = [project[2] for project in processed_data[1:-2]]
    engaged = [project[4] for project in processed_data[1:-2]]
    complete = [project[6] for project in processed_data[1:-2]]
    top_three_views = sorted(zip(views, projects), reverse=True)[:3]
    top_three_engaged = sorted(zip(engaged, projects), reverse=True)[:3]
    top_three_complete = sorted(zip(complete, projects), reverse=True)[:3]
    return top_three_views, top_three_engaged, top_three_complete

def biggest_drop(processed_data):
    projects = [project[0] for project in processed_data[1:]]
    percent_engaged = [int(project[2])/int(project[1])*100 for project in processed_data[1:]]
    percent_complete = [int(project[3])/int(project[1])*100 for project in processed_data[1:]]
    top_three_percent_engaged = sorted(zip(percent_engaged, projects), reverse=True)[:3]
    top_three_percent_complete = sorted(zip(percent_engaged, projects), reverse=True)[:3]
    bottom_three_percent_engaged = sorted(zip(percent_engaged, projects))[:3]
    bottom_three_percent_complete = sorted(zip(percent_engaged, projects))[:3]
    return [top_three_percent_engaged,
            top_three_percent_complete,
            bottom_three_percent_engaged,
            bottom_three_percent_complete]

def calc_totals(processed_data):
    total_views = 0
    total_engaged = 0
    total_complete = 0
    final_page = 0
    printed = 0
    learning_hours = 0
    projects = 0
    for row in processed_data[1:]:
        projects += 1
        total_views += int(row[1])
        total_engaged += int(row[3])
        total_complete += int(row[5])
        final_page += int(row[7])
        printed += int(row[8])
        learning_hours += int(row[16])
                              
    totals = ['TOTALS', total_views,
              '', total_engaged,
              '', total_complete,
              '', final_page, printed,
              '','','','','','','',learning_hours]
    averages = ['AVERAGE',total_views/projects,
                '', total_engaged/projects,
                '', total_complete/projects,
                '', final_page/projects ,printed/projects,
                '','','','','','','',learning_hours/ projects]
    processed_data.append(totals)
    processed_data.append(averages)
    return processed_data, total_views

def compose_summary(processed_data):
    top_three_views, top_three_engaged, top_three_complete = find_top_three(processed_data)
    learning_hours = sum(i[-1] for i in processed_data[1:-2])
    ## engaged by level

    def summary_strand(strand, metric):
        if metric == 'engaged':
            column = 3
        elif metric == 'completed':
            column = 5
        total = 0
        views = 0
        for row in processed_data[1:-2]:
            if int(row[strand]) != 0:
                total += int(row[column])
                views += int(row[1])
        try:
            percent = total/views * 100
        except ZeroDivisionError:
            percent = 0
        return percent

    def summary_level(level, metric):
        if metric == 'engaged':
            column = 3
        elif metric == 'completed':
            column = 5
        
        total = 0
        views = 0
        for row in processed_data[1:-2]:
            if row[9] == level:
                total += int(row[column])
                views += int(row[1])
        try:
            percent = total/views * 100
        except ZeroDivisionError:
            percent = 0
        return percent
    
    engaged_dev = summary_strand(10, 'engaged')
    engaged_pro = summary_strand(11, 'engaged')
    engaged_phy = summary_strand(12, 'engaged')
    engaged_mak = summary_strand(13, 'engaged')
    engaged_com = summary_strand(14, 'engaged')
    completed_dev = summary_strand(10, 'completed')
    completed_pro = summary_strand(11, 'completed')
    completed_phy = summary_strand(12, 'completed')
    completed_mak = summary_strand(13, 'completed')
    completed_com = summary_strand(14, 'completed')

    engaged_cre = summary_level('creator', 'engaged')
    engaged_bui = summary_level('builder', 'engaged')
    engaged_dev = summary_level('developer', 'engaged')
    engaged_mak = summary_level('maker', 'engaged')
    completed_cre = summary_level('creator', 'completed')
    completed_bui = summary_level('builder', 'completed')
    completed_dev = summary_level('developer', 'completed')
    completed_mak = summary_level('maker', 'completed')

    ## reverse each tuple and flatten
    top_views = [j for i in top_three_views for j in reversed(i)]
    top_engaged = [j for i in top_three_engaged for j in reversed(i)]
    top_complete = [j for i in top_three_complete for j in reversed(i)]
    past_data = read_sheets(sheets, 'Summary')
    for row in past_data:
        if row[0] == MONTH:
            del(row[1:])
            row.append(processed_data[-2][1])
            row.append(learning_hours)
            row.extend(top_views + top_engaged + top_complete)
            row.extend([engaged_dev, engaged_pro,  engaged_phy, engaged_mak, engaged_com])
            row.extend([engaged_cre, engaged_bui, engaged_dev, engaged_mak])
            row.extend([completed_dev, completed_pro,  completed_phy, completed_mak, completed_com])
            row.extend([completed_cre, completed_bui, completed_dev, completed_mak])
    return past_data
    

##Fetch live projects
projects = fetch_projects()

#### Get the API service objects
analytics, sheets = initialize_api()
response = get_analytics_report(analytics)

## Root project pages showing hits to first page and hits to all sub pages
root_pages = response['reports'][0]['data']['rows']

## Initialise the dictionary of projects
all_pages_dict = {page['dimensions'][1][1:-1] : {'0': page['metrics'][0]['values']} for page in root_pages if page['dimensions'][1][-1] == '/'}

## add in the first page that has a trailing `/` - can remove this later if fixed in Analytics
for page in root_pages:
    if page['dimensions'][1][-1] != '/':
        page_name = page['dimensions'][1][1:]
        try:
            all_pages_dict[page_name]['1'] = page['metrics'][0]['values']
        except KeyError:
            pass
                                                         
        
## Drill down to project pages
pages = response['reports'][1]['data']['rows']

## Add additional pages
for page in pages:
    try:
        page_name = page['dimensions'][1][1:-1]
        page_number = page['dimensions'][2][1:]
        all_pages_dict[page_name][page_number] = page['metrics'][0]['values']
    except KeyError:
        pass

meta_details = collect_meta(projects)
processed_data = assemble_data(meta_details)
processed_data, total= calc_totals(processed_data)
for i in processed_data[1:-2]:
    total_percent = int(i[1]) / int(total) * 100
    i[2] = total_percent

summary = compose_summary(processed_data)


write_data(sheets, processed_data, summary)
