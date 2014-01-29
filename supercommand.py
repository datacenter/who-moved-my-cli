#!/usr/bin/env python
#
# Copyright (C) 2013 Cisco Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0 
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# This script is a simple 'supercommand', where a sequence of three
# common commands, show ip arp, show mac address-table and show cdp neighbor
# are all chained with their outputs fed into each other to gather information
# about a particular device connected to this switch.
#
# The script can be easily extended to include additional commands, and introduce
# branching logic to handle different situations. An example may be totreat a 
# host that appears in the CDP table differently from one that does not, and 
# collect a other command outputs in that case
# 

import cli
import json
import re
from argparse import ArgumentParser

# Perform some basic argument parsing for parameters passed to the script
parser = ArgumentParser('Supercommand')
parser.add_argument('ip')
args = parser.parse_args()
ip = args.ip

# Check the output of the ARP table for the IP address in question
arp = json.loads(cli.clid('show ip arp %s vrf all' % ip))['TABLE_vrf']['ROW_vrf']['TABLE_adj']['ROW_adj']
if len(arp) == 0:
    raise Exception('Unable to find %s in ARP output' % ip)

# Take the resulting output and collect the fields we want
ip, timer, mac, interface = arp['ip-addr-out'], arp['time-stamp'], arp['mac'], arp['intf-out']

# Now use the MAC address we extracted for the IP and look it up in the CAM table
for cam in cli.cli('show mac address-table address %s' % (mac)).split('\n'):
    if mac in cam: break
else:
    raise Exception('Unable to find %s in CAM output' % mac)

cam_fields = cam.split()
if cam_fields[0] in ['*', 'G', 'R', '+']: cam_fields.pop(0)

vlan, mac, entrytype, age, secure, ntfy, port = cam_fields

# Next use the interface we found the device on from CAM and look it up in CDP
cdp = json.loads(cli.clid('show cdp neighbor interface %s' % port))['TABLE_cdp_neighbor_brief_info']['ROW_cdp_neighbor_brief_info']
if len(cdp) == 0:
    raise Exception('Unable to find %s in CDP output' % port)
if len(cdp) > 0:
	cdp = cdp[0]

# Finally print out all of this information
print('Here is some information on %s:' % ip)
print(' ' * 4 + 'MAC address: %s' % mac)
print(' ' * 4 + 'Local interface: %s' % port)
print(' ' * 4 + 'VLAN: %s' % vlan)
print(' ' * 4 + 'L3 gateway: %s' % interface)
print(' ' * 4 + 'CDP Platform: %s' % cdp['platform_id'])
print(' ' * 4 + 'CDP Device ID: %s' % cdp['device_id'])
print(' ' * 4 + 'CDP Port ID: %s' % cdp['port_id'])
