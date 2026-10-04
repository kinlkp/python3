#!/usr/bin/env python
#
# Written by Brian Leung
#
# Example script to unmount/mount datastores

from datacenter import run_cli
from tools import cli, service_instance, pchelper
from pyVmomi import vim

import time
import csv
import json


DATASTORE_LIST_CSV = "datastore_list.csv"


def compare_csv_all_ds(content, datacenter):
    results = []
    # Match the csv uuid with Vcenter uuid
    for csv_name, csv_uuid in read_ds_csv().items():
        for u in find_all_vcenter_ds(content, datacenter):
            if u['uuid'] == csv_uuid and u['name'] == csv_name:
                results.append(u)
    return results


def find_all_vcenter_ds(content, datacenter):
    # Connect to Vcenter and find all datastores
    uuids = []
    host_view = content.viewManager.CreateContainerView(datacenter, [vim.HostSystem], True)
    # Find all datastores in vcenter
    for host in host_view.view:
        # host.configManager.storageSystem.UnmountVmfsVolume(vmfsUuid="65976112-57b5c868-b7b1-005056af88ac")
        mount_arr = host.configManager.storageSystem.fileSystemVolumeInfo.mountInfo
        for m in mount_arr: 
            if m.volume.type == "VMFS":
                uuids.append({'uuid': m.volume.uuid, 'name': m.volume.name, 'host': host})
    return uuids


def read_ds_csv():
    csv_uuids = {}
    # Read .csv to get datastores being unmounted
    with open(DATASTORE_LIST_CSV) as csvfile:
        rows = csv.DictReader(csvfile)
        for row in rows:
            csv_uuids[row['datastore_name']] = row['datastore_uuid']
    return csv_uuids


def mount_or_umount_ds(args, results):
    count = 0
    for res in results:
        if args.mount.lower() == 'n':
            res['host'].configManager.storageSystem.UnmountVmfsVolume(vmfsUuid=res['uuid'])
            state = "unmounted"
        elif args.mount.lower() == 'y':
            res['host'].configManager.storageSystem.MountVmfsVolume(vmfsUuid=res['uuid'])
            state = "mounted"
        else:
            raise Exception(f"Wrong mount state: {state}")
        print(f"{res['host']} {state} datastore {res['name']} {res['uuid']}")
        count += 1
    return count, state


def main():
    args = run_cli(cli.Argument.MOUNT, cli.Argument.DATACENTER_NAME)
    # Connect to VCenter
    si = service_instance.connect(args)
    content = si.RetrieveContent()
    # Find datacenter name
    DATACENTER = pchelper.get_obj(content, [vim.Datacenter], args.datacenter_name)

    # Datastore list. Example, 
    # results = 
    #  [{'uuid': '65976112-57b5c868-b7b1-005056af88ac', 'name': 'san-1', 
    # 'host': 'vim.HostSystem:host-1391'},...]
    results = compare_csv_all_ds(content, DATACENTER)

    # Mount or Unmount the datastores
    try:
        (count, state) = mount_or_umount_ds(args, results)
    except Exception as e:
        print(f"\nError: failed to umount datastore {e.msg}")
        print("Umount datastore aborted.")
        exit()

    print(f"\n{count} datastores are {state}.")


if __name__ == '__main__':
    main()