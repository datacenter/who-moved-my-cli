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
# This script will gather details from the CDP database and generate
# interface descriptions based on the neighbor name and remote interface
# and then print out the configuration needed to apply these descriptions.
#


import cli
import json

cdp_dict = {}

cdp = json.loads(cli.clid('show cdp neighbor'))[
    'TABLE_cdp_neighbor_brief_info']['ROW_cdp_neighbor_brief_info']
for entry in cdp:
    intf_id = entry['intf_id']
    if intf_id not in cdp_dict:
        cdp_dict[intf_id] = {}
    cdp_dict[intf_id]['intf_id'] = intf_id
    cdp_dict[intf_id]['device_id'] = entry['device_id']
    cdp_dict[intf_id]['port_id'] = entry['port_id']

for key, value in cdp_dict.items():
    if 'port_id' in value and 'device_id' in value and 'intf_id' in value:
        cli.cli('conf t ; interface ' + value[
                'intf_id'] + ' ; description ' + value['device_id'] + ' ' + value['port_id'])
