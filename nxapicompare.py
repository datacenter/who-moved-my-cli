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
# This script requires NXAPITransport and the cisco remote access libraries
# These are available from Cisco Dev Net at https://developer.cisco.com/web/n9k/downloads
# Under the Downloads section named nx-os-remote-client.tgz
# Once downloaded, unpack these and place this script in the same directory as the 
# 'cisco' and 'utils' directories
#
# 
# This script uses the NXAPI remote API to query a list of Nexus 9000 devices, issuing the same
# command on each of them, and then comparing the results with each other
# Any values that do not match between the first switch in the list and any other
# will be printed in a tabular form
#
# Note: due to differences in the way data is returned for different commands, the comparison
# logic below may need to be modified, to look at different tiers.
#

import sys
import pprint
import json
sys.path.append("./cisco")
sys.path.append("./utils")

from nxapi_utils import NXAPITransport 
from cisco.interface import Interface

switches = [ ['172.23.3.116', 'admin', 'insieme'], 
			['172.23.3.117', 'admin', 'insieme']]

results = []
for switch in switches:
	target_url = "http://%s/ins" % switch[0]
	username = switch[1]
	password = switch[2]
	NXAPITransport.init(target_url=target_url, username=username, password=password)
	results.append(json.loads(NXAPITransport.clid("show version")))

switchlist = [r['host_name'] for r in results]

fmt = "{:>45}" * (len(switchlist) + 1)
print fmt.format("", *switchlist)

for k,v in results[0].items():
	values = []
	for i,r in enumerate(results[1:]):
		values.append(v)
		mismatch = False
		if k in r:
			values.append(r[k])
			if r[k] != v: mismatch = True
		if mismatch is True: print fmt.format(k, *values)
