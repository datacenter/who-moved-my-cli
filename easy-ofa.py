#!/usr/bin/env python
#
# Copyright (C) 2014 Cisco Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# This script installs and configures the Cisco Plug-in for OpenFlow.  Copy
# the script to bootflash: and execute using:
# 
# 	# source easy-ofa.py <package>
# 			   - or -
# 	# python bootflash:easy-ofa.py <package>
# 
# Additional help is available using the --help option.
#

import argparse
import cisco
import re
import sys
import time

supported = ['Nexus3016', 'Nexus3064', 'Nexus3048', 'Nexus3132', 'Nexus5548', 'Nexus5596', 'Nexus6001', 'Nexus6004']

def max_flows(platform):
	print 'Tuning switch TCAM for max flows ...'
	if platform == 'Nexus6001' or platform == 'Nexus6004':
		cisco.cli("conf t")
		cisco.cli("hardware profile tcam resource template vacl 0")
		cisco.cli("hardware profile tcam resource template ifacl 3520")
		cisco.cli("hardware profile tcam resource template e-vacl 0")
		cisco.cli("hardware profile tcam resource template rbacl 0")
		cisco.cli("hardware profile tcam resource template qos 128")
		cisco.cli("hardware profile tcam resource template span 64")
		cisco.cli("end")
	elif platform == 'Nexus3016' or platform == 'Nexus3064' or platform == 'Nexus3048' or platform == 'Nexus3132':
		cisco.cli("conf t")
		cisco.cli("hardware profile tcam region vacl 0")
		cisco.cli("hardware profile tcam region e-vacl 0")
		cisco.cli("hardware profile tcam region racl 0")
		cisco.cli("hardware profile tcam region e-racl 0")
		cisco.cli("hardware profile tcam region qos 0")
		cisco.cli("hardware profile tcam region ifacl 1644")
		cisco.cli("end")
	else:
		print 'TCAM tuning not supported, bypassing ...'

def normalize(interface):
	if ("eth" in interface or "Eth" in interface):
		match = re.search("[a-z A-Z]*([0-9/]*)", interface)
		if match:
			# Interface must be spelled out, all lower case, no spaces
			return "ethernet%s" % match.group(1)

def expand(links):
	expanded_links = []
	for link in links.split():
		int_range = link.split("-")
		if len(int_range) == 2:
			slot_int = int_range[0].split("/")
			i = int(slot_int[1])
			while i <= int(int_range[1]):
				expanded_links.append("%s/%s" % (normalize(slot_int[0]), i))
				i += 1
		else:
			expanded_links.append(normalize(int_range[0]))
	return expanded_links

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('package', help = 'OpenFlow Plug-in OVA package to install')
	parser.add_argument('-m', '--maxflows', help = 'Tune switch TCAM to support maximum number of flows', required = False, action = 'store_true')
	args = parser.parse_args()
	
	ver = cisco.cli("show version")
	platform = re.search(r'(Hardware\s*cisco\s)([^\s]+)', ver).group(2)
	if platform not in supported:
		print 'ERROR: Unsupported hardware platform.'
		sys.exit(1)

	if args.maxflows:
		max_flows(platform)
	
	# raw_input() doesn't work reliably across all platforms, so ...
	sys.stdout.write('Interfaces (seperated by space) to use for OpenFlow: ')
	sys.stdout.flush()
	interfaces = sys.stdin.readline()
	
	# TODO: Input validation ...
	sys.stdout.write('Enter the OpenFlow controller IP address: ')
	sys.stdout.flush()
	controller = sys.stdin.readline()
	
	sys.stdout.write("Enter vrf (If no input, current vrf 'default' is used): ")
	sys.stdout.flush()
	vrf = sys.stdin.readline()
	if not vrf:
		vrf = 'default'
	
	print '\nEnabling OpenFlow hardware profile ...'
	cisco.cli("conf t")
	cisco.cli("hardware profile openflow")
	cisco.cli("end")
	
	print 'Installing Cisco Plug-in for OpenFlow ...'
	cisco.cli("virtual-service install name ofa package bootflash:" + args.package)
	while True:
		status = re.search(r'ofa\s*Installed', cisco.cli("show virtual-service list | i ofa"))
		time.sleep(3)
		if status:
			break
	
	print 'Activating Cisco Plug-in for OpenFlow ...'
	cisco.cli("conf t")
	cisco.cli("virtual-service ofa")
	cisco.cli("activate")
	cisco.cli("end")
	while True:
		status = re.search(r'ofa\s*Activated', cisco.cli("show virtual-service list | i ofa"))
		time.sleep(3)
		if status:
			break
	print 'Installation complete.'
	
	print '\nConfiguring OpenFlow logical switch ...'
	cisco.cli("conf t")
	cisco.cli("openflow")
	cisco.cli("switch 1")
	cisco.cli("pipeline 201")
	cisco.cli("controller ipv4 " + controller + " port 6633 vrf " + vrf + " security none")
	targets = expand(interfaces)
	for t in targets:
		print 'Adding interface %s ...' % t
		cisco.cli("of-port interface %s" % t)
	cisco.cli("end")
	# Interate back through interfaces to add pre-requisite configs
	cisco.cli("conf t")
	for t in targets:
		print 'Configuring interface %s for OpenFlow ...' % t
		cisco.cli("interface %s" % t)
		cisco.cli("switchport")
		cisco.cli("switchport mode trunk")
		cisco.cli("spanning-tree port type edge trunk")
	cisco.cli("end")

	print 'Configuration complete.'
	print 'Saving running-config to startup-config ...'
	cisco.cli("copy running-config startup-config")
	
	sys.stdout.write("Do you want to reload now? (y/n) ")
	sys.stdout.flush()
	reload = sys.stdin.readline().lower()
	if reload == 'yes' or reload == 'y':
		cisco.cli("reload")
	else:
		sys.exit()
	
if __name__ == '__main__':
	main()
