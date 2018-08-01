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

from github import Github
from github.GithubException import UnknownObjectException
import json
import yaml

from datetime import datetime

import calendar

MONTH = ''

## GOOGLE APIs being used
SCOPES = ['https://www.googleapis.com/auth/analytics.readonly', 'https://www.googleapis.com/auth/spreadsheets']

## Discovery URI for APIs
ANALYTICS_DISCOVERY_URI = ('https://analyticsreporting.googleapis.com/$discovery/rest')
SHEETS_DISCOVERY_URI = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')

## Creds for APIs (should update to json at some point)
KEY_FILE_LOCATION = 'mycreds.p12'
SERVICE_ACCOUNT_EMAIL = 'id-018-analytics@ancient-sandbox-191211.iam.gserviceaccount.com'


## Load GitHub credentials - token is stored in form key: token in github.yml
with open('github.yml', 'r') as f:
    auth = yaml.load(f.read())
git = Github(auth['key'])
org = git.get_organization('raspberrypilearning')


def fetch_date_range():
    global MONTH
    '''Fetch year and month for analytics and get the YYYY,MM,DD date range
    Return a start and end date for the fiven month'''
    year = input('Enter the year you are interested in ')
    month = input('Enter the short name of the month ')
    MONTH = month
    start_date = datetime.strptime(month + ' ' + year, '%b %Y')
    days_in_month = calendar.monthrange(start_date.year, start_date.month)
    end_date = datetime.strptime(str(days_in_month[1]) + ' ' + month + ' ' + year , '%d %b %Y')
    print('Processing analytics from', start_date.strftime('%Y-%m-%d'), 'to', end_date.strftime('%Y-%m-%d'))
    return start_date, end_date


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

def initialize_sheets_api():
    """Initializes an analyticsreporting and sheets service object.
    Returns:
      analytics an authorized analyticsreporting service object.
    """

    credentials = ServiceAccountCredentials.from_p12_keyfile(
      SERVICE_ACCOUNT_EMAIL, KEY_FILE_LOCATION, scopes=SCOPES)

    http = credentials.authorize(httplib2.Http())

    # Build the service object.
    sheets = build('sheets', 'v4', http=http, discoveryServiceUrl=SHEETS_DISCOVERY_URI)

    return sheets


def get_analytics_report(analytics, start_date, end_date):
    ## View ID for Analytics - https://ga-dev-tools.appspot.com/query-explorer/
    VIEW_ID = '157729614'
    start = start_date.strftime('%Y-%m-%d')
    end = end_date.strftime('%Y-%m-%d')
    # Use the Analytics Service Object to query the Analytics Reporting API V4.
    return analytics.reports().batchGet(
        body={
            'reportRequests': [
                ## This report gets total views and views for first project page
                {
                    'viewId': VIEW_ID,
                    'pageSize': 10000,
                    'dateRanges': [{'startDate': start, 'endDate': end}],
                    'metrics': [{'expression': 'ga:pageviews'},
                                {'expression': 'ga:uniquePageviews'},
                                {'expression': 'ga:avgTimeOnPage'},],
                    'dimensions': [{'name': 'ga:pagePathLevel2'},
                                   {'name': 'ga:pagePathLevel3'},

                    ],
                    "orderBys":[{
                        "fieldName": "ga:uniquePageviews",
                        "sortOrder": "DESCENDING"}],
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
                    'dateRanges': [{'startDate': start, 'endDate': end}],
                    'metrics': [{'expression': 'ga:pageviews'},
                                {'expression': 'ga:uniquePageviews'},
                                {'expression': 'ga:avgTimeOnPage'},],
                    'dimensions': [{'name': 'ga:pagePathLevel2'},
                                   {'name': 'ga:pagePathLevel3'},
                                   {'name': 'ga:pagePathLevel4'},
                    ],
                    "orderBys":[{
                        "fieldName": "ga:uniquePageviews",
                        "sortOrder": "DESCENDING"}],
                                        'metricFilterClauses':[{
                        'filters':[
                            {'metricName': 'ga:pageviews',
                             'operator': 'GREATER_THAN',
                             'comparisonValue': '5'}]}]
                }]
        }
    ).execute()


def read_sheets(sheets, range_name):
    '''Read a given Google sheet and name and return the values'''
    spreadsheetId = '1VdqfhNMM66rwBk7VsDoVWeLQbochGRf4S9BsQqH_9is'
    rangeName = range_name
    result = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheetId,
        range=rangeName).execute()
    values = result.get('values', [])
    return values


def write_data(sheets, values, end):
    if type(end) == str:
        range_name = end
    else:
        range_name = calendar.month_name[end.month][0:3]
    '''Write to a specific range and tab, with values represented by a 2D list'''
    spreadsheetId = '1VdqfhNMM66rwBk7VsDoVWeLQbochGRf4S9BsQqH_9is'
    body = {'value_input_option': 'USER_ENTERED',
            'data': {'range' : range_name,
                     'values' : values}
            }

    result = sheets.spreadsheets().values().batchUpdate(
       spreadsheetId=spreadsheetId,
       body=body).execute() 


def fetch_repo_list():
    '''Fetch and return a list of all repos in the organisation'''
    repos = org.get_repos()
    return [repo.name for repo in repos] ##temp reduce number of repos


def get_meta(repo):
    '''For a given repo
    return the data in the meta.yml in the form a dictionary'''
    print(repo)
    repo = org.get_repo(repo)
    if not repo.archived:
        try:
            file_contents = repo.get_file_contents('en/meta.yml')
            meta_text = file_contents.decoded_content.decode('utf-8')
            meta_dict = yaml.load(meta_text)
        except UnknownObjectException:
            meta_dict = None
    else:
        meta_dict = None
    return meta_dict


def process_meta():
    '''Return a dictionary with repos as keys and meta dictionary as value'''
    repos = fetch_repo_list()
    projects = {}
    for repo in repos:
        meta_dict = get_meta(repo)
        print(meta_dict)
        if meta_dict:
            projects[repo] = meta_dict
    return projects
    
def process_analytics(start_date, end_date):
    analytics = initialize_analytics_api()
    analytics_data = get_analytics_report(analytics, start_date, end_date)
    parent_pages = analytics_data['reports'][0]['data']['rows']
    child_pages = analytics_data['reports'][1]['data']['rows']

    ## Initialise the dictionary of projects
    # all_pages_dict = {}
    # for page in parent_pages:
    #     if page['dimensions'][1][-1] != '/' and page['dimensions'][1][-1] not in all_pages_dict:
    #         all_pages_dict[page['dimensions'][1][1:]] = {'1': page['metrics'][0]['values']}
                           
    all_pages_dict = {page['dimensions'][1][1:] : {'1': page['metrics'][0]['values']} for page in parent_pages if page['dimensions'][1][-1] != '/'}

    for page in child_pages:
        ## Remove slashes from name and number
        page_name = page['dimensions'][1][1:-1]
        ## Get the page number if it's not 1, so not to overwrite parent
        if page['dimensions'][2][1:] != '1':
            page_number = page['dimensions'][2][1:]
        page_metrics = page['metrics'][0]['values']
        ## Add child pages data to dictionary
        if page_name in all_pages_dict.keys():
            all_pages_dict[page_name][page_number] = page_metrics
    
    return all_pages_dict


def compile_meta_analytics(projects_analytics):
    print('fetching analytics')

    print('fetching meta data')
    projects_meta = process_meta()
    print('processing')
    ## Remove projects with no site_areas tag
    learning_projects = {project:meta for project, meta in projects_meta.items() if 'site_areas' in meta}
    ## Remove projects where site areas is not "projects"
    projects = {project:meta for project, meta in learning_projects.items() if meta['site_areas'] == 'projects'}
    ## Add the analytics data for each project
    for project in projects.keys():
        if project in projects_analytics.keys():
            projects[project]['analytics'] = projects_analytics[project]
    return projects


def refine_curriculum(raw_curriculum):
    curriculum = {}
    raw_curriculum = raw_curriculum.replace(" ", "").split(",")
    ## Get the oveerall level
    curriculum['level'] = raw_curriculum.pop(0)
    ## Get the strand levels
    for strands in raw_curriculum:
        strand = strands.split("-")
        curriculum[strand[0]] = strand[-1]
    return curriculum

        
    
def create_data_list(projects):


    ## Titles
    values = [['Name',
               'Viewed', 'Views as % Total',
               'Engaged','Enagaged as % Views',
               'Complete', 'Complete as % Views',
               'Final','Print',
               'Curriculum Level', 'Design', 'Programming', 'Phys-comp', 'Manufacture', 'Community',
               'duration',
               'learning_hours']]

    ## Find total project views
    total_views = 0
    for project in projects.keys():
        try:
            total_views += int(projects[project]['analytics']['1'][1])
        except KeyError:
            print('No analytics available for', project, 'for this month')

    ## Assemble values for spreadsheet
    
    for project in projects.keys():
        try:
            viewed_first_page = int(projects[project]['analytics']['1'][1])
            try:
                views_as_percentage = viewed_first_page / total_views * 100
            except ZeroDivisionError:
                views_as_percentage = 0
            engaged = int(projects[project]['analytics']['3'][1])
            try:
                engaged_as_percentage = engaged / viewed_first_page * 100
            except ZeroDivisionError:
                engaged_as_percentage = 0
            ## Find last page
            pages = []
            for page in projects[project]['analytics'].keys():
                try:
                    pages.append(int(page))
                except ValueError:
                    pass
            final = str(max(pages))

            complete = int(projects[project]['analytics'][final][1])
            try:
                complete_as_percentage = complete / viewed_first_page * 100
            except ZeroDivisionError:
                complete_as_percentage = 0
            try:
                final = int(projects[project]['analytics']['complete'][1])
            except KeyError:
                final = 0

            try:
                printed = int(projects[project]['analytics']['print'][1])
            except KeyError:
                printed = 0

            curriculum = refine_curriculum(projects[project]['curriculum'])
            level = int(curriculum['level'])
            design =int(curriculum['design'])
            programming = int(curriculum['programming'])
            phys = int(curriculum['phys'])
            manufacture = int(curriculum['manufacture'])
            community =  int(curriculum['community'])

            duration = int(projects[project]['duration'])
            if duration == 1:
                learning_hours = 0.25 * complete
            elif duration == 2:
                learning_hours = 1 * complete
            elif duration == 3:
                learning_hours = 2 * complete
            else:
                learning_hours = 0

            values.append([project,
                           viewed_first_page,
                           views_as_percentage,
                           engaged,
                           engaged_as_percentage,
                           complete,
                           complete_as_percentage,
                           final,
                           printed,
                           level,
                           design,
                           programming,
                           phys,
                           manufacture,
                           community,
                           duration,
                           learning_hours])
        except KeyError:
            print(project)
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
    return processed_data, total_views, totals

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
    
    engaged_des = summary_strand(10, 'engaged')
    engaged_pro = summary_strand(11, 'engaged')
    engaged_phy = summary_strand(12, 'engaged')
    engaged_mak = summary_strand(13, 'engaged')
    engaged_com = summary_strand(14, 'engaged')
    completed_des = summary_strand(10, 'completed')
    completed_pro = summary_strand(11, 'completed')
    completed_phy = summary_strand(12, 'completed')
    completed_mak = summary_strand(13, 'completed')
    completed_com = summary_strand(14, 'completed')

    engaged_cre = summary_level(1, 'engaged')
    engaged_bui = summary_level(2, 'engaged')
    engaged_dev = summary_level(3, 'engaged')
    engaged_mak = summary_level(4, 'engaged')
    completed_cre = summary_level(1, 'completed')
    completed_bui = summary_level(2, 'completed')
    completed_dev = summary_level(3, 'completed')
    completed_mak = summary_level(4, 'completed')
    total_creator = sum([1 for row in processed_data[1:-2] if row[9] == 1])
    total_builder = sum([1 for row in processed_data[1:-2] if row[9] == 2])
    total_developer = sum([1 for row in processed_data[1:-2] if row[9] == 3])
    total_maker = sum([1 for row in processed_data[1:-2] if row[9] == 4])
    design = sum([1 for row in processed_data[1:-2] if int(row[10]) > 0])
    programming = sum([1 for row in processed_data[1:-2] if int(row[11]) > 0])
    physical = sum([1 for row in processed_data[1:-2] if int(row[12]) > 0])
    manufacture = sum([1 for row in processed_data[1:-2] if int(row[13]) > 0])
    community = sum([1 for row in processed_data[1:-2] if int(row[14]) > 0])
    ## reverse each tuple and flatten
    top_views = [j for i in top_three_views for j in reversed(i)]
    top_engaged = [j for i in top_three_engaged for j in reversed(i)]
    top_complete = [j for i in top_three_complete for j in reversed(i)]
    past_data = read_sheets(sheets, 'Summary')
    for row in past_data:
        if row[0] == MONTH:
            del(row[1:])
            row.append(processed_data[-2][1])
            row.append(processed_data[-2][3])
            row.append(processed_data[-2][5])
            row.append(learning_hours)
            row.extend(top_views + top_engaged + top_complete)
            row.extend([engaged_des, engaged_pro,  engaged_phy, engaged_mak, engaged_com])
            row.extend([engaged_cre, engaged_bui, engaged_dev, engaged_mak])
            row.extend([completed_des, completed_pro,  completed_phy, completed_mak, completed_com])
            row.extend([completed_cre, completed_bui, completed_dev, completed_mak])
            row.extend([design, programming, physical, manufacture, community])
            row.extend([total_creator, total_builder, total_developer, total_maker])

    return past_data

start, end = fetch_date_range()
projects_analytics = process_analytics(start, end)
projects = compile_meta_analytics(projects_analytics)
processed_data = create_data_list(projects)
sheets = initialize_sheets_api()
write_data(sheets, processed_data, end)





# ##Fetch live projects
# projects = fetch_projects()

# #### Get the API service objects
# analytics, sheets = initialize_api()
# response = get_analytics_report(analytics)

# ## Root project pages showing hits to first page and hits to all sub pages
# root_pages = response['reports'][0]['data']['rows']

# ## Initialise the dictionary of projects
# all_pages_dict = {page['dimensions'][1][1:-1] : {'0': page['metrics'][0]['values']} for page in root_pages if page['dimensions'][1][-1] == '/'}

# ## add in the first page that has a trailing `/` - can remove this later if fixed in Analytics
# for page in root_pages:
#     if page['dimensions'][1][-1] != '/':
#         page_name = page['dimensions'][1][1:]
#         try:
#             all_pages_dict[page_name]['1'] = page['metrics'][0]['values']
#         except KeyError:
#             pass
                                                         
        
# ## Drill down to project pages
# pages = response['reports'][1]['data']['rows']

# ## Add additional pages
# for page in pages:
#     try:
#         page_name = page['dimensions'][1][1:-1]
#         page_number = page['dimensions'][2][1:]
#         all_pages_dict[page_name][page_number] = page['metrics'][0]['values']
#     except KeyError:
#         pass

# meta_details = collect_meta(projects)
# processed_data = assemble_data(meta_details)
processed_data, total_views, totals= calc_totals(processed_data)
for i in processed_data[1:-2]:
    total_percent = int(i[1]) / int(total_views) * 100
    i[2] = total_percent

summary = compose_summary(processed_data)


write_data(sheets, summary, 'Summary')

