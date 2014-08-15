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
# The logic here can be extended to include additional commands, and introduce
# branching logic to handle different situations. An example may be to treat a
# host that appears in the CDP table differently from one that does not, and
# collect a other command outputs in that case
#
# Tested and validated on Nexus 9000 6.1(2)I2(2a)
#
# A best effort was also made to try to run it on other platforms, but was only
# tested on Nexus 5000 5.2(1)N1(6)
#
# For Nexus 5000 support, this depends on xmltodict
#   https://github.com/martinblech/xmltodict/blob/master/xmltodict.py
#
#
import re
import pprint
import json
from argparse import ArgumentParser

#
# This entire block of code is aimed at detecting of we have access to cli and
# the clid command. If we do not have them, we attempt to import cli from the
# cisco package (which is present on other NXOS platforms). If that fails, we
# cannot proceed further. However, if it does succeed, then we need to create
# an equivalent of clid(), so we introduce an external dependency on xmltodict
# which is used to convert the XML output of the commands into a JSON dict.
#
# Finally, after that we check to see if cli() returns a tuple, if so that means
# we are on a 5K or similar, and we need to patch the output to return it as
# just the command output, and not the two-tuple


class UnstructuredOutput(Exception):
    pass

try:
    from cli import clid, cli
except ImportError:
    try:
        from cisco import cli
    except ImportError:
        print 'Script is unsupported on this platform'
        raise

    def clid(cmd):
        try:
            import xmltodict
        except ImportError:
            print 'Script is unsupported on this platform: requires xmltodict'
            raise
        tag = '__readonly__'
        starttag, endtag = '<' + tag + '>', '</' + tag + '>'
        output = cli('{0} | xml'.format(cmd))
        start_index, end_index = output.find(starttag), output.find(endtag)
        if start_index == -1 or end_index == -1:
            raise UnstructuredOutput(
                'Command {0} does not support structured output: {1}'.format(
                    cmd, output))
        output = xmltodict.parse(
            output[start_index:end_index + len(endtag)])
        json_output = json.dumps(output[tag])
        return json_output


def cli_decorator(target_function):
    def wrapper(cmd):
        return target_function(cmd)[1]
    return wrapper

if isinstance(cli('show version'), tuple):
    cli = cli_decorator(cli)


def findkey(dct, key, value=None):
    found = []
    if isinstance(dct, list):
        for item in dct:
            f = findkey(item, key, value)
            if f:
                found.extend(f)
    if isinstance(dct, dict):
        for k, v in dct.items():
            if isinstance(v, list) or isinstance(v, dict):
                f = findkey(v, key, value)
                if f:
                    found.extend(f)
            if str(k) == str(key):
                if (value and str(v) == str(value)) or not value:
                    found.append(v)
    return found if len(found) > 0 else None


def getarpentry(ip=None, vrf='all'):
    # Check the output of the ARP table for the IP address in question
    if ip:
        arpoutput = json.loads(clid('show ip arp {0} vrf {1}'.format(ip, vrf)))
    else:
        arpoutput = json.loads(clid('show ip arp vrf {0}'.format(vrf)))
    rowadjlist = findkey(arpoutput, 'ROW_adj')
    if not rowadjlist:
        return None

    # flatten out the data received from show ip arp into a list of dicts
    arpentries = []
    for rowadj in rowadjlist:
        if isinstance(rowadj, dict):
            arpentries.append(rowadj)
        elif isinstance(rowadj, list):
            arpentries.extend(rowadj)

    arplist = []
    for arp in arpentries:
        try:
            arplist.append(
                [arp['ip-addr-out'], arp['time-stamp'], arp['mac'], arp['intf-out']])
        except KeyError:
            continue
    return arplist


def getmacentry(mac, vlanfilter=None):
    try:
        macaddroutput = json.loads(
            clid('show mac address-table address {0}'.format(mac)))
    except UnstructuredOutput:
        return None

    macaddrlist = findkey(macaddroutput, 'ROW_mac_address')
    if not macaddrlist:
        return None

    macentries = []
    for macaddr in macaddrlist:
        if isinstance(macaddr, dict):
            macentries.append(macaddr)
        elif isinstance(macaddr, list):
            macentries.extend(macaddr)

    entries = []
    for macaddr in macentries:
        vlan = macaddr['disp_vlan']
        mac = macaddr['disp_mac_addr']
        entrytype = macaddr['disp_type']
        age = macaddr['disp_age']
        secure = macaddr['disp_is_secure']
        ntfy = macaddr['disp_is_ntfy']
        port = macaddr['disp_port']

        if vlanfilter and vlan != vlanfilter:
            continue

        # If a MAC is on a port channel, dereference it and use the first entry
        if 'po' in port.lower():
            members = getportchannelmembers(port)
            if not members:
                raise Exception(
                    'Unable to find any member interfaces in {0}'.format(port))

            entries.extend(
                [[vlan, mac, entrytype, age, secure, ntfy, memberport,
                    port] for memberport in members])
        elif 'vlan' in port.lower():
            continue
        else:
            entries.append(
                [vlan, mac, entrytype, age, secure, ntfy, port, port])

    return entries


def getportchannelmembers(port):
    po = json.loads(
        clid('show port-channel summary int {0}'.format(port)))
    members = findkey(po, 'port')
    return members


def getcdpentry(port):
    # Next use the interface we found the device on from CAM and look it up in
    # CDP
    cdp = json.loads(clid('show cdp neighbor interface {0}'.format(port)))
    cdp = findkey(cdp, 'ROW_cdp_neighbor_brief_info')
    if not cdp:
        raise Exception('Unable to find {0} in CDP output'.format(port))
    if len(cdp) > 0:
        cdp = cdp[0]
    return cdp


def main():

    # Perform some basic argument parsing for parameters passed to the script
    parser = ArgumentParser('Supercommand')
    parser.add_argument(
        'ip', help='IP address to query. Use all for every IP in arp')
    args = parser.parse_args()
    ip = args.ip

    output = []

    try:
        if ip == 'all':
            arpentries = getarpentry()
        else:
            arpentries = getarpentry(ip)
        if not arpentries:
            print 'Unable to find {0} in ARP table'.format(ip)
            arpentries = []

        for arp in arpentries:
            depth = 2
            ip, timer, mac, interface = arp
            output += ['Here is some information on {0}:'.format(ip)]
            if len(arpentries) > 1:
                output += [' ' * depth + 'ARP entry on {0}'.format(interface)]
                depth = 4
            output += [' ' * depth + 'MAC address: {0}'.format(mac)]
            output += [' ' * depth + 'L3 gateway: {0}'.format(interface)]
            if 'Vlan' in interface:
                vlanfilter = interface.split('Vlan')[1]
            else:
                vlanfilter = None
            macentries = getmacentry(mac, vlanfilter=vlanfilter)
            if not macentries:
                print 'Unable to find {0} in MAC table'.format(mac)
                macentries = []

            topdepth = depth
            for macentry in macentries:
                depth = topdepth
                vlan, mac, entrytype, age, secure, ntfy, port, parentport = macentry
                if len(macentries) > 1:
                    output += [' ' * depth +
                               'Port Channel {0} member {1}'.format(parentport, port)]
                    depth += 2
                output += [' ' * depth + 'Local interface: {0}'.format(port)]
                output += [' ' * depth + 'VLAN: {0}'.format(vlan)]
                cdp = getcdpentry(port)
                if cdp:
                    output += [' ' * depth +
                               'CDP Platform: {0}'.format(cdp['platform_id'])]
                    output += [' ' * depth +
                               'CDP Device ID: {0}'.format(cdp['device_id'])]
                    output += [' ' * depth +
                               'CDP Remote Port ID: {0}'.format(cdp['port_id'])]
    finally:
        print(chr(10).join(output))

if __name__ == '__main__':
    main()
