#!/usr/bin/env python
#
# Written by Brian Leung
#
# Example script to power off VMs


from tools import cli, service_instance, pchelper
from pyVmomi import vim

import json


VM_LIST_FILE = "vm_list.txt"
VM_CFG_BACKUP = "results.json"


def read_vm_list():
    #Read the VM names from hosts file
    with open(VM_LIST_FILE, "r") as file:
        file_content = file.read()
    return file_content.split('\n')


def read_result_json():
    # Read the vm config backup from results.json
    with open(VM_CFG_BACKUP, "r") as j:
        data = json.load(j)
    return data


def run_cli(*args):
    parser = cli.Parser()
    for a in args:
        if a["name_or_flags"][0] == "--vm-name":
            parser.add_optional_arguments(a)
        else:
            parser.add_required_arguments(a)
    return parser.get_args()


def vm_config_backup(si, datacenter_name):
    content = si.RetrieveContent()
    DATACENTER = pchelper.get_obj(content, [vim.Datacenter], datacenter_name)
    
    results = []
    VM = pchelper.get_all_obj(content, [vim.VirtualMachine], DATACENTER.vmFolder)
    for v in VM:
        if not v.config.template:
            print(f"Storing config of {v.name} in results.json.")
            obj = {}
            obj['name'] = v.name
            obj['uuid'] = v.config.uuid
            obj['vm_obj'] = str(v)
            obj['folder'] = str(v.parent)
            obj['host'] = v.summary.runtime.host.name
            obj['vm_path'] = v.summary.config.vmPathName
            obj['resource_pool'] = str(v.resourcePool)
            results.append(obj)

    # Write vm config to results.json
    with open("results.json", "w") as f:
        f.write(json.dumps(results))
        

def main():
    args = run_cli(cli.Argument.DATACENTER_NAME)
    si = service_instance.connect(args)
    vm_config_backup(si, args.datacenter_name)


if __name__ == '__main__':
    main()