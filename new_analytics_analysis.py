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

## APIs being used
SCOPES = ['https://www.googleapis.com/auth/analytics.readonly', 'https://www.googleapis.com/auth/spreadsheets']

## Discovery URI for APIs
ANALYTICS_DISCOVERY_URI = ('https://analyticsreporting.googleapis.com/$discovery/rest')
SHEETS_DISCOVERY_URI = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')

## Creds for APIs (should update to json at some point)
KEY_FILE_LOCATION = 'mycreds.p12'
SERVICE_ACCOUNT_EMAIL = 'id-018-analytics@ancient-sandbox-191211.iam.gserviceaccount.com'

#START_DATE = input('Provide start date in YYYY-MM-DD format ')
#END_DATE = input('Provide end date in YYYY-MM-DD format ')

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

  ## Date range for analytics reports
  START_DATE = '2018-01-01'
  END_DATE = '2018-01-12'
  # Use the Analytics Service Object to query the Analytics Reporting API V4.
  return analytics.reports().batchGet(
      body={
        'reportRequests': [
          ## This report gets total views and views for first project page
          {
          'viewId': VIEW_ID,
          'pageSize': 10000,
          'dateRanges': [{'startDate': START_DATE, 'endDate': END_DATE}],
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
          'dateRanges': [{'startDate': START_DATE, 'endDate': END_DATE}],
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
  rangeName = 'Sheet1'
  body = {'values':values}
  result = sheets.spreadsheets().values().update(
    spreadsheetId=spreadsheetId,
    range=rangeName,
    valueInputOption='RAW',
    body=body).execute()

def fetch_projects():
    '''USe firefox to iterate over projects.raspberrypi.org and return the names of all live projects'''
    driver = webdriver.Firefox()
    base_url = "https://projects.raspberrypi.org/en/projects?page%5Bnumber%5D="
    all_cards = []
    for i in range(1,10):
        driver.get("https://projects.raspberrypi.org/en/projects?page%5Bnumber%5D="+str(i))
        cards = driver.find_elements_by_class_name('c-card')
        for card in cards:
            all_cards.append(card.get_attribute('innerHTML'))
    driver.close()

    html = ' '.join(all_cards)
    soup = BeautifulSoup(html, 'html.parser')
    images = soup.find_all('img')
    projects = []
    for image in images:
        projects.append(str(image).split('/')[4])
    return projects
  
##Fetch live projects
projects = fetch_projects()

#### Get the API service objects
analytics, sheets = initialize_api()
response = get_analytics_report(analytics)

## Root project pages showing hits to first page and hits to all sub pages
root_pages = response['reports'][0]['data']['rows']
## Initialise the dictionary of projects
all_pages_dict = {page['dimensions'][1][1:-1] : {'0': page['metrics'][0]['values']} for page in root_pages if page['dimensions'][1][-1] == '/'}
## add in the first page
for page in root_pages:
  if page['dimensions'][1][-1] != '/':
    page_name = page['dimensions'][1][1:]
    print(page_name)
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

## Filter out onnly RPI resources
resources = {resource : all_pages_dict[resource] for resource in projects}

values = [
  ['Name',0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,'complete','print'],
  ]
for resource in resources:
  values.append([resource] + [resources[resource][str(i)][1] if str(i) in resources[resource].keys() else '0' for i in range(31)] + [resources[resource]['complete'][1] if 'complete' in resources[resource].keys() else '0'] + [resources[resource]['print'][1] if 'print' in resources[resource].keys() else '0'])

write_data(sheets, values)
