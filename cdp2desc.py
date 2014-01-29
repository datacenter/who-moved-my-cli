# palesiak@cisco.com
cdp_dict = {}
for key,value in clid('show cdp neighbor').items():
    fields = key.split('/')
    if fields[2] in cdp_dict:
        cdp_dict[fields[2]][fields[1]] = value
    else:
        cdp_dict[fields[2]] = { fields[1]: value }

for key,value in cdp_dict.items():
    if 'port_id' in value and 'device_id' in value and 'intf_id' in value:
        print 'interface ' + value['intf_id']
        print 'this is a question mark?'
        print '  description ' + value['device_id'] + ' ' + value['port_id']
