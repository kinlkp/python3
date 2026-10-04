#!/opt/opsware/agent/bin/python3

'''
The script is used to check the modification of the critical files
SMAX 12371457 11760322
'''

import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta


BACKUPDIR = "/var/tmp/bk_crit2"
LOGPATTERN = r".*type=PROCTITLE\smsg=audit\((\S+\s\d{2}:\d{2}:\d{2})\.\S+\)\s:\s(proctitle=[a-zA-Z0-9\s_,\^\#\-\.\/\+\?\{\}@]+)\stype=PATH\s+.*(cwd=\S+).*(ppid=\d+)\s(pid=\d+)\s(auid=\S+).*\s(euid=\S+).*(tty=\S+)\s.*"
FILES_DICT = {
    'file000': '/etc/sudoers',
    'file001': '/etc/audit/rules.d',
    'file002': '/etc/audit/auditd.conf',
    'file003': '/etc/selinux/config',
    'file004': '/etc/sudoers.d',
    'file005': '/etc/rsyslog.conf',
    'file006': '/etc/group',
    'file007': '/var/lib/rpm/Name',
    'file008': '/etc/ssh/sshd_config',
    'file009': '/etc/hosts',
    'file010': '/var/spool/cron'
}
PATCHING_YUM_UPDATE = '/var/tmp/yum-update.txt'


class ModifiedFile:
    def __init__(self, filename, match_regex):
        try:
            # 2 digit year format
            format_string = '%m/%d/%y %H:%M:%S'
            date_string = match_regex.group(1)[:19]
            dt_object = datetime.strptime(date_string, format_string)
        except ValueError:
            # 4 digit year format
            format_string = '%m/%d/%Y %H:%M:%S'
            dt_object = datetime.strptime(date_string, format_string)
        except Exception as ex:
            print(f"Error: {ex}")
            sys.exit(1)
        modified_time = dt_object.timestamp()
        self.modified_time =  modified_time
        self.command = match_regex.group(2)
        self.workDir = match_regex.group(3)
        self.ppid = match_regex.group(4)
        self.filename = filename
        self.originalUID = match_regex.group(6)
        self.effectiveUID = match_regex.group(7)
        self.tty = match_regex.group(8)
        self.pid = match_regex.group(5)
        self.diff_result = ""
        
    def print_syslog(self):
        date_object = datetime.fromtimestamp(self.modified_time)
        self.command = self.command.replace('proctitle', 'command')
        self.workDir = self.workDir.replace('cwd', 'workDir')
        self.originalUID = self.originalUID.replace('auid', 'originalUID')
        self.effectiveUID = self.effectiveUID.replace('euid', 'effectiveUID')
        message = f"Information: {self.filename} has been changed on {str(date_object)} Details: {self.command}, {self.workDir}, {self.originalUID}, {self.effectiveUID}, {self.tty}, {self.ppid}, {self.pid}"
        message += f", targetFileDiff: {self.diff_result}"
        subprocess.run(["logger", "-p", "local0.warning", message])
        print(message)

        
    def diff_file(self):
        basename = os.path.basename(self.filename)
        result = subprocess.run(["diff", f"{self.filename}", f"{BACKUPDIR}/{basename}-base"], capture_output=True)
        subprocess.run(["rm", "-rf", f"{BACKUPDIR}/{basename}-base"])
        subprocess.run(["cp", "-pr", self.filename, f"{BACKUPDIR}/{basename}-base"])
        # Set the diff file result
        self.diff_result = result.stdout.decode().strip().replace('\n', '\\n')


def recent_patching(filename):
    """
    if patching happens within 24 hours, 
    rules file007 will be skipped.
    """
    if filename != '/var/lib/rpm/Name':
        return False
    if os.path.exists(PATCHING_YUM_UPDATE):
        ymu_update_m_time = os.path.getmtime(PATCHING_YUM_UPDATE)
        if time.time() - ymu_update_m_time < 86400:
            print("Patching happened today.")
            return True
        else:
            return False
    else:
        # /var/tmp/yum-update.txt does not exist
        return False


def check_ausearch(search_key):
    # for search_key, file in FILES_DICT.items():
    now = datetime.now()
    yesterday = now - timedelta(hours=24)
    getpids = f"nice -n +10 ausearch -i -k {search_key} -sc openat -ts today | grep ^type=SYSCALL | sort -k2 | cut -d' ' -f15 |uniq"
    result = subprocess.run(getpids, shell=True, capture_output=True)
    for pid in result.stdout.decode('utf-8').split('\n'):
        if pid:
            pid = pid.replace('pid=', '')
            ausearch = f"nice -n +10 ausearch -i -k {search_key} -sc openat -p {pid} -ts today --just-one"
            result = subprocess.run(ausearch, shell=True, capture_output=True)
            yield result.stdout.decode('utf-8')


def check_critical_files():
    for searchkey, filename in FILES_DICT.items():
        if recent_patching(filename):
            continue
        fileObjectTmp = None
        for item  in check_ausearch(searchkey):
            data_string = item.replace('\n', '')
            # print(data_string)
            match = re.search(LOGPATTERN, data_string)
            if not match:
                print(f"Error: failed to match LOGPATTERN: {data_string}")
                continue
            fileObject = ModifiedFile(filename, match)
            if fileObject:
                fileObjectTmp = fileObject
                yield fileObject
        if fileObjectTmp:
            # To reflect the latest difference, find the difference in the last object
            fileObjectTmp.diff_file()


def main():
    if not os.path.exists(BACKUPDIR):
        # Create the file baseline
        os.mkdir(BACKUPDIR, mode=0o700)
        for _, filename in  FILES_DICT.items():
            subprocess.run(["cp", "-pr", filename, f"{BACKUPDIR}/{os.path.basename(filename)}-base"])
        print("INFO: baseline is created.")
    else:
        # Return a list of ModifiedFile objects
        files = [line for line in check_critical_files()]
        sorted_by_time = sorted(files, key=lambda file: file.modified_time)
        for file in sorted_by_time:
            file.print_syslog()
        print("Completed.")


if __name__ == '__main__':
    main()
