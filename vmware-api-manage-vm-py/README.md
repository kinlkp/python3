# VMware DR scripts

# Requirements:

1. python 3.9 with virtual environment

2. pyvmomi module

pip install pyvmomi

# Getting started

**_Activate python virtual env_**

source ~/venv/bin/activate

# Build execuable

pip install pyinstaller

pyinstaller --onefile vm.py

# DR steps

**_List all VMs in Vcenter_**

./get_all_vm_names.py -s _vcenter-ip_ -u '_administrator@vsphere.local_' -p '_password_' -nossl --datacenter-name '_datacenter_name_'

**_edit hostlist_**

Add the vm names into file vm_list

**_Shut down VMs in Vcenter_**

./vm.py -s _vcenter-ip_ -u '_administrator@vsphere.local_' -p '_password_' -nossl --datacenter-name '_datacenter_name_' --power off

Output:

    Shutting down: abc1
    Shutting down: abc2
    abc1 is in poweredOff
    abc2 is in poweredOff

    2 VMs are powered off.

**_Unregister VMs in Vcenter_**

./unregister_vms.py -s _vcenter-ip_ -u '_administrator@vsphere.local_' -p '_password_' -nossl --datacenter-name '_datacenter_name_'

Output:

    abc2 is unregistered.
    abc1 is unregistered.

    2 VMs are unregistered.

**_Edit datastore_list.csv_**

Add the datastores being umounted

**_Unmount datastores in Vcenter_**

./datastore.py -s _vcenter-ip_ -u '_administrator@vsphere.local_' -p '_password_' -nossl --mount n --datacenter-name '_datacenter_name_'

Output:

    'vim.HostSystem:host-10' unmounted datastore san-1 65976112-57b5c868-b7b1-005056af88ac
    'vim.HostSystem:host-16' unmounted datastore san-1 65976112-57b5c868-b7b1-005056af88ac
    'vim.HostSystem:host-10' unmounted datastore san-2 65976122-59d3f660-dded-005056af88ac
    'vim.HostSystem:host-16' unmounted datastore san-2 65976122-59d3f660-dded-005056af88ac
    'vim.HostSystem:host-10' unmounted datastore san-3 65976131-80086a28-d939-005056af88ac
    'vim.HostSystem:host-16' unmounted datastore san-3 65976131-80086a28-d939-005056af88ac

    6 datastores are unmounted.

**_Mount datastores in Vcenter_**

./datastore.py -s _vcenter-ip_ -u '_administrator@vsphere.local_' -p '_password_' -nossl --mount y --datacenter-name '_datacenter_name_'

Output:

    'vim.HostSystem:host-10' mounted datastore san-1 65976112-57b5c868-b7b1-005056af88ac
    'vim.HostSystem:host-16' mounted datastore san-1 65976112-57b5c868-b7b1-005056af88ac
    'vim.HostSystem:host-10' mounted datastore san-2 65976122-59d3f660-dded-005056af88ac
    'vim.HostSystem:host-16' mounted datastore san-2 65976122-59d3f660-dded-005056af88ac
    'vim.HostSystem:host-10' mounted datastore san-3 65976131-80086a28-d939-005056af88ac
    'vim.HostSystem:host-16' mounted datastore san-3 65976131-80086a28-d939-005056af88ac

    6 datastores are mounted.


**_Register VMs in Vcenter_**

./register_vms.py -s _vcenter-ip_ -u '_administrator@vsphere.local_' -p '_password_' -nossl --datacenter-name '_datacenter_name_'

Output:

    6 VMs are registered.


**_Power on VMs in Vcenter_**

./vm.py -s _vcenter-ip_ -u '_administrator@vsphere.local_' -p '_password_' -nossl --datacenter-name '_datacenter_name_' --power on

Output:

    Powering on: New Virtual Machine
    Powering on: abc2
    Powering on: abc4
    Powering on: abc1
    Powering on: abc3
    Powering on: abc5

    6 VMs are powered on.
