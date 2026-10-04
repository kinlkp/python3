#!/usr/bin/env python
#
# Written by Brian Leung
#
# Example script to register VMs after DR

from datacenter import run_cli, read_vm_list, read_result_json
from tools import cli, service_instance, pchelper
from pyVmomi import vim

import json


def get_all_folders(content, DATACENTER):
    fds = {}
    all_folders = pchelper.get_all_obj(content, [vim.Folder], DATACENTER.vmFolder)

    for f in all_folders:
        fds[str(f)] = f
    # return a map fds['folder_name'] = folder object        
    return fds


def get_all_resource_pools(content):
    rps = {}
    all_folders = pchelper.get_all_obj(content, [vim.ResourcePool])
    for x in all_folders:
        rps[str(x)] = x
    # return a map rp['pool_name'] = pool object
    return rps


def register_vm(content, DATACENTER, vms, fds, rps):
    count = 0
    for vm in vms:
        # Read the results.json which is created in unregister
        for d in read_result_json():
            if vm == d['name']:
                # create host object for the vm before register
                esx_host = pchelper.get_obj(content, [vim.HostSystem], d['host'])
                if d['folder'] == str(DATACENTER.vmFolder):
                    # VM in datacenter root folder
                    folder_obj = DATACENTER.vmFolder
                else:
                    folder_obj = fds[d['folder']]

                folder_obj.RegisterVM_Task(path=d['vm_path'], name=d['name'], 
                                           asTemplate=False, 
                                           pool=rps[d['resource_pool']], 
                                           host=esx_host)
                count += 1
    return count

def main():
    args = run_cli(cli.Argument.DATACENTER_NAME)
    si = service_instance.connect(args)
    content = si.RetrieveContent()

    rps = get_all_resource_pools(content)

    DATACENTER = pchelper.get_obj(content, [vim.Datacenter], args.datacenter_name)
    fds = get_all_folders(content, DATACENTER)

    VM_LIST = read_vm_list()
    count = register_vm(content, DATACENTER, VM_LIST, fds, rps)
    print(f"\n{count} VMs are registered.")


if __name__ == '__main__':
    main()