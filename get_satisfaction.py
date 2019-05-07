import argparse

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client import tools
from pprint import pprint

import json

from datetime import datetime

import calendar

import sys
import csv

import requests

## Global MONTH
MONTH = ''

SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']

## Discovery URI for APIs
ANALYTICS_DISCOVERY_URI = ('https://analyticsreporting.googleapis.com/$discovery/rest')

## Creds for APIs (should update to json at some point)
KEY_FILE_LOCATION = 'mycreds.p12'
SERVICE_ACCOUNT_EMAIL = 'id-018-analytics@ancient-sandbox-191211.iam.gserviceaccount.com'

def initialize_analytics_api():
    """Initializes an analyticsreporting and sheets service object.
    Returns:
      analytics an authorized analyticsreporting service object.
    """

    credentials = ServiceAccountCredentials.from_p12_keyfile(
      SERVICE_ACCOUNT_EMAIL, KEY_FILE_LOCATION, scopes=SCOPES)

    http = credentials.authorize(httplib2.Http())

    # Build the service object.
    analytics = build('analytics', 'v4', http=http, discoveryServiceUrl=ANALYTICS_DISCOVERY_URI)


    return analytics

def get_analytics_report(analytics, start_date, end_date):
    ## View ID for Analytics - https://ga-dev-tools.appspot.com/query-explorer/
    VIEW_ID = '157729614'
    start = start_date
    end = end_date
    # Use the Analytics Service Object to query the Analytics Reporting API V4.
    return analytics.reports().batchGet(
        body={
            'reportRequests': [
                ## This report gets total views and views for first project page
                {
                    'viewId': VIEW_ID,
                    'pageSize': 10000,
                    'dateRanges': [{'startDate': start, 'endDate': end}],
                    'dimensions': [{'name': 'ga:eventCategory'},
                                   {'name': 'ga:eventAction'},
                                   {'name': 'ga:eventLabel'},],
                    'metrics': [{'expression': 'ga:totalEvents'}]
                }]
        }
    ).execute()

def build_clean_dict(data):
    all_data = [project['dimensions'] + [project['metrics'][0]['values'][0]] for project in data['reports'][0]['data']['rows']]
    all_events = {}
    for project in all_data:
        if project[0] not in all_events:
            all_events[project[0]] = {project[2]:{project[1]:project[3]}}
        elif project[2] not in all_events[project[0]]:
            all_events[project[0]][project[2]] = {project[1]:project[3]}
        else:
            all_events[project[0]][project[2]][project[1]] = project[3]
    return all_events
        
        
            

analytics = initialize_analytics_api()
data = get_analytics_report(analytics,"2019-04-01", "2019-04-30")
events = build_clean_dict(data)  
