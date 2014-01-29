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
# This script implements the BaseHTTPServer class available within Python
# and displays a status page on your Nexus 9000 running on port 8081.
#
# This sample displays the route that is used to reach the device contacting
# the web server, and also displays the ping latency to the host
#

import cli
import json
import re
import BaseHTTPServer

class Route():

    def printroute(self, j, d=0):
        o = ''
        whitelist = ['vrf-name-out', 'addrf', 'ipprefix', 'ucast-nhops', 'mcast-nhops', 'attached', 'uptime', 'pref', 'metric', 'clientname', 'ubest']
        if isinstance(j, list):
            for i in j:
                o += self.printroute(i, d + 1)
        else:
            for k, v in j.items():
                if k in whitelist:
                    o += '%s %s: %s\n' % ('-' * d, k, v)
                if isinstance(v, dict) or isinstance(v, list):
                    o += self.printroute(v, d + 1)
        return o

    def title(self):
        return 'Route to your IP'

    def data(self, **kwargs):
        s = kwargs['s']
        ip = s.client_address[0]
        r = json.loads(cli.clid('show ip route %s vrf management' % ip))
        return self.printroute(r)

class Latency():

    def title(self):
        return 'Latency to your IP'

    def data(self, **kwargs):
        s = kwargs['s']
        ip = s.client_address[0]
        a = ''.join(cli.cli('ping %s vrf management count 1' % ip).split('\n'))
        m = re.match('.*time=([0-9\.]+).*', a)
        return float(m.group(1))

def HTMLBuilder():
    return '''
<html>
    <head>
        <title>Nexus 9000</title>
        <script type="text/javascript" src="https://www.google.com/jsapi"></script>
        <script src="//ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js"></script>
        <script type="text/javascript" language="javascript">

        google.load("visualization", "1", {packages:["corechart"]});
        google.setOnLoadCallback(drawChart);

        function drawChart() {

            var options = {
              title: 'Latency',
              curveType: 'function',
              legend: { position: 'bottom' }
            };

            var chart = new google.visualization.LineChart(document.getElementById('chart_div'));

            chart.draw(google.visualization.arrayToDataTable(window.items), options);
        }

        $(document).ready(function() {
            window.items = [['Time', 'Latency'], [getTimeHHMMSS(), 0]];

            $.getJSON( "/route", function( data ) {
                $("#route_div").html('<p><pre>' + data + '</pre></p>');
            });

            fetchData();
        });
        function padInt(i) {
            if (i < 10) {
                i = "0" + i;
            }
            return i;
        }

        function getTimeHHMMSS() {
            var now = new Date();
            var h = now.getHours();
            var m = now.getMinutes();
            var s = now.getSeconds();
            m = padInt(m);
            s = padInt(s);
            return h + ":" + m + ":" + s;
        }

        function fetchData() {
            $.getJSON( "/latency", function( data ) {
                window.items.push( [getTimeHHMMSS(), data] );
            });
            // console.log(items);
            drawChart();
            if (window.items.length > 20) {
                window.items.splice(1, 1);
            }
            setTimeout(fetchData, 1000);
        }
        
        </script>
            </head>

   <body>
    <div id="chart_div" style="width: 800px; height: 400px;"></div>
    <div id="route_div" style="width: 800px; height: 100px; top: 500;">Route</div>
   </body>
 <html>
'''    
class httphandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_GET(s):
        s.send_response(200)
        s.send_header('Content-type', 'text/html')
        s.end_headers()
        if s.path == '/':
            s.wfile.write(HTMLBuilder())
        elif s.path == '/latency':
            lat = Latency().data(s=s)
            s.wfile.write(json.dumps(lat))
        elif s.path == '/route':
            rout = Route().data(s=s)
            s.wfile.write(json.dumps(rout))

if __name__ == '__main__':
    httpserver = BaseHTTPServer.HTTPServer

    httpd = httpserver(('0.0.0.0', 8081), httphandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
