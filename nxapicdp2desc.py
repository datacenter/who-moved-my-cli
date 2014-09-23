#!/usr/bin/env python
#
# Copyright (C) 2014 Cisco Systems Inc.
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
# This script demonstrates how you can write a single script that runs on both
# on box and off box, using the same APIs on Nexus 9000.
#
# The workflow will gather details from the CDP database and generate
# interface descriptions based on the neighbor name and remote interface
# and then print out the configuration needed to apply these descriptions.
# This version executes via the NX-API, and will simply print out the 
# generated configuration output, as opposed to applying it
#

# Define your list of switches here, with their IP addresses and credentials
switches = [
    ['10.0.0.1', 'admin', 'cisco'],
]


import sys
import pprint
import json
sys.path.append("./cisco")
sys.path.append("./utils")

onbox = True
try:
    from cli import clid, cli
except ImportError:
    try:
        from nxapi_utils import NXAPITransport
        from cisco.interface import Interface
        onbox = False
    except ImportError:
        print 'Script is unsupported on this platform'
        raise

def findkey(dct, key, value=None):
    """This method recursively searches through a JSON dict for a key name
    and returns a list of the matching results
    """
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

for switch in switches:
    cdp_dict = {}
    if not onbox:
        target_url = "http://%s/ins" % switch[0]
        username = switch[1]
        password = switch[2]
        NXAPITransport.init(
            target_url=target_url, username=username, password=password)

        def smartcli(*args):
            """This wrapper function provides a less intrusive way to call the
            appropriate msg_type for configuration based commands
            """
            cmd = args[0]
            if cmd[:4] == 'conf':
                NXAPITransport.send_cmd(cmd, msg_type='cli_conf')
            else:
                NXAPITransport.cli(cmd)
        cli = smartcli
        clid = NXAPITransport.clid

    cdp_dict = {}

    cdp = json.loads(clid('show cdp neighbor'))
    cdp = findkey(cdp, 'ROW_cdp_neighbor_brief_info')[0]
    for entry in cdp:
        intf_id = entry['intf_id']
        if intf_id not in cdp_dict:
            cdp_dict[intf_id] = {
                'intf_id': intf_id,
                'device_id': entry['device_id'],
                'port_id': entry['port_id']
            }

    for key, value in cdp_dict.items():
        if 'port_id' in value and 'device_id' in value and 'intf_id' in value:
            fields = {
                'interface': value['intf_id'].strip().encode('UTF-8'),
                'device_id': value['device_id'].strip().encode('UTF-8'),
                'port_id': value['port_id'].strip().encode('UTF-8')
            }
            cmd = 'conf t ; interface {interface} ; description {device_id} {port_id}'.format(
                **fields)
            print(cmd)
            cli(cmd)
