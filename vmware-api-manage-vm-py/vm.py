#!/usr/bin/env python
#
# Written by Brian Leung
#
# Example script to shut down VMs

from datacenter import run_cli, read_vm_list
from tools import cli, service_instance, tasks, pchelper
from pyVmomi import vim
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Union

import sys
import time


MAX_WORKERS_NUM = 2

VM_LIST = read_vm_list()


def find(args, si):
    if not args.vm_name:
        print(f"Error: argument vm name not provided.")
        sys.exit(1)
    content = si.RetrieveContent()
    DATACENTER = pchelper.get_obj(content, [vim.Datacenter], args.datacenter_name)

    try:
        dc_vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name, DATACENTER.vmFolder)
    except:
        print(f"Error: vm {args.vm_name} not found.")
        sys.exit(1)
    print(f"{dc_vm.name} is found.")


def power_on(vm_name, si, datacenter_name) -> Union[int, bool]:
    content = si.RetrieveContent()
    DATACENTER = pchelper.get_obj(content, [vim.Datacenter], datacenter_name)
    dc_vm = None
    try:
        dc_vm = pchelper.get_obj(content, [vim.VirtualMachine], vm_name, DATACENTER.vmFolder)
    except:
        print(f"Error: vm {vm_name} not found.")
        sys.exit(1)
    if not dc_vm:
        print(f"Error: vm {vm_name} not found.")
        sys.exit(1)
    esx_host = pchelper.get_obj(content, [vim.HostSystem], dc_vm.summary.runtime.host.name)
    task = dc_vm.PowerOnVM_Task(esx_host)
    tasks.wait_for_tasks(si, [task])
    return 1

# def power_on(vm_name, si, datacenter_name) -> Union[int, bool]:
#     content = si.RetrieveContent()
#     DATACENTER = pchelper.get_obj(content, [vim.Datacenter], datacenter_name)
#     dc_all_vm = None
#     try:
#         dc_all_vm = pchelper.get_all_obj(content, [vim.VirtualMachine], DATACENTER.vmFolder)
#     except:
#         pass

#     if not dc_all_vm:
#         return False
    
#     count = 0
#     for key, value in dc_all_vm.items():
#         if key.runtime.powerState == "poweredOff" and value == vm_name:
#             print(f"Powering on: {value}")
#             esx_host = pchelper.get_obj(content, [vim.HostSystem], key.summary.runtime.host.name)
#             count += 1
#             if count > len(VM_LIST):
#                 print(f"Error: count {count} is larger than list length.")
#                 sys.exit(1)
#             task = key.PowerOnVM_Task(esx_host)
#             tasks.wait_for_tasks(si, [task])
                
#     return count
        

def take_snapshot(vm_name, si, datacenter_name) -> Union[int, bool]:
    content = si.RetrieveContent()
    DATACENTER = pchelper.get_obj(content, [vim.Datacenter], datacenter_name)
    the_vm = pchelper.get_obj(content, [vim.VirtualMachine], vm_name, DATACENTER.vmFolder)
    if not the_vm:
        return False
    task = the_vm.CreateSnapshot_Task("snapshot before SA 2024 upgrade", "", False, False)
    tasks.wait_for_tasks(si, [task])
    return 1
    # dc_all_vm = None
    # try:
    #     dc_all_vm = pchelper.get_all_obj(content, [vim.VirtualMachine], DATACENTER.vmFolder)
    # except:
    #     pass
    
    # if not dc_all_vm:
    #     return False
        
    # count = 0
    # for key, value in dc_all_vm.items():
    #     if value == vm_name:
    #         print(vm_name)
    #         task = key.CreateSnapshot_Task("snapshot before rhel 8.10 upgrade", "", False, False)
    #         count += 1
    #         if count > len(VM_LIST):
    #             print(f"Error: count {count} is larger than list length.")
    #             sys.exit(1)
    #         tasks.wait_for_tasks(si, [task])
    
    # return count


# def shut_down(vm_name, si, datacenter_name) -> Union[int, bool]:
#     content = si.RetrieveContent()
#     DATACENTER = pchelper.get_obj(content, [vim.Datacenter], datacenter_name)
#     dc_all_vm = None
#     try:
#         dc_all_vm = pchelper.get_all_obj(content, [vim.VirtualMachine], DATACENTER.vmFolder)
#     except:
#         pass
    
#     if not dc_all_vm:
#         return False
        
#     count = 0
#     for key, value in dc_all_vm.items():
#         if key.runtime.powerState != "poweredOff" and value == vm_name:
#             try:
#                 print(f"Shutting down: {value}")
#                 count += 1
#                 if count > len(VM_LIST):
#                     print(f"Error: count {count} is larger than list length.")
#                     sys.exit(1)
#                 key.ShutdownGuest()
#             except Exception as e:
#                 print(f"Powering off: {vm_name} due to {e.msg}")
#                 key.PowerOffVM_Task()
    
#     return count

def shut_down(vm_name, si, datacenter_name) -> Union[int, bool]:
    content = si.RetrieveContent()
    DATACENTER = pchelper.get_obj(content, [vim.Datacenter], datacenter_name)
    dc_vm = None
    try:
        dc_vm = pchelper.get_obj(content, [vim.VirtualMachine], vm_name, DATACENTER.vmFolder)
    except:
        print(f"Error: vm {vm_name} not found.")
        sys.exit(1)
        
    count = 0
    try:
        count += 1
        dc_vm.ShutdownGuest()
    except Exception as e:
        print(f"Powering off: {vm_name} due to {e.msg}")
        dc_vm.PowerOffVM_Task()
        
    # for key, value in dc_all_vm.items():
    #     if key.runtime.powerState != "poweredOff" and value == vm_name:
    #         try:
    #             print(f"Shutting down: {value}")
    #             count += 1
    #             if count > len(VM_LIST):
    #                 print(f"Error: count {count} is larger than list length.")
    #                 sys.exit(1)
    #             key.ShutdownGuest()
    #         except Exception as e:
    #             print(f"Powering off: {vm_name} due to {e.msg}")
    #             key.PowerOffVM_Task()
    
    return count


def start_workers(action, si, args):
    count = 0
    # VM_LIST = read_vm_list()
    # Parallel actions on the VMs
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_NUM) as executor:
        results = [executor.submit(action, vm_name.strip(), si, args.datacenter_name) 
                   for vm_name in VM_LIST if vm_name and not vm_name.startswith('#')]
        for result in as_completed(results):
            if result.exception():
                # Print the exception from threads
                print(result.exception())
            else:
                count += result.result()

    print(f"\n{count} VMs are {args.action}.")
    

def main():
    args = run_cli(cli.Argument.DATACENTER_NAME, cli.Argument.ACTION, cli.Argument.VM_NAME)
    si = service_instance.connect(args)
    # content = si.RetrieveContent()
    # abcd = pchelper.search_for_obj(content, [vim.VirtualMachine], "n2vsmsautl0010")
    # print(abcd)
    if args.action == "on":
        start_workers(power_on, si, args)
    elif args.action == "off":
        start_workers(shut_down, si, args)
    elif args.action == "snapshot":
        start_workers(take_snapshot, si, args)
    elif args.action == "find":
        find(args, si)
    else:
        print("Error: wrong options.")
    

if __name__ == '__main__':
    main()
