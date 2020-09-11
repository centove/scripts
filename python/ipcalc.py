#!/usr/bin/env python3
# ipcalc - calculate the networking info for a block. Handles both ipv4 and ipv6 addresses transparently.
#          it defaults to showing address space for a vrrp configured block.
import ipaddress
from ipaddress import AddressValueError
import argparse

def display_range (cidr):
    # this is so we can take any ip address in cidr notation and spit back the correct network info for it.
    # will handle having the host bits set in the passed in value and will re-try with the strict checking off
    # to get the proper network info. (ie 192.168.0.1/29 will give you the network 192.168.0.0/29 as one would expect)
    try:
        network = ipaddress.ip_network(cidr)
    except ValueError as e:
        try:
            network = ipaddress.ip_network(cidr, False)
        except ValueError as e:
            print ("{}".format( e))
            exit(-1)

    print ("Subnet   : {}".format(str(network)))
    print ("Network  : {}".format(network.network_address.exploded))
    print ("Broadcast: {}".format(network.broadcast_address.exploded))
    print ("Netmask  : {}".format(network.netmask.exploded))
    print ("Gateway  : {}".format(network.network_address + 1))
    print ("Usable   : {} - {} ({})".format(str(network.network_address +2), str(network.broadcast_address -3), network.num_addresses - 5))      
    print ("Reserved : {} - {}".format(str(network.broadcast_address - 2), str(network.broadcast_address - 1)))


parser = argparse.ArgumentParser(description='Display the networking info for a network block in a user freindly format')
parser.add_argument("cidr", help="The network cidr to display the info about")

args = parser.parse_args()
display_range(args.cidr)
