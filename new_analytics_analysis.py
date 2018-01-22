"""Hello Analytics Reporting API V4."""
"""When you come back to this - the url is https://developers.google.com/analytics/devguides/reporting/core/v4/"""

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

YEAR = input('Enter the year you are interested in ')
MONTH = input('Enter the short name of the month ')
START_DATE = datetime.strptime(MONTH + ' ' + YEAR, '%b %Y')
DAYS_IN_MONTH = calendar.monthrange(START_DATE.year, START_DATE.month)
END_DATE = datetime.strptime(str(DAYS_IN_MONTH[1]) + ' ' + MONTH + ' ' + YEAR , '%d %b %Y')


print('Processing analytics from', START_DATE.strftime('%Y-%m-%d'), 'to', END_DATE.strftime('%Y-%m-%d'))

## APIs being used
SCOPES = ['https://www.googleapis.com/auth/analytics.readonly', 'https://www.googleapis.com/auth/spreadsheets']

## Discovery URI for APIs
ANALYTICS_DISCOVERY_URI = ('https://analyticsreporting.googleapis.com/$discovery/rest')
SHEETS_DISCOVERY_URI = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')

## Creds for APIs (should update to json at some point)
KEY_FILE_LOCATION = 'mycreds.p12'
SERVICE_ACCOUNT_EMAIL = 'id-018-analytics@ancient-sandbox-191211.iam.gserviceaccount.com'

## GitHub integration
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
                        "fieldName": "ga:pagePathLevel3",
                        "sortOrder": "ASCENDING"}]
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
                        "fieldName": "ga:pagePathLevel3",
                        "sortOrder": "ASCENDING"}]
                }]
        }
    ).execute()


def read_sheets(sheets):
    spreadsheetId = '1VdqfhNMM66rwBk7VsDoVWeLQbochGRf4S9BsQqH_9is'
    rangeName = 'Sheet1'
    result = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheetId,
        range=rangeName).execute()
    values = result.get('values', [])
    return values

def write_data(sheets, values):
    spreadsheetId = '1VdqfhNMM66rwBk7VsDoVWeLQbochGRf4S9BsQqH_9is'
    rangeName = sheet
    body = {'value_input_option': 'RAW',
            'data': {'range' : MONTH,
                     'values' : values}
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
        curriculum = [curriculum[0], curriculum[1][-2], curriculum[2][-2], curriculum[3][-2], curriculum[4][-2], curriculum[5][-1]]
    except:
        print(repo, 'is missing Curriculum data')
        curriculum = ['None Provided','0','0','0','0', '0']
    try:
        duration = meta_dict['duration']
    except KeyError:
        print(repo, 'is missing duration data')
        duration = 0
    return curriculum, duration

def assemble_data():
    '''Assemble data for each resource, and handle past queries where resources are not in analytics'''
    resources = {}
    for resource in projects:
        try:
            resources[resource] = all_pages_dict[resource]
        except KeyError:
            print(resource, 'not found in this date range')

    ##Spreadsheet titles
    values = [['Name',
               0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,
               'complete','print',
               'Curriculum Level', 'design', 'programming', 'phys-comp', 'manufacture', 'community',
               'duration']]
    
    for resource in resources:
        name = [resource]
        pages = [resources[resource][str(i)][1] if str(i) in resources[resource].keys() else '0' for i in range(31)]
        complete = [resources[resource]['complete'][1] if 'complete' in resources[resource].keys() else '0']
        printed = [resources[resource]['print'][1] if 'print' in resources[resource].keys() else '0']
        curriculum, duration = get_meta(resource)
        
        values.append(name + pages + complete + printed + curriculum + [duration])


    return values

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

write_data(sheets, assemble_data())
