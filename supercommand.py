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

# This script is a simple 'supercommand', where a sequence of three
# common commands, show ip arp, show mac address-table and show cdp neighbor
# are all chained with their outputs fed into each other to gather information
# about a particular device connected to this switch.
#
# The script can be easily extended to include additional commands, and introduce
# branching logic to handle different situations, such as treat a host that appears
# in the CDP table differently from one that does not. 
# 

from cisco import *
from argparse import ArgumentParser

# Perform some basic argument parsing for parameters passed to the script
parser = ArgumentParser('Supercommand')
parser.add_argument('ip')
args = parser.parse_args()
ip = args.ip

# Check the output of the ARP table for the IP address in question
for arp in CLI('show ip arp %s' % (ip), do_print=False).get_output():
    if ip in arp: break
else:
    raise Exception('Unable to find %s in ARP output' % ip)

# Take the resulting output and split it into relevant fields
ip, timer, mac, interface = arp.split()

# Now use the MAC address we extracted for the IP and look it up in the CAM table
for cam in CLI('show mac address-table address %s' % (mac), do_print=False).get_output():
    if mac in cam: break
else:
    raise Exception('Unable to find %s in CAM output' % mac)

# Remove some extraneous information from the CAM output and then parse our fields
cam_fields = cam.split()
if cam_fields[0] == '*': cam_fields.pop(0)
vlan, mac, entrytype, age, secure, ntfy, port = cam_fields

# Next use the interface we found the device on from CAM and look it up in CDP
for cdp in CLI('show cdp neighbor interface %s' % (port), do_print=False).get_output():
    if port in cdp: break
else:
    raise Exception('Unable to find %s in CDP output' % port)

# Finally print out all of this information
print('Here is some information on %s:' % ip)
print(' ' * 4 + 'MAC address: %s' % mac)
print(' ' * 4 + 'Local interface: %s' % port)
print(' ' * 4 + 'VLAN: %s' % vlan)
print(' ' * 4 + 'L3 gateway: %s' % interface)
print(' ' * 4 + 'CDP details: %s' % cdp)
