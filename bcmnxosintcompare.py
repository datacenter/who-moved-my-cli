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
# This script performs an NX-OS to BCM T2 port mapping and then
# populates a dictionary with the interface properties available
# between the two OSs. Finally, it prints out the status of an interface
# as seen by the Broadcom shell, and as seen by NX-OS
#


import cli
import libbcmshell
import re
import pprint

intmap = {}
for line in cli.cli('show interface hardware-mappings').split('\n'):
    p = '^Eth(?P<mod>[0-9]+)\/(?P<interface>[0-9\/]+) +(?P<ifIndex>[a-z0-9]+) +(?P<Smod>[0-9]+) +(?P<Unit>[0-9]+) +(?P<HPort>[0-9]+) +(?P<FPort>[0-9]+) +(?P<NPort>[0-9]+) +(?P<VPort>[\-0-9]+)'
    r = re.match(p, line)
    if r is not None:
        if r.groupdict()['mod'] not in intmap:
            intmap[r.groupdict()['mod']] = []
        intmap[r.groupdict()['mod']].append(r.groupdict())


for line in cli.cli('show int brief').split('\n'):
    p = '^Eth(?P<mod>[0-9]+)\/(?P<interface>[0-9\/]+) +(?P<VLAN>[\-0-9]+) +(?P<type>eth) +(?P<Mode>[a-z]+) +(?P<Status>[a-z]+) +(?P<Reason>.+) +(?P<Speed>[a-zA-Z0-9]+\(.\)) +(?P<PortCh>[\-0-9]+)'
    r = re.match(p, line)
    if r is not None:
        if r.groupdict()['mod'] not in intmap:
            raise 'Found module in show brief that wasn\'t found in show interface hardware-mappings'
        for interface in intmap[r.groupdict()['mod']]:
            if interface['interface'] == r.groupdict()['interface']:
                for k, v in r.groupdict().items():
                    if k not in interface:
                        interface[k] = v


for mod, interfaces in intmap.items():
    bcmmap = {}
    bcmPortIndex = -1
    for interface in interfaces:
        bcmPortIndex += 1
        if interface['Unit'] not in bcmmap:
            bcmPortIndex = -1
            bcmmap[interface['Unit']] = []
            for line in libbcmshell.runBcmCmd(int(mod), int(interface['Unit']), 'ps').split('\n'):
                p = '^ +(?P<bcmPort>xe[0-9]+) +(?P<bcmEnalink>[\!a-z]+) +(?P<bcmSpeed>[0-9A-Z]+) +(?P<bcmDuplex>[A-Z]+) +(?P<bcmLinkScan>[A-Z]+) +(?P<bcmAutoNeg>Yes|No) +(?P<bcmSTPState>Forward|Disable) +(?P<bcmPause>[ TRX]+) +(?P<bcmDiscard>None) +(?P<bcmLrnOps>[A-Z]+) +(?P<bcmInterface>[A-Z0-9]+) +(?P<bcmMaxFrame>[0-9]+).*'
                r = re.match(p, line)
                if r is not None:
                    d = r.groupdict()
                    bcmmap[interface['Unit']].append(d)
        else:
            print 'found ' + interface['Unit']
        for k, v in bcmmap[interface['Unit']][bcmPortIndex].items():
            if k not in interface:
                interface[k] = v

for mod, interfaces in intmap.items():
    for interface in interfaces:
        print 'interface Eth%s/%s : BCM %s/%s/%s :: %s : %s' % (mod, interface['interface'], mod, interface['Unit'], interface['bcmPort'], interface['Status'], interface['bcmEnalink'])
