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
# # term len 0
# # source easy-ofa.py <package>
# 			   - or -
# # term len 0
# # python bootflash:easy-ofa.py <package>
# 
# Additional help is available using the --help option.
#

import argparse
import os
import re
import socket
import sys
import time

import cisco

supported = [
    "Nexus3016", "Nexus3064", "Nexus3048", "Nexus3132", "Nexus5548", 
    "Nexus5596", "Nexus 6001", "Nexus 6004"
    ]

# Handle cisco.cli() type inconsistencies
def make_cli_wrapper(f):
    if type(f("show clock")) is tuple:
        def cli_wrapper(*args, **kwargs):
            return f(*args, **kwargs)[1]
        return cli_wrapper
    return f

cli = make_cli_wrapper(cisco.cli)

# Prevent print() buffering when connected via tty
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

def max_flows(platform):
    print "Tuning switch TCAM for max flows ..."
    if (platform == "Nexus 6001" or platform == "Nexus 6004"):
        cli("conf t")
        cli("hardware profile tcam resource template vacl 0")
        cli("hardware profile tcam resource template ifacl 3520")
        cli("hardware profile tcam resource template e-vacl 0")
        cli("hardware profile tcam resource template rbacl 0")
        cli("hardware profile tcam resource template qos 128")
        cli("hardware profile tcam resource template span 64")
        cli("end")
    elif (platform == "Nexus3016" or platform == "Nexus3064" or 
            platform == "Nexus3048" or platform == "Nexus3132"):
        cli("conf t")
        cli("hardware profile tcam region vacl 0")
        cli("hardware profile tcam region e-vacl 0")
        cli("hardware profile tcam region racl 0")
        cli("hardware profile tcam region e-racl 0")
        cli("hardware profile tcam region qos 0")
        cli("hardware profile tcam region ifacl 1644")
        cli("end")
    else:
        print "TCAM tuning not supported, bypassing ..."

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

def af_check(ip):
    try:
        socket.inet_pton(socket.AF_INET, ip)
    except socket.error:
        return False
    else:
        return True
    
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("package", help = 
                        "OpenFlow Plug-in OVA package to install")
    parser.add_argument("-m", "--maxflows", help = 
                        "Tune switch TCAM to support maximum number of flows",
                        required = False, action = "store_true")
    args = parser.parse_args()

    ver = cli("show version")
    platform = re.search(r"(Hardware\s*cisco\s)(.*)(?=\sC)", ver).group(2)
    if platform not in supported:
        print "ERROR: Unsupported hardware platform. Exiting ..."
        sys.exit(1)

    if args.maxflows:
        max_flows(platform)

    # raw_input() doesn't work reliably across all platforms, so ...
    sys.stdout.write("Interfaces (seperated by space) to use for OpenFlow: ")
    interfaces = sys.stdin.readline()

    sys.stdout.write("Enter the OpenFlow controller IP address: ")
    controller = sys.stdin.readline().rstrip('\n')
    while not af_check(controller):
        print '\nERROR: Invalid IP address.  Please enter a valid IPv4 address ...'
        sys.stdout.write("Enter the OpenFlow controller IP address: ")
        controller = sys.stdin.readline().rstrip('\n')

    sys.stdout.write("Enter vrf (If no input, vrf 'default' is used): ")
    vrf = sys.stdin.readline().rstrip('\n')
    if not vrf:
        vrf = "default"

    print "\nEnabling OpenFlow hardware profile ..."
    cli("conf t")
    cli("hardware profile openflow")
    cli("end")

    print "Installing Cisco Plug-in for OpenFlow ..."
    cli("virtual-service install name ofa package bootflash:" + args.package)
    while True:
        status = re.search(r"ofa\s*Installed", 
                            cli("show virtual-service list | i ofa"))
        time.sleep(3)
        if status:
            break

    print "Activating Cisco Plug-in for OpenFlow ..."
    cli("conf t")
    cli("virtual-service ofa")
    cli("activate")
    cli("end")
    while True:
        status = re.search(r"ofa\s*Activated", 
                            cli("show virtual-service list | i ofa"))
        time.sleep(3)
        if status:
            break
    print "Installation complete."

    print "\nConfiguring OpenFlow logical switch ..."
    cli("conf t")
    cli("openflow")
    cli("switch 1")
    cli("pipeline 201")
    cli("controller ipv4 " + controller + " port 6633 vrf " + vrf + 
        " security none")
    targets = expand(interfaces)
    for t in targets:
        print "Adding interface %s ..." % t
        cli("of-port interface %s" % t)
    cli("end")
    # Interate back through interfaces to add pre-requisite configs
    cli("conf t")
    for t in targets:
        print "Configuring interface %s for OpenFlow ..." % t
        cli("interface %s" % t)
        cli("switchport")
        cli("switchport mode trunk")
        cli("spanning-tree port type edge trunk")
    cli("end")

    print "Configuration complete."
    print "Saving running-config to startup-config ..."
    cli("copy running-config startup-config")

    sys.stdout.write("Do you want to reload now? (y/n) ")
    reload = sys.stdin.readline().lower()
    if reload == "yes" or reload == "y":
        cli("reload")
    else:
        sys.exit()

if __name__ == "__main__":
    main()
