import requests
import json
import boto3
import os
import re
from requests.auth import HTTPBasicAuth

# === Loading Local Environment Variables ===
from dotenv import load_dotenv 
load_dotenv()

def get_groovy_file(region, product, env):
    if region == "us" or region == "can":
        if product == "elevate":
            if env == "nonprod" or env == "sandbox":
                groovy = "env/10005_" + product + "_" + region + "_" + env + ".groovy"
            elif env == "":
                groovy = "env/10005_" + product + "_" + region + "_prod.groovy"
            elif region == "us" and (env == "cloudopstest" or env == "pretest"):
                groovy = "env/10004_" + product + "_" + region + "_" + env + ".groovy"
            elif region == "can" and env == "catest":
                groovy = "env/10004_" + product + "_ca_" + env + ".groovy"
            else:
                groovy = "Error: no appropriate groovy found. Unknown environment" + env + \
                    " in " + region + " region for Elevate. Verify URL is correct."
        else: 
            groovy = "Error: no appropriate groovy found. Unknown product " + product + ". Verify URL is correct."
    elif region == "eu" or region == "au":
        if product == "quercus":
            if env == "nonprod" or env == "sandbox":
                groovy = "env/10005_" + product + "_" + region + "_" + env + ".groovy"
            elif env == "":
                groovy = "env/10005_" + product + "_" + region + "_prod.groovy"
            elif region == "eu" and env == "internal":
                groovy = "env/10004_" + product + "_" + region + "_" + env + ".groovy"
            elif region == "au" and env == "cloudopstest":
                groovy = "env/10004_" + product + "_" + region + "_" + env + ".groovy"
            else:
                groovy = "Error: no appropriate groovy found. Unknown environment" + env + \
                    " in " + region + " region for Quercus. Verify URL is correct."
        else: 
            groovy = "Error: no appropriate groovy found. Unknown product " + product + ". Verify URL is correct."
    else: 
        groovy = "Error: no appropriate groovy found. Unknown region " + region + ". Verify URL is correct."
    return groovy

def get_build_data(description):
    # capture groups: 0. region, 1. product, 2. environment, 3. type, 4. client
    # use 10004 accounts for now
    # us pretest and cloudops test
    # make sure client name matches
    url_regex = r'https://(.*?)-(.*?)-(.*?).elluciancloud.com/(.*?)/(.*?)/'
    url_pattern = re.compile(url_regex)
    url_matches = re.findall(url_pattern, description)

    # capture groups: 0. date
    date_regex = r'(?:[0-9]{2}/){2}[0-9]{4}'
    date_pattern = re.compile(date_regex)
    date_matches = re.findall(date_pattern, description)

    # capture groups: 0. hours, 1. minutes, 2. AM or PM (all capitalization variants), 3. time zone
    # expected start date
    time_regex = r'([0-9]{1,2}):([0-9]{2})\s*?([AaPp][Mm])\s*?([a-zA-Z]{2}[tT])'
    time_pattern = re.compile(time_regex)
    time_matches = re.findall(time_pattern, description)

    build_data_list = []

    try: 
        from_region = url_matches[0][0]
        from_product = url_matches[0][1]
        from_env = url_matches[0][2]
        from_type = url_matches[0][3]
        from_client = url_matches[0][4]

        to_region = url_matches[1][0]
        to_product = url_matches[1][1]
        to_env = url_matches[1][2]
        to_type = url_matches[1][3]
        to_client = url_matches[1][4]
    except IndexError:
        return "Error: Will not build. URL not formatted correctly."

    if from_region == "us" and (from_client != to_client):
        return "Error: Will not build. Export and import must have the same client in their urls."

    try: 
        date = date_matches[0]
    except IndexError:
        return "Error: Will not build. Date not formatted correctly"

    try: 
        time_hours = time_matches[0][0]
        time_minutes = time_matches[0][1]
        am_or_pm = time_matches[0][2]
        time_zone = time_matches[0][3]
    except IndexError:
        return "Error: Will not build. Time not formatted correctly"

        export_groovy_file = get_groovy_file(from_region, from_product, from_env)
    import_groovy_file = get_groovy_file(to_region, to_product, to_env)

    if "Error" not in (export_groovy_file or import_groovy_file): 
        build_data_list.append([export_groovy_file, import_groovy_file, date, time_hours, time_minutes, am_or_pm, time_zone])
    else: 
        return ("Error: Groovy file error. Export: " + export_groovy_file + "\nImport: " + import_groovy_file) 

    return build_data_list

def lambda_handler(event, context):
    # url = 'https://elluciandev.service-now.com/api/sn_customerservice/case/CS0722732'
    # active_cases_url = 'https://elluciandev.service-now.com/api/sn_customerservice/case?sysparm_query=active=true'
    url4 = 'https://elluciandev.service-now.com/api/sn_customerservice/case?sysparm_query=short_description=Clone%20of%20test%20to%20prod'
    # Additional headers.
    headers = {'Content-Type': 'application/json'} 
    
    # convert dict to json string by json.dumps() for body data. 

    # os.environ['USER'] for Lambda, os.getenv('USER') for local server
    # USER = os.environ['USER'] # Lambda
    USER = os.getenv("USER")
    # PASSWORD = os.environ["PASSWORD"] # Lambda
    PASSWORD = os.getenv("PASSWORD")

    print("trying requests | ENV VARS =", USER, PASSWORD)
    # resp = requests.get(url4, headers=headers, auth=HTTPBasicAuth(USER, PASSWORD))
    print("requests succeeded?")
    # return -1 
    
    
    sns = boto3.client('sns')
    dynamodb = boto3.client('dynamodb')
    
    test_build_parameters = ['Clone of test to prod\u200bCS0722732', [['env/10004_elevate_us_pretest.groovy', 'env/10004_elevate_us_cloudopstest.groovy', '04/12/2020', '01', '24', 'AM', 'GMT']]]
    dynamodb.put_item(TableName='clone-schedule', Item={'caseID':{'S':test_build_parameters[0]}, 'build_info':{tuple(test_build_parameters[1:])}})
    
    return 1
    
    build_parameters_list = []
        
    # Validate response headers and body contents, e.g. status code.
    if resp.status_code == 200:
        resp_body = resp.json()
        print("finding response")
        for result, case_list in resp_body.items():
            for case in case_list:
                for key, value in case.items():
                    if key == "case":
                        print("case is : ", case)
                        build_parameters_list.append(value)
                    if key == "description":
                        # in current test, no time in description, need to add it for clarity
                        new_description = value + " 01:24 AM GMT"
                        build_parameters = get_build_data(new_description)
                        print("build parameters")
                        print(build_parameters)
                        if "Error" not in build_parameters: 
                            build_parameters_list.append(build_parameters)
                            # item_in_table = dynamodb.get_item(TableName='clone-schedule', Key={'caseID':{'S':build_parameters_list[0]}})
                            # print("item in table")
                            # print(item_in_table)
                            # if not item_in_table: 
                            dynamodb.put_item(TableName='clone-schedule', Item={'caseID':{'S':build_parameters_list[0]}, 'build_info':{tuple(build_parameters_list[1:])}})
                            # else:
                            #     return "Item in table already."
                        else: 
                            response = sns.publish(
                                TopicArn='arn:aws:sns:us-east-1:475064013001:snow-auto',    
                                Message=build_parameters,    
                            )
                            
                            return -1
    else:
        print("Unable to query SNOW")
    
    return 1
lambda_handler(None, None)