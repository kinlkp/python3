#!/usr/bin/env python
#
# Written by Brian Leung
#
# Example script to unregister VMs

from tools import cli, service_instance, pchelper
from pyVmomi import vim
from datacenter import vm_config_backup, read_vm_list, run_cli

import time


def unregister(vm_name, all_vms):
    if not all_vms:
        return False

    for key, value in all_vms.items():
        if key.runtime.powerState == "poweredOff" and value == vm_name:
            try:
                key.UnregisterVM()
                print(f"{vm_name} is unregistered.")
            except:
                return False

    return True


def backup_cfg(si, args):
    # backup is used by registration process later
    try:
        vm_config_backup(si, args.datacenter_name)
    except:
        return False

    return True


def main():
    args = run_cli(cli.Argument.DATACENTER_NAME)
    si = service_instance.connect(args)
    if backup_cfg(si, args):
        content = si.RetrieveContent()
        DATACENTER = pchelper.get_obj(content, [vim.Datacenter], args.datacenter_name)
        # Read the VM names from vm_list file
        VM_LIST = read_vm_list()

        count = 0
        for vmname in VM_LIST:
            if unregister(vmname, pchelper.get_all_obj(content, [vim.VirtualMachine], DATACENTER.vmFolder)):
                count += 1
        print(f"\n{count} VMs are unregistered.")
    else:
        print("Error: failed to backup current VMs config in results.json. Unregister aborted!")
    

if __name__ == '__main__':
    main()