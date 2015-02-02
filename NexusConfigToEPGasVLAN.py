#!/usr/bin/env python
#
# This script will accept a Nexus 7000 configuration containing multiple
# L3 VLAN interfaces and their associated configuration, and migrate that
# to ACI network centric policy configuration along with the required
# attachable entity profiles, and leaf static attachment policies.
# Note that this script should be run on a greenfield fabric, due to risk
# of creating overlapping policies with existing switch/interface selectors
# For more support, please contact Cisco Advanced Services
#
# palesiak@cisco.com
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

import logging
import urllib
import cobra.mit.access
import cobra.mit.session
import cobra.mit.request
import cobra.model.fv
import cobra.model.pol
import cobra.model.infra
from cobra.internal.codec.xmlcodec import toXMLStr
import ConfigParser
import argparse
import StringIO
import textfsm

try:
    import requests.packages.urllib3
    requests.packages.urllib3.disable_warnings()
except:
    pass


class EPGasVLAN(object):

    """Class that will accept various vlan and leaf ranges, and 
    configure an APIC to make the vlans available on these leafs making
    simple EPGs that are identified by the VLAN, following a network-
    centric approach to leveraging the ACI fabric. Sample invocation:

    moDir = cobra.mit.access.MoDirectory(
        cobra.mit.session.LoginSession(apicUri, apicUser, apicPassword))

    easv = EPGasVLAN(md=moDir, verifyleaf=False)

    nodes = [101, 102]
    vlans = [
        (100, '10.0.100.1/24'),
        (200, '10.0.200.1/24'),
        (201, '10.0.201.1/24'),
        (202, '10.0.202.1/24')
    ]
    easv.createVlans('epgasvlan', vlans, nodes)
    """

    def __init__(self, md=None, verifyleaf=True):
        """Constructor accepts two parameters:

        md is the cobra.mit.access.MoDirectory object specifying the
        session that will be used for issuing queries and commits

        verifyleaf is a boolean that when set to True, will attempt
        to lookup a leaf node ID before using it in node attach
        statement. if set to false, the Dn for the leaf will be 
        auto-generated based on the dn naming properties.
        """
        self.md = md
        self.verifyleaf = verifyleaf
        if self.md:
            md.login()
        pass

    def setMd(self, md):
        self.md = md
        self.md.login()

    def createVlanInstances(self, vlans, nodes):
        """Creates the VLAN pools, AEP and port/leaf selector policies
        necessary to attach the EPG to the leafs within the application
        profile. If you run into nwissues class exceptions, you likely
        didn't run this

        vlans is list of ranges, defined as either a single entry for a
        single vlan or a range defined as a list [fromvlan, tovlan] that
        contains the list of vlans that should be configured in the vlan
        pool
        for example:
            vlans = [1, 2, [5, 10]]
        would create vlans 1, 2, 5, 6, 7, 8, 9, 10

        nodes is a list of leaf node ids will have available to them the
        list of vlans configured. this can be defined similarly to the
        vlan range, with single entries or list entries for ranges
        """
        topMo = cobra.model.pol.Uni('')
        infraInfra = cobra.model.infra.Infra(topMo)

        physDomP = self.md.lookupByClass(
            'physDomP', propFilter='eq(physDomP.name,"phys")')[0]

        # associate default AEP with phys domain
        infraAttEntityP = cobra.model.infra.AttEntityP(
            infraInfra, name='EPGasVLAN')
        cobra.model.infra.RsDomP(infraAttEntityP, tDn=physDomP.dn)

        # create VLAN pool
        fvnsVlanInstP = cobra.model.fvns.VlanInstP(
            infraInfra, name='EPGasVLAN', allocMode='static')
        for i, vlan in enumerate(vlans):
            if isinstance(vlan, list):
                fromvlan, tovlan = vlan
            else:
                fromvlan, tovlan = vlan, vlan
            fvnsEncapBlk = cobra.model.fvns.EncapBlk(
                fvnsVlanInstP, from_='vlan-{0}'.format(fromvlan), 
                to='vlan-{0}'.format(tovlan), name='encap{0}'.format(i))
        # create interface selector, switch selector and associate with the
        # switch nodes
        infraFuncP = cobra.model.infra.FuncP(infraInfra, name='default')
        infraAccPortGrp = cobra.model.infra.AccPortGrp(
            infraFuncP, name='EPGasVLAN')
        infraRsAttEntP = cobra.model.infra.RsAttEntP(
            infraAccPortGrp, tDn=infraAttEntityP.dn)
        infraAccPortP = cobra.model.infra.AccPortP(infraInfra, name='EPGasVLAN')
        infraHPortS = cobra.model.infra.HPortS(
            infraAccPortP, name='EPGasVLAN', type='ALL')
        infraRsAccBaseGrp = cobra.model.infra.RsAccBaseGrp(
            infraHPortS, tDn=infraAccPortGrp.dn)
        infraNodeP = cobra.model.infra.NodeP(infraInfra, name='EPGasVLAN')
        infraLeafS = cobra.model.infra.LeafS(
            infraNodeP, type='range', name='EPGasVLAN')
        for i, nodeblk in enumerate(self.collapseRange(nodes)):
            if isinstance(nodeblk, list):
                fromleaf, toleaf = nodeblk
            else:
                fromleaf, toleaf = nodeblk, nodeblk
            infraNodeBlk = cobra.model.infra.NodeBlk(
                infraLeafS, from_=fromleaf, to_=toleaf, 
                name='block{0}'.format(i))
        infraRsAccPortP = cobra.model.infra.RsAccPortP(
            infraNodeP, tDn='uni/infra/accportprof-EPGasVLAN')

        c = cobra.mit.request.ConfigRequest()
        logging.debug(toXMLStr(infraInfra))
        c.addMo(infraInfra)
        self.md.commit(c)

        # associate physical domain with VLAN pool
        infraRsVlanNs = cobra.model.infra.RsVlanNs(
            physDomP, tDn=fvnsVlanInstP.dn)
        c = cobra.mit.request.ConfigRequest()
        logging.debug(toXMLStr(physDomP))
        c.addMo(physDomP)
        self.md.commit(c)

        return vlans

    def createEPGasVLANTenant(self, tenant, vlans, nodes):
        vlanlist = []
        successfulnodes = []
        leafDn = {}
        physDomP = self.md.lookupByClass(
            'physDomP', propFilter='eq(physDomP.name,"phys")')[0]
        topMo = cobra.model.pol.Uni('')
        fvTenant = cobra.model.fv.Tenant(topMo, name=tenant)
        fvCtx = cobra.model.fv.Ctx(
            fvTenant, name=tenant, pcEnfPref='unenforced')
        fvAp = cobra.model.fv.Ap(fvTenant, name='EPG-as-VLAN')

        for v in vlans:
            vlan, ip = v
            kwargs = {'descr': urllib.quote('{0}'.format(ip))}

            vlanlist.append(vlan)
            fvAEPg = cobra.model.fv.AEPg(
                fvAp, name='vlan{0}'.format(vlan), **kwargs)
            fvRsDomAtt = cobra.model.fv.RsDomAtt(fvAEPg, tDn=physDomP.dn)
            fvBD = cobra.model.fv.BD(
                fvTenant, name='vlan{0}'.format(vlan), **kwargs)
            fvSubnet = cobra.model.fv.Subnet(fvBD, ip=ip)
            fvRsCtx = cobra.model.fv.RsCtx(fvBD, tnFvCtxName=fvCtx.name)
            fvRsBd = cobra.model.fv.RsBd(fvAEPg, tnFvBDName=fvBD.name)
            for leaf in map(str, nodes):
                if self.verifyleaf:
                    if leafDn.get(leaf):
                        leafMo = leafDn.get(leaf)
                    else:
                        leafMo = self.md.lookupByClass(
                            'fabricNode', 
                            propFilter='eq(fabricNode.id,"{0}")'.format(leaf))
                        if len(leafMo) > 0 and leafMo[0].role != 'leaf':
                            print 'Cannot apply EPG policy to non-leaf switch {0} ({1})'.format(leaf, leafMo[0].role)
                            leafMoDn = None
                            leafDn[leaf] = None
                        elif len(leafMo) > 0:
                            leafMo = leafMo[0]
                            leafMoDn = leafMo.dn
                            leafDn[leaf] = leafMo
                        else:
                            print 'Unable to find leaf {0}. Skipping it'.format(leaf)
                            leafMoDn = None
                            leafDn[leaf] = None
                else:
                    leafMoDn = 'topology/pod-1/node-{0}'.format(leaf)

                if leafMoDn:
                    if leafMoDn not in successfulnodes:
                        successfulnodes.append(leafMoDn)
                    fvRsNodeAtt = cobra.model.fv.RsNodeAtt(
                        fvAEPg, tDn=leafMoDn, encap='vlan-{0}'.format(vlan))

        successfulvlans = self.createVlanInstances(self.collapseRange(vlanlist), nodes)
        return fvTenant, successfulnodes, successfulvlans

    def createVlans(self, tenant, vlantuples, nodes):
        fvTenant, successfulnodes, successfulvlans = self.createEPGasVLANTenant(tenant, vlantuples, nodes)
        c = cobra.mit.request.ConfigRequest()
        logging.debug(toXMLStr(fvTenant))
        c.addMo(fvTenant)
        self.md.commit(c)
        return fvTenant, successfulnodes, successfulvlans

    def collapseRange(self, expandedlist):
        addrange = lambda l, a, b: l.append(
            a) if a == b else l.append(sorted([a, b]))
        results = []
        for i in sorted(set(expandedlist)):
            try:
                if i - last > 1:
                    addrange(results, startrange, last)
                    startrange = i
            except NameError:
                startrange = i
            last = i
        addrange(results, startrange, last)
        return results


class NxosConfig(object):

    sourcefile = ''
    svi_parser = '''#parse vlans
Value Key,Required vlan ([0-9]+)
Value Required ip_address ([0-9.\/]+)
Value description (.+)

Start
  ^\s*interface [vV]lan\s*${vlan} -> Continue
  ^\s*description\s+${description} -> Continue
  ^\s*ip address\s+${ip_address} -> Record
'''

    def __init__(self, sourcefile):
        self.sourcefile = sourcefile

    def getVlanIP(self):
        results = []
        svi_parser_handle = StringIO.StringIO(self.svi_parser)
        svi_template = textfsm.TextFSM(svi_parser_handle)

        svi_dump = open(self.sourcefile, 'r').read()
        with open(self.sourcefile, 'r') as f:
            svi_dump = f.read()

            svi_output = svi_template.ParseText(svi_dump)
            for h in svi_output:
                ip = h[svi_template.header.index('ip_address')]
                vlan = int(h[svi_template.header.index('vlan')])
                results.append([vlan, ip])

        return results


def expandRange(s):
    """expand a text range that defines a range of integers using commas
    and dashes into a list
    """
    o = []
    if ',' in s:
        for c in s.split(','):
            o.extend(expandRange(c))
    elif '-' in s:
        r = s.split('-')
        o = range(int(r[0]), int(r[1]) + 1)
    else:
        o = [int(s)]
    return o

def main():
    parser = argparse.ArgumentParser(description='Process input filename')
    parser.add_argument(
        '-config', required=True, help='NXOS configuration containing SVIs to be converted to EPG')
    parser.add_argument('-uri', required=True, help='URI of APIC (e.g., https://apic.cisco.com')
    parser.add_argument('-username', required=True, help='Username for APIC')
    parser.add_argument('-password', required=True, help='Password for APIC')
    parser.add_argument('-leafs', required=True, help='Comma separated list of leaf nodes to include attach EPGs')
    parser.add_argument('-tenant', required=True, help='Tenant name')
    parser.add_argument('-debug', default=False, action='store_true')


    args = parser.parse_args()

    apicUri = args.uri
    apicUser = args.username
    apicPassword = args.password
    nodes = args.leafs

    if args.debug:
        logging.basicConfig(format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)

    nodes = map(int, expandRange(nodes))

    print 'Parsing {0}'.format(args.config)
    nxosConf = NxosConfig(args.config)
    nxosVlanInts = nxosConf.getVlanIP()
    if len(nxosVlanInts) > 0:
        print 'Found {0} VLANs in configuration'.format(len(nxosVlanInts))
        vlans = []
        for svi in nxosVlanInts:
            vlans.append(tuple(svi))

        print 'Logging into APIC {0}'.format(apicUri)
        moDir = cobra.mit.access.MoDirectory(
            cobra.mit.session.LoginSession(apicUri, apicUser, apicPassword))
        easv = EPGasVLAN(md=moDir)
        print 'Creating EPGs'
        tenant,successfulnodes,successfulvlans = easv.createVlans(args.tenant, vlans, nodes)
        print 'Created:'
        print '  Tenant:    {0}'.format(args.tenant)
        print '  VLANS:     {0}'.format(', '.join([str(vlan) for vlan in successfulvlans]))
        print '  on Nodes:  {0}'.format(', '.join([str(node) for node in successfulnodes]))
    else:
        print 'No parsable SVI configuration found'


if __name__ == "__main__":
    main()
