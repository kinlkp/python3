#!/bin/bash

vcenter_ip="10.1.5.44"
basic_auth_base64=$(echo -n 'administrator@vsphere.local:abcd1234' | base64)
session_id_json=$(curl --silent -k -XPOST -H "Authorization: Basic ${basic_auth_base64}" https://$vcenter_ip/rest/com/vmware/cis/session)
session_id=$(echo "$session_id_json" | jq '.value')
x=$(echo "$session_id" | sed -e 's/\"//g')
#curl --silent -k -XGET -H 'vmware-api-session-id: '"$x"  https://$vcenter_ip/rest/vcenter/vm # list vm internal name

curl --silent -k -XGET -H 'vmware-api-session-id: '"$x"  https://$vcenter_ip/rest/vcenter/vm/vm-97 # get specific vm details
