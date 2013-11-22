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

# This script will accept as a parameter an IP or range of IP address
# and attempt to ping them all from the switch it is running on
# Ranges can be specified in any octet, e.g., 
# python pingrange.py 10.1.0-1.0-255 will ping 10.1.0.0/23
#
# 
import re
from cisco import *
from argparse import ArgumentParser

def expandrange(rnge):
	''' Take an octet passed to the function, which may be in the format
	of a single integer, or N-M. If it's a single octet, just return it 
	as a list. If it's a range, return a list containing the range of those IPs.
	'''
	if '-' in rnge:
		r = rnge.split('-')
		return range(int(r[0]), int(r[1])+1)
	else:
		return [rnge]

# Parse some arguments passed to the script, notably the IP and the options parameter
# If you don't specify the options, it defaults to just doing a single count
# Note that these options are the same as if you were to type "ping ?" at the NXOS cli
parser = ArgumentParser('pingrange')
parser.add_argument('ip')
parser.add_argument('-o', '--options', help='Options to pass to ping, default: count 1', default='count 1')
args = parser.parse_args()
target = args.ip

# Now we do some simple octet splitting, with not much verification
# Break up the IP by the . and then apply the expandrange command to those
# so that a user can specify a range at any point in the IP
# This is very similar to how nmap supports ranges, with exception to commas
octets = target.split('.')
for o1 in expandrange(octets[0]):
	for o2 in expandrange(octets[1]):
		for o3 in expandrange(octets[2]):
			for o4 in expandrange(octets[3]):
				# At this point we build the IP from whatever our loops have found
				# and then we can execute the ping command on that IP with some options
				ip = '%d.%d.%d.%d' % (int(o1),int(o2),int(o3),int(o4))
				print('%s - ' % ip),
				# We extract the packet loss from the output, however you can extract whatever output you'd like
				# As long as you build the right regular expression for it. Play around with it and tweak it to your needs!
				m = re.search('([0-9\.]+% packet loss)', cli('ping %s %s' % (ip, args.options))[1])
				# the first group returned by re.search is the first matching regex within parenthesis
				print m.group(0)
