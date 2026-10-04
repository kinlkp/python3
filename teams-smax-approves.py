#!/usr/bin/env python
# -*- coding: utf-8 -*-


import json
import requests
import sys
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime

# Suppress the warnings that occur when verify=False
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

APPROVERS = {
    1984678: ["user1",'https://MS-power-automate-api'],
    1965496: ["user2",'https://MS-power-automate-api'],
    1938364: ["user3",'https://MS-power-automate-api'],
    426123: ["user4",'https://MS-power-automate-api'],
    1938363: ["user5",'https://MS-power-automate-api'],
    444083: ["user6",'https://MS-power-automate-api'],
    9999999: ["user7",'https://MS-power-automate-api']
}


def send_teams(smax_num, userid):
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.2",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": f"Reminder: SMAX#{smax_num} still pending your approval.",
                            "size": "small",
                            "weight": "bolder"
                        }
                    ]
                }
            }
        ]
    }
    # print(userid)
    try:
        response = requests.post(
            APPROVERS[userid][1],
            headers=headers,
            json=data
        )
    
        print(response)
    except:
        print("Error: MS API connection error.")
        exit()
        

def check_change_approval(smax_num, api_token):
    # print(api_token)
    headers = {
        "Content-Type": "application/json",
        "Cookie": f"SMAX_AUTH_TOKEN={api_token}",
        "User-Agent": "Apache-HttpClient/4.1"
    }

    try:
        response = requests.get(
            f"https://p1vsmcmpxlc003.abc.local/rest/9999999999/tasks/Change/{smax_num}/TasksExecutionPlanApprovePlan?layout=LastErrorMessage&layout=ApproverComment&layout=TaskData&layout=ActualEndTime&layout=ApprovedBy.Name&layout=DisplayLabelKey",
            headers=headers,
            verify=False
        )
    except:
        print("Error: SMAX connection error.")
        exit()
    result_dict = json.loads(response.text)
    tasks = result_dict['TaskNodes']
    for key in tasks.keys():
        if tasks[key]['AggregatedStatus']['TaskStatus'] == "InProgress":
            # Approval is stil pending
            for approver in tasks[key]['RelatedTasks']:
                # Loop over all approvers
                if approver['PhaseId'] == "Pending":
                    print(f"==={datetime.now()}===")
                    userid = int(approver['Assignee'])
                    print(APPROVERS[userid][0], approver['PhaseId'])
                    #print(APPROVERS[int(approver['Assignee'])[0]], approver['PhaseId'])
                    if send:
                        send_teams(smax_num, int(approver['Assignee']))
                        print("send")
        else:
            pass
        

def get_smax_api_token():
    data = {"Login":"xxxxxxxxxx", "Password":"yyyyyyyyyyyy"}
    try:
        response = requests.post(
            "https://p1vsmcmpxlc003.abc.local/auth/authentication-endpoint/authenticate/token?TENANTID=00000000000",
            json=data,
            headers={"Content-Type": "application/json"},
            verify=False
        )
    except:
        print("Error: SMAX connection error.")
        exit()
    api_token = response.text
    return api_token


def main():
    if len(sys.argv) < 2:
        print("Error: no SMAX number is provided.")
        sys.exit(0)
    smax_num = sys.argv.pop(1)
    if len(sys.argv) > 1:
        global send
        send = sys.argv.pop(1)
    api_token = get_smax_api_token()
    check_change_approval(smax_num, api_token)


if __name__ == '__main__':
    send = False
    main()
