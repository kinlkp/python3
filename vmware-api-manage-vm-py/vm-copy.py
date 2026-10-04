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

import time


def main():
    args = run_cli(cli.Argument.DATACENTER_NAME)
    si = service_instance.connect(args)
    content = si.RetrieveContent()
    DATACENTER = pchelper.get_obj(content, [vim.Datacenter], args.datacenter_name)
    abc1 = pchelper.get_obj(content, [vim.VirtualMachine], "abc1", DATACENTER.vmFolder)
    spec = vim.vm.ConfigSpec()
    # get all disks on a VM, set unit_number to the next available
    unit_number = 0
    controller = None
    disk_size = 2
    disk_type = "thin"
    for device in abc1.config.hardware.device:
        print(device)
        if hasattr(device.backing, 'fileName'):
            unit_number = int(device.unitNumber) + 1
            # unit_number 7 reserved for scsi controller
            if unit_number == 7:
                unit_number += 1
            if unit_number >= 16:
                print("we don't support this many disks")
                return -1
        if isinstance(device, vim.vm.device.VirtualSCSIController):
            controller = device
        if isinstance(device, vim.vm.device.VirtualPCIController):
            device.device.append(1001)
            pcislot = device
    if controller is None:
        print("Disk SCSI controller not found!")
        return -1
    
    controller_spec = vim.vm.device.VirtualDeviceSpec()
    controller_spec.fileOperation = "replace"
    controller_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
    # controller_spec.device = vim.vm.device.VirtualLsiLogicController()
    controller_spec.device = controller
    # controller_spec.device.key = 1001
    controller_desc = vim.Description()
    controller_desc.label = "SCSI controller 1"
    controller_desc.summary = "LSI Logic"
    controller_spec.device.deviceInfo = controller_desc
    # controller_slot = vim.vm.device.VirtualDevice.PciBusSlotInfo()
    # controller_slot.pciSlotNumber = 17
    # controller_spec.device.slotInfo = controller_slot
    # controller_spec.device.controllerKey = 100
    # controller_spec.device.unitNumber = 4
    # controller_spec.device.busNumber = 1
    # controller_spec.device.device = []
    # controller_spec.device.hotAddRemove = True
    # controller_spec.device.sharedBus = 'noSharing'
    # controller_spec.device.scsiCtlrUnitNumber = 7
    # add disk here
    dev_changes = []
    new_disk_kb = int(disk_size) * 1024 * 1024
    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.fileOperation = "create"
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    disk_spec.device = vim.vm.device.VirtualDisk()
    disk_spec.device.backing = \
        vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
    if disk_type == 'thin':
        disk_spec.device.backing.thinProvisioned = True
    disk_spec.device.backing.diskMode = 'persistent'
    disk_spec.device.unitNumber = unit_number
    disk_spec.device.capacityInKB = new_disk_kb
    disk_spec.device.controllerKey = controller.key
    # dev_changes.append(disk_spec)
    # pci_spec = vim.vm.device.VirtualDeviceSpec()
    # pci_spec.fileOperation = "replace"
    # pci_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
    # pci_spec.device = pcislot
    # dev_changes.append(pci_spec)
    dev_changes.append(controller_spec)
    # pci_spec = vim.vm.device.VirtualDeviceSpec()
    # pci_spec.fileOperation = "create"
    # pci_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    # pci_spec.device = vim.vm.device.VirtualPCIController()
    # pci_spec.device.key = 101
    # pci_spec.device.deviceInfo = vim.Description(label='PCI controller 1', summary='PCI controller 1')
    # pci_spec.device.busNumber = 0
    # pci_spec.device.device = []
    
    # dev_changes.append(pci_spec)
    spec.deviceChange = dev_changes
    abc1.ReconfigVM_Task(spec=spec)
    
    # print(pcislot)
    

if __name__ == '__main__':
    main()