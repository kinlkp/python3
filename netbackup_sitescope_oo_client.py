#!/usr/bin/python3.9
# -*- coding: utf-8 -*-

"""
The script is used to suppress the sitescope monitoring and check netbackup
"""

import argparse
import datetime
import json
import requests
import sys
import os
import urllib3

from datetime import datetime
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings


disable_warnings(InsecureRequestWarning)


desc = None


class NBUClient:

    ENC_NBU_API_KEYs = {
        "n1": b"binary-password",
        "p1": b'binary-password',
        "p2": b'binary-password',
        "n2": b'binary-password'
    }

    NBU_SERVERs = {
        "p1": "p1psmwindc003.xyz.com",
        "p2": "p2psmwindc003.xyz.com",
        "n1": "n1psmwindc003.nonxyz.com",
        "n2": "n2psmwindc003.nonxyz.com",
    }


    def __init__(self, row):
         host, _ = row.split(',')
         if not host:
             print("Error: no hostname provides.")
             sys.exit(1)
         self.hostname = host


    def get_password(self, nbu_env):
        from cryptography.hazmat.primitives.asymmetric import rsa, padding
        from cryptography.hazmat.primitives import serialization, hashes
        # Get the private from server
        with open('/root/.sitescope/priv.pem', 'rb') as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None
            )

        # Decrypt the password using private key
        decrypted = private_key.decrypt(
            NBUClient.ENC_NBU_API_KEYs[nbu_env],
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        password = decrypted.decode()
        return password
        

    def call_server(self):
        nbu_env = self.hostname[:2]     # for example, n1, n2, p1, p2
        import socket
        this_host = socket.gethostname()
        if nbu_env[0] != this_host[0]:
            # print(f'{self.hostname} is not in this nbu.')
            return
        nbu_s = NBUClient.NBU_SERVERs[nbu_env]
        headers = {
            "Authorization": self.get_password(nbu_env),
            "Accept": "application/vnd.netbackup+json;version=2.0"
        }
        params = {
            "filter": f"clientName eq '{self.hostname}' and jobType eq 'BACKUP'",
            "page[limit]": 5
        }
        response = requests.get(f"https://{nbu_s}/netbackup/admin/jobs", params=params, headers=headers, verify=False)

        output = json.loads(response.text)
        try:
            for item in output["data"]:
                #print(f'{self.hostname} {item["id"]:7s} {item["attributes"]["scheduleType"]:25s} {item["attributes"]["endTime"][0:10]:10s} {item["attributes"]["state"]}')
                return f'{self.hostname} netbackup backup {item["attributes"]["state"]} on {item["attributes"]["endTime"][0:10]:10s}'
                break
        except:
            return f'{self.hostname} no backup'

        print("=========")
        print("*********")



class SiteScopeClient():

    SITESCOPR_PASSWORD = b'binary-password'
    TIME_DELTA = 1 		 # means delta is 1 day

    BLACKOUT_LENGTH = 1      # means blackout length = 1 hr

    def __init__(self, row):
        self.row = row

    def get_password(self):
        from cryptography.hazmat.primitives.asymmetric import rsa, padding
        from cryptography.hazmat.primitives import serialization, hashes


        with open('/root/.sitescope/priv.pem', 'rb') as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None
            )
        
        decrypted = private_key.decrypt(
            SiteScopeClient.SITESCOPR_PASSWORD,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        password = decrypted.decode()
        return password


    def cal_date(self, start_suppress):
        from_datetime = datetime.strptime(start_suppress, '%Y%m%d%H%M')
        from_diff = int(from_datetime.timestamp() - datetime.now().timestamp())
        return from_diff


    def check_monitor(self, host: str, group_name: str, web_URL: str):
        find_url = f'{web_URL}/api/monitors/group/properties'
        params = {'fullPathToGroup': group_name}
        response = requests.get(find_url, params=params, verify=False,
                                auth=HTTPBasicAuth(os.environ['SITESCOPE_USER'], SiteScopeClient.SITESCOPR_PASSWORD))
        output = json.loads(response.text)
        print(f"{host} {output['status']}")


    def blackout(self):
        if self.row[0] == "#":
            global desc
            desc = self.row[1:]
            return

        blackout_duration = SiteScopeClient.BLACKOUT_LENGTH * 3300 * 1000

        mon_state = 'disable'
        host, hour_min = self.row.split(',')
        if not host:
            print("Error: no hostname provides.")
            sys.exit(1)

        import socket
        this_host = socket.gethostname()
        if this_host[0] == 'n' and host[0] == 'n':
            web_URL = 'https://n1vsmobmaw0010.nonxyz.com/SiteScope'
        elif this_host[0] == 'p' and host[0] == 'p':
            web_URL = 'https://p1vsmobmaw0010.xyz.com/SiteScope'
        else:
            return

        find_url = f'{web_URL}/api/monitors'
        set_url = f'{web_URL}/api/monitors/group/status'

        #if args.time:
        from datetime import date, datetime, timedelta
        today = datetime.now()
        tmr = today + timedelta(SiteScopeClient.TIME_DELTA)
        start_suppress = tmr.strftime("%Y%m%d") + hour_min[0:4]

        params = {
            'entity_type': '', # for both monitors and groups.
            'searchregex': 'true',
            'name': host
        }

        # Find the group name in sitescope
        response = requests.get(find_url, params=params, verify=False,
                                auth=HTTPBasicAuth('administrator', self.get_password()))
        if response.status_code != 200:
            print("Error: Auth failed.")
            sys.exit(1)
        groups_dict = json.loads(response.text)
        if not bool(groups_dict):
            print(f"{host} is NOT in sitescope.")
            return

        # Post to sitescope
        for k, group_name in enumerate(groups_dict):
            if groups_dict[group_name] == 'Group' and host in group_name:
                if mon_state == "check":
                    self.check_monitor(host, group_name, web_URL)
                    break
                # Suppress monitoring for 4 hours
                from_diff = self.cal_date(start_suppress) * 1000
                to_diff = from_diff + blackout_duration
                params = {
                    'fullPathToGroup': group_name,
                    'enable': mon_state,
                    'fromTime': str(from_diff),
                    'toTime': str(to_diff),
                    'description': f"SMAX{desc}"
                }
                response = requests.post(set_url, data=params, verify=False,
                                        auth=HTTPBasicAuth('administrator', self.get_password()))

                if host[2] == "p":
                    print(f"WARNING: You need to disable NNMI - {host}.")

                if response.status_code == 204:
                    return f"{response.status_code}  {host} blackout start from {start_suppress} for {blackout_duration/1000} secs."
                else:
                    return f"{response.status_code}  {host} blackout failed."
                break


def main():
    # Get server list from p2vsmsautl0010:/repo/sasa
    url='http://192.168.0.21:3001/sasa/servers.csv'
    res = requests.get(url, stream=True)
    with open('/tmp/servers.csv', "w") as f:
        f.write(res.text)

    import csv
    with open('/tmp/servers.csv', "r") as csv_f:
        for row in csv_f:
            if row[0] == "#":
                global desc
                desc = row[1:]
                continue
            else:
                sitescope_c =  SiteScopeClient(row)
                sitescope_output = sitescope_c.blackout()
                nbu_c = NBUClient(row)
                nbu_output = nbu_c.call_server()
            print(f"{sitescope_output} {nbu_output}")
    os.unlink('/tmp/servers.csv')


if __name__ == '__main__':
    main()