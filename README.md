who-moved-my-cli
================

The scripts contained in this directory are meant to help demonstrate to network
engineers how they can take common administrative tasks, and use Python to help
automate these tasks. 

Supported Hardware
----
Unless otherwise stated, all of these scripts are supported on Nexus 9000 and
have been tested with NXOS: version 7.0(3)I2(2). Running on other platforms may require
modification to the code.

Installation
----
Most of these scripts can be copied to bootflash: and executed using
```
python bootflash:script.py
````
There are also many other ways to invoke Python scripts on NX-OS, so it's 
suggested that you references Cisco Live presentation BRKDCT-1302 or review
the [Nexus 9000 documentation on CCO] for more information. 

Contributing
----
All users are strongly encouraged to contribute patches, new scripts or ideas.
Please submit a pull request with your contribution and we will review, provide
feedback to you and if everything looks good, we'll merge it!


Descriptions
----

| Script               | Description                                                                                                                                                                                                                                                                                                                | 
|----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| bcmnxosintcompare.py | Script demonstrating how to programmatically interface with the broadcom shell on a Nexus 9000 |
| cdp2desc.py          | Example of using the output of show cdp neighbors information, to create a configuration template populating the CDP neighbor in the interface description field |
| cdp2descv2.py        | Similar to cdp2desc.py, except this script configures the interface description to match the CDP output |
| easy-ofa.py          | This script installs and configures the Cisco Plug-in for OpenFlow. |
| httpserver.py        | Creates a simple web server in Python, that runs on a Nexus 9000 exposing a web interface displaying real time information on the switch | 
| interface_rate.py    | This script prints interface throughput/packet rate statistics in an easy to read list format on NX-OS platforms |
| nxapicdp2desc.py     | Using the NX-API interface, this script will create a configuration template to configure interface descriptions with CDP details |
| nxapicompare.py      | Remotely compare the outputs of commands on multiple Nexus switches running NX-API |
| pingrange.py         | Introduces an enhanced ping command that allows for a network administrator to ping an entire range of hosts from a switch |
| servermon.py         | Monitors the status of a TCP port on a host and then takes some action if the port stops responding |
| supercommand.py      | Command that chains together the output of show ip arp, show mac address table and show cdp neighbors to create a single "supercommand". Note: Supported on Nexus 9000, but best effort has been made to support Nexus 5000 and other platforms. This code may be useful to see examples of supporting multiple platforms. |

[Nexus 9000 documentation on CCO]:http://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/6-x/programmability/guide/b_Cisco_Nexus_9000_Series_NX-OS_Programmability_Guide/b_Cisco_Nexus_9000_Series_NX-OS_Programmability_Configuration_Guide_chapter_01.html
