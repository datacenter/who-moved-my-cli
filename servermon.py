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
# This script is a simple server monitor that can be run from a Nexus switch
# which will monitor an L4 port to see if it actively accepts connections on
# a server. If the connection fails to be established, the commands specified
# will be executed
#

import socket
import time
from argparse import ArgumentParser
import nxos
import cli

parser = ArgumentParser('Server health monitor')
parser.add_argument('-s', '--server', help='IP address of server to monitor', required=True)
parser.add_argument('-p', '--port', help='TCP port to poll', type=int, required=True)
parser.add_argument('cmd', nargs='+', help='Commands to run if an interface fails, use , to separate multiple commands')
args = parser.parse_args()
connected = False
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((socket.gethostbyname(args.server), int(args.port)))
    sock.close()
    connected = True
except socket.error:
    connected = False
if connected == False:
    nxos.py_syslog(1, 'The server %s failed on port %s at time %s. Debug output below:' % (args.server, args.port, time.asctime()))
    for cmd in ' '.join(args.cmd).split(','):
        nxos.py_syslog(1, cli.cli(cmd))
