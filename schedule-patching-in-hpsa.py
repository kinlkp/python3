#!/opt/opsware/bin/python3

"""
The script is using the HPSA Opsware Python SDK to schedule the patching jobs
"""

import asyncio
import argparse
import os
import random
import re
import sys
import time

from collections import deque, defaultdict
from pytwist import twistserver
from pytwist.com.opsware.search import Filter
from pytwist.com.opsware.device import DeviceGroupVO
from pytwist.com.opsware.server import ServerRef
from pytwist.com.opsware.common import UniqueNameException, NotFoundException
from pytwist.com.opsware.job import JobNotification, JobSchedule
from pytwist.com.opsware.script import ServerScriptJobArgs
from datetime import date, datetime, timedelta

sys.path.append("/root/.SA/lib")
from schedule import auth


ROOT = "Public/SMAX"
NEW_TIME_DELTA = None
DEFAULT_TIME_DELTA = 1          # means delta is +1 day
LNX_SCRIPT_NAME = "yum-update-reboot"
WIN_SCRIPT_NAME = "windows-reboot-by-python"
HOSTS_RESTRICTIONS = {
    #APP_CODE:restricted time
    "redi":5
}
PATTERN = "^#\d+[a-z]?@\d+-\d+-\d+"

os.environ['TZ'] = 'Asia/Hong_Kong'
time.tzset()

SAPASSWORD = b''

class NNMISingleton:
    def __init__(self):
        self.hosts = []
        self.start_time = None

    def add_host(self, hostname, start_time):
        if hostname[2] == "p":
            self.hosts.append(hostname)
            self.start_time = start_time
        

def read_servers_csv2():
    # Download the servers.csv from p2vsmsautl0010
    download_command='https_proxy="" curl -k https://192.168.0.21:3001/sasa/servers.csv -o /tmp/servers.csv 2>/dev/null'
    os.system(download_command)
    smax = {'num':None, 'start_dates':{}}
    count = 0
    with open("/tmp/servers.csv", "r") as f:
        for line in f:
            line = line.strip()
            if not len(line) > 0:
                # empty line
                continue

            if count == 0 and not re.match(PATTERN, line):
                # ignore all comments # besides the first
                print("Error: format problem in /tmp/servers.csv")
                print("#smax-number@2025-10-14")
                print("host1,0000-0200")
                sys.exit(1)

            count += 1
            if line[0] == "#" and "@" not in line:
                continue
            elif line[0] == "#" and "@" in line:
                temp = []
                line = line.replace('#', '')
                line = line.replace(' ', '')
                smax_num, start_date = line.strip().split('@')
                if not smax['num']:
                    smax['num'] = smax_num
                    smax['start_dates'][start_date] = []
                else:
                    smax['start_dates'][start_date] = []
            else:
                smax['start_dates'][start_date].append(line)
    return smax


class SMAXFolder:
    def __init__(self, id, ts, start_date):
        self.id = id
        self.startDate = start_date
        self.timeSlotDeviceGroups = None
        self.deviceGroupService = ts.device.DeviceGroupService
        self.serverService = ts.server.ServerService
        self.searchService = ts.search.SearchService
        self.rootDeviceGroupRef = None
        self.hosts = None
        self.jobNotification = JobNotification()
        self.jobSchedule = JobSchedule()
        self.serverScriptJobArgs = ServerScriptJobArgs()
        self.serverScriptService = ts.script.ServerScriptService
        self.linuxScriptRef = self.searchService.findObjRefs(f'ServerScriptVO.name = {LNX_SCRIPT_NAME}', 'server_script')[0]
        self.winScriptRef = self.searchService.findObjRefs(f'ServerScriptVO.name = {WIN_SCRIPT_NAME}', 'server_script')[0]
        self.blackoutSitescopeRef = self.searchService.findObjRefs(f'ServerScriptVO.name = "blackout-sitescope-monitoring"', 'server_script')[0]
        self.winInstallKBRef = self.searchService.findObjRefs(f'ServerScriptVO.name =  "schedule-win-install-software"', 'server_script')[0]
        self.core1 =  self.searchService.findObjRefs('ServerVO.name = "PCORE1"', 'device')
        self.winGPupdateRef = self.searchService.findObjRefs('ServerScriptVO.name = "windows-gpupdate-after-patching"', 'server_script')[0]
        # self.checkSMAXPhase =  self.searchService.findObjRefs('ServerScriptVO.name = "check-smax-approval"', 'server_script')[0]
        self.LinuxCheckScript =  self.searchService.findObjRefs('ServerScriptVO.name = "3_healthcheck-after-yum-update"', 'server_script')[0]
        self.WinCheckScript =  self.searchService.findObjRefs('ServerScriptVO.name = "check-after-win-patching"', 'server_script')[0]
        self.notifyScriptRef = self.searchService.findObjRefs('ServerScriptVO.name = "check-hosts-up-notification-to-osc"', 'server_script')[0]
        self.timeHostsResult = None

    def getDeviceGroupPath(self, path):
        try:
            self.rootDeviceGroupRef = self.deviceGroupService.getDeviceGroupByPath(path.split('/'))
        except NotFoundException as e:
            return False
        return True
        
    def createFolder(self, folderName):
        vo = DeviceGroupVO()
        vo.parent = self.rootDeviceGroupRef
        vo.shortName = folderName
        vo.description = f"SMAX on {self.startDate}"
        try:
            self.deviceGroupService.create(vo)
        except UniqueNameException as e:
            # print("Device group name must be unique.")
            pass
            # sys.exit(0)
            

class TimeSlotFolder(SMAXFolder):
    def __init__(self, id, ts, start_date):
        super().__init__(id, ts, start_date)
        self.minitimeslot = 99
        self.numberOfHosts = {}
        self.userTag = f"smax {self.id}"

    async def createFolder2(self, folderName):
        vo = DeviceGroupVO()
        vo.parent = self.rootDeviceGroupRef
        vo.shortName = folderName
        vo.description = f"SMAX on {self.startDate}"
        try:
            self.deviceGroupService.create(vo)
        except UniqueNameException as e:
            # print("Device group name must be unique.")
            pass
            # sys.exit(0)
        
    async def createTimeSlotFolders(self, hosts):
        pattern = re.compile(r'\-.*$')
        tasks = []
        self.hosts = hosts
        for h in hosts:
            h_arr = h.split(',')
            start_time = h_arr[1].replace(" ","")
            start_time = pattern.sub('', start_time).strip()
            task = asyncio.create_task(self.createFolder2(start_time))
            tasks.append(task)
            self.minitimeslot = int(start_time[:2]) if int(start_time[:2]) < self.minitimeslot else self.minitimeslot
        await asyncio.gather(*tasks)
            
    async def __attachHostToDeviceGroup(self, hostname, start_time):
        # print(foundServers)
        f = Filter()
        f.expression = f'ServerVO.hostName *=* "{hostname}"'
        foundServers = self.serverService.findServerRefs(f)
        if not foundServers:
            print(f"Error:{foundServers} not found.")
            return
        self.getDeviceGroupPath(f"{ROOT}/{self.id}/{start_time}")
        self.deviceGroupService.addDevices(self.rootDeviceGroupRef, foundServers)
        if self.numberOfHosts.get(start_time):
            self.numberOfHosts[start_time] += 1
        else:
            self.numberOfHosts[start_time] = 1
        
    async def addHostsToDGs(self):
        pattern = re.compile(r'\-.*$')
        tasks = []
        result = {}
        for h in self.hosts:
            h_arr = h.split(',')
            hostname = h_arr[0]
            start_time = h_arr[1].replace(" ","")
            start_time = pattern.sub('', start_time).strip()
            if not result.get(start_time):
                result[start_time] = []
                result[start_time].append(hostname)
            else:
                result[start_time].append(hostname)
            task = asyncio.create_task(self.__attachHostToDeviceGroup(hostname, start_time))
            tasks.append(task)
        await asyncio.gather(*tasks)
        self.timeHostsResult = result
        
    def __calculateRebootTime(self, child_dg_name):
        time_folder_name = child_dg_name.shortName[0:2].strip()
        exec_time_min = int(child_dg_name.shortName[2:4].strip())
        exec_time_hr = int(time_folder_name)
        exec_time = exec_time_hr * 3600 + exec_time_min * 60
        start_date = datetime.strptime(self.startDate, '%Y-%m-%d')
        tmr_0000 = start_date.timestamp()
        reboot_time = int(tmr_0000) + int(exec_time) + 120
        return reboot_time
    
    async def __attachScripts(self, linux_hosts, win_hosts, reboot_time, child_dg_name):
        dg_name = child_dg_name.shortName
        # self.jobSchedule.startDate = reboot_time
        args = self.serverScriptJobArgs
        args.timeOut = 45 * 60 # seconds
        if linux_hosts:
            args.targets = linux_hosts
            self.jobSchedule.startDate = reboot_time
            self.serverScriptService.startServerScript(self.linuxScriptRef, args, self.userTag, self.jobNotification, self.jobSchedule)
            #self.jobSchedule.startDate = reboot_time + 3600
            #self.serverScriptService.startServerScript(self.LinuxCheckScript, args, self.userTag, self.jobNotification, self.jobSchedule)
        if win_hosts:
            args.targets = win_hosts
            self.jobSchedule.startDate = reboot_time
            self.serverScriptService.startServerScript(self.winScriptRef, args, self.userTag, self.jobNotification, self.jobSchedule)
            self.jobSchedule.startDate = reboot_time + 2700
            self.serverScriptService.startServerScript(self.winGPupdateRef, args, self.userTag, self.jobNotification, self.jobSchedule)
            #self.jobSchedule.startDate = reboot_time + 3600
            #self.serverScriptService.startServerScript(self.WinCheckScript, args, self.userTag, self.jobNotification, self.jobSchedule)
            args.targets = self.core1
            args.parameters = f"Public/SMAX/{self.id}/{dg_name}"
            self.jobSchedule.startDate = reboot_time - 21600
            self.serverScriptService.startServerScript(self.winInstallKBRef, args, self.userTag, self.jobNotification, self.jobSchedule)
  

    async def getServersAttachScripts(self, timeslotDG):
        linux_hosts = []
        win_hosts = []
        child_dg_name = self.deviceGroupService.getDeviceGroupVO(timeslotDG)
        reboot_time = self.__calculateRebootTime(child_dg_name)
        devices = self.deviceGroupService.getDevices(timeslotDG)
        if not devices:
            # No device in time folder
            return
        for devRef in devices:
            vo = self.serverService.getServerVO(devRef)
            if "Linux" in vo.osVersion:
                linux_hosts.append(devRef)
            if "NT" in vo.osVersion:
                win_hosts.append(devRef)
        await self.__attachScripts(linux_hosts, win_hosts, reboot_time, child_dg_name)
        # tasks.append(task)
        self.__printHostsSummary(child_dg_name, devices)

    async def getDevAttachScripts(self):
        tasks = []  
        self.getDeviceGroupPath(f"Public/SMAX/{self.id}")
        children = self.deviceGroupService.getChildren(self.rootDeviceGroupRef)
        tasks = [asyncio.create_task(self.getServersAttachScripts(childdg)) for childdg in children]
        await asyncio.gather(*tasks)
        # self._attachCheckSMAX(reboot_time)

    def blackoutMonitoring(self):
        args = self.serverScriptJobArgs
        self.getDeviceGroupPath(f"Public/Sitescope")
        args.targets = self.deviceGroupService.getDevices(self.rootDeviceGroupRef)
        args.timeOut = 60 * 60
        args.parameters = ""
        self.jobSchedule.startDate = int(time.time()) + 120
        self.serverScriptService.startServerScript(self.blackoutSitescopeRef, args, self.userTag, self.jobNotification, self.jobSchedule)
    
    def __printHostsSummary(self, child_dg_name, devices):
        print(f"Summary: timeslot {child_dg_name.shortName} added {len(devices)} hosts")


class Notification:
    hosts_before_send = []

    def __init__(self, timeslotsobj, start_date):
        self.timeslotsobj = timeslotsobj
        # print(self.timeslotsobj.timeHostsResult)
        datetime_obj = datetime.strptime(start_date, "%Y-%m-%d")
        self.todayUnixTime = int(datetime_obj.timestamp())
        self.scriptRef = self.timeslotsobj.searchService.findObjRefs('ServerScriptVO.name = "check-hosts-up-notification-to-osc"', 'server_script')[0]
        self.catb_max_time = 0
        self.catb_min_time = 9999
        # self.batch = 0
        # self.catb_set = set()
 
    def set_scehdule(self):
        catb_hosts_b1 = []
        catb_hosts_b2 = []
        catb_hosts_b3 = []
        catb_hosts_b4 = []
        catb_hosts_b5 = []
        catb_hosts_b6 = []
        catb_hosts_b7 = []
        # Cat A hosts
        pattern = re.compile(r'va2|vdb|vsmstagw')   
        jobSchedule = JobSchedule()
        args = ServerScriptJobArgs()
        args.targets = self.timeslotsobj.searchService.findObjRefs('ServerVO.name = "PCORE1"', 'device')
        userTag = f"smax {self.timeslotsobj.id}"
        count = 0
        for start_time, hosts in self.timeslotsobj.timeHostsResult.items():
            count += 1
            if pattern.search(' '.join(hosts)):
                args.parameters = f"--production --smax {self.timeslotsobj.id} --timeslot {start_time} --hosts {' '.join(hosts)}"
                jobSchedule.startDate = self.todayUnixTime + ( int(start_time[0:2]) * 3600 ) + 3900 + ( random.randint(0,9) * 60 )
                self.timeslotsobj.serverScriptService.startServerScript(self.scriptRef, args, userTag, self.timeslotsobj.jobNotification, jobSchedule)
            else:
                # Not Cat A hosts
                time_int = int(start_time)
                if time_int > 700 and time_int <= 1100:
                    # Batch < 1pm
                    catb_hosts_b1 += self.timeslotsobj.timeHostsResult[start_time]
                    # print(time, self.timeslotsobj.timeHostsResult)
                elif time_int > 1100 and time_int <= 1400:
                    # Batch  < 2pm
                    catb_hosts_b2 += self.timeslotsobj.timeHostsResult[start_time]
                elif time_int > 1400 and time_int <= 1700:
                    # Batch < 9pm
                    catb_hosts_b3 += self.timeslotsobj.timeHostsResult[start_time]
                elif time_int > 1700 and time_int <= 2000:
                    # Batch < 12am
                    catb_hosts_b4 += self.timeslotsobj.timeHostsResult[start_time]
                elif time_int > 2000 and time_int <= 2245:
                    # Batch < 12am
                    catb_hosts_b5 += self.timeslotsobj.timeHostsResult[start_time]
                elif time_int > 2245 and time_int <= 2359:
                    # Batch < 12am
                    catb_hosts_b6 += self.timeslotsobj.timeHostsResult[start_time]
                else:
                    catb_hosts_b7 += self.timeslotsobj.timeHostsResult[start_time]

        def add_jobs(*batch):
            send_times = ('1130', '1420', '1720', '2120', '2300', '2402', '2430')
            for hosts, time_str in zip(batch, send_times):
                if hosts:
                    args.parameters = f"--production --smax {self.timeslotsobj.id} --timeslot 0000 --hosts {' '.join(hosts)}"
                    jobSchedule.startDate = self.todayUnixTime + ( int(time_str[0:2]) * 3600 + int(time_str[2:4]) * 60 ) + ( random.randint(0,5) * 60 )
                    self.timeslotsobj.serverScriptService.startServerScript(self.scriptRef, args, userTag, self.timeslotsobj.jobNotification, jobSchedule)
                    print(f"INFO: {time_str} Hosts: {hosts}")
                else:
                    pass
                    # print(f"INFO: {time_str} Hosts: {hosts}")

        add_jobs(catb_hosts_b1, catb_hosts_b2, catb_hosts_b3, catb_hosts_b4, catb_hosts_b5, catb_hosts_b6)
        # print(self.catb_hosts_1330, self.catb_hosts_1730, self.catb_hosts_2130, self.catb_hosts_2359, self.catb_hosts_0100)

                    
def main(smax):
    parser = argparse.ArgumentParser()
    parser.add_argument('-np', '--nopatching', action='store_true', default=False)
    args = parser.parse_args()
    smax_num = smax['num']
    smax_num_tmp = smax_num

    smax_suffix = 97
    ts = auth(SAPASSWORD)
    # Loop the data structure from .csv
    for start_date, hosts in smax['start_dates'].items():
        # Create the device group for SMAX
        # root = "Public/SMAX"
        # ts = auth(SAPASSWORD)
        print(start_date, "=================================")
        smax_num = smax_num_tmp + chr(smax_suffix)
        smaxpatching = TimeSlotFolder(smax_num, ts, start_date)
        if not smaxpatching.getDeviceGroupPath(ROOT):
            print("Error: Public/SMAX does not exist.")
            exit()
        smaxpath = f"{ROOT}/{smax_num}"
        if not smaxpatching.getDeviceGroupPath(smaxpath):
            smaxpatching.createFolder(smax_num)
            smaxpatching.getDeviceGroupPath(smaxpath)
            asyncio.run(smaxpatching.createTimeSlotFolders(hosts))      
            asyncio.run(smaxpatching.addHostsToDGs())
            if not args.nopatching:
                asyncio.run(smaxpatching.getDevAttachScripts())
            #smaxpatching.printHostsSummary()
        else:
            print("Found path. SMAX is already created.")
            sys.exit(1)    
        smax_suffix += 1
        print(start_date, "=================================")
        if not args.nopatching:
            notifyafterpatch = Notification(smaxpatching, start_date)
            notifyafterpatch.set_scehdule()
    if not args.nopatching:
        smaxpatching.blackoutMonitoring()

        
if __name__ == '__main__':
    s = time.perf_counter()
    total_hosts = 0
    # Read servers.csv from https://10.122.0.21:3001/sasa/servers.csv
    smax = read_servers_csv2()
    main(smax)
    e = time.perf_counter()
    print(f"Task duration: {e - s}")
    os.unlink('/tmp/servers.csv')
    sys.exit(0)