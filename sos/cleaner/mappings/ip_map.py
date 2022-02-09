# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import ipaddress
import random

from sos.cleaner.mappings import SoSMap


class SoSIPMap(SoSMap):
    """A mapping store for IP addresses

    Each IP address added to this map is chcked for subnet membership. If that
    subnet already exists in the map, then IP addresses are deterministically
    generated sequentially within that subnet. For example, if a given IP is
    matched to subnet 192.168.1.0/24 then 192.168.1 may be obfuscated to
    100.11.12.0/24. Each IP address in the original 192.168.1.0/24 subnet
    will then be assigned an address in 100.11.12.0/24 sequentially, such as
    100.11.12.1, 100.11.12.2, etc...


    Internally, the ipaddress library is used to manipulate the address objects
    however, when retrieved by SoSCleaner any values will be strings.
    """

    ignore_matches = [
        r'127.*',
        r'::1',
        r'0\.(.*)?',
        r'1\.(.*)?',
        r'8.8.8.8',
        r'8.8.4.4',
        r'169.254.*',
        r'255.*'
    ]

    _networks = {}
    network_first_octet = 100
    skip_network_octets = ['127', '169', '172', '192']
    compile_regexes = False

    def ip_in_dataset(self, ipaddr):
        """There are multiple ways in which an ip address could be handed to us
        in a way where we're matching against a previously obfuscated address.

        Here, match the ip address to any of the obfuscated addresses we've
        already created
        """
        for _ip in self.dataset.values():
            if str(ipaddr).split('/')[0] == _ip.split('/')[0]:
                return True
        return False

    def get(self, ipaddr):
        """Ensure that when requesting an obfuscated address, we return a str
        object instead of an IPv(4|6)Address object
        """
        filt_start = ('/', '=', ']', ')')
        if ipaddr.startswith(filt_start):
            ipaddr = ipaddr.lstrip(''.join(filt_start))

        if ipaddr in self.dataset.keys():
            return self.dataset[ipaddr]

        if self.ignore_item(ipaddr) or self.ip_in_dataset(ipaddr):
            return ipaddr

        # it's not in there, but let's make sure we haven't previously added
        # an address with a CIDR notation and we're now looking for it without
        # that notation
        if '/' not in ipaddr:
            for key in self.dataset.keys():
                if key.startswith(ipaddr):
                    return self.dataset[key].split('/')[0]

        # fallback to the default map behavior of adding it fresh
        return self.add(ipaddr)

    def set_ip_cidr_from_existing_subnet(self, addr):
        """Determine if a given address is in a subnet of an already obfuscated
        network and if it is, then set the address' network to the network
        object we're tracking. This allows us to match ip addresses with or
        without a CIDR notation and maintain proper network relationships.
        """
        nets = []
        for net in self._networks:
            if addr.ip == net.broadcast_address:
                addr.network = net
                return
            if addr.ip in net:
                nets.append(net)
        # assign the address to the smallest network that was matched. This is
        # necessary due to certain files specifying addresses that cause the
        # ipaddress library to create artificially huge subnets that will
        # include the actual subnets used by the system
        if nets:
            nets.sort(key=lambda n: n.prefixlen, reverse=True)
            addr.network = nets[0]

    def sanitize_item(self, item):
        """Given an IP address, sanitize it to an obfuscated network or host
        address as appropriate
        """

        try:
            addr = ipaddress.ip_interface(item)
        except ValueError:
            # not an IP, add it to the skip list to avoid flooding logs
            self.ignore_matches.append(item)
            raise
        network = addr.network

        if str(network.netmask) == '255.255.255.255':
            # check to see if this IP is in a subnet of an already obfuscated
            # network and if it has, replace the default /32 netmask that
            # ipaddress applies to no CIDR-notated addresses
            self.set_ip_cidr_from_existing_subnet(addr)
        else:
            # we have a CIDR notation, so generate an obfuscated network
            # address and then generate an IP address within that network's
            # range
            self.sanitize_network(network)
        return self.sanitize_ipaddr(addr)

    def sanitize_network(self, network):
        """Obfuscate the network address provided, and if there are host bits
        in the address then obfuscate those as well
        """
        # check if the address is in a network we've already encountered
        if network not in self._networks:
            self._new_obfuscated_network(network)

    def sanitize_ipaddr(self, addr):
        """Obfuscate the IP address within the known obfuscated network
        """
        # get the obfuscated network object
        if addr.network in self._networks:
            _obf_network = self._networks[addr.network]

            # if the plain address is the broadcast address for it's own
            # network, then assign the broadcast address for the obfuscated
            # network
            if addr.ip == addr.network.broadcast_address:
                return str(_obf_network.broadcast_address)

            # otherwise within that obfuscated network grab the next available
            # address from it
            for _ip in _obf_network.hosts():
                if not self.ip_in_dataset(_ip):
                    # the ipaddress module does not assign the network's
                    # netmask to hosts in the hosts() generator for some reason
                    return "%s/%s" % (str(_ip), _obf_network.prefixlen)

        # ip is a single ip address without the netmask
        return self._new_obfuscated_single_address()

    def _new_obfuscated_single_address(self):
        def _gen_address():
            _octets = []
            for i in range(0, 4):
                _octets.append(random.randint(11, 99))
            return "%s.%s.%s.%s" % tuple(_octets)

        _addr = _gen_address()
        if _addr in self.dataset.values():
            return self._new_obfuscated_single_address()
        return _addr

    def _new_obfuscated_network(self, network):
        """Generate an obfuscated network address for the network address given
        which will allow us to maintain network relationships without divulging
        actual network details

        Positional arguments:

            :param network:     An ipaddress.IPv{4|6)Network object
        """
        _obf_network = None

        if isinstance(network, ipaddress.IPv4Network):
            if self.network_first_octet in self.skip_network_octets:
                self.network_first_octet += 1
            _obf_address = "%s.0.0.0" % self.network_first_octet
            _obf_mask = network.with_netmask.split('/')[1]
            _obf_network = ipaddress.IPv4Network(
                "%s/%s" % (_obf_address, _obf_mask)
            )
            self.network_first_octet += 1

        if isinstance(network, ipaddress.IPv6Network):
            # TODO: define this
            pass

        if _obf_network:
            self._networks[network] = _obf_network
            self.dataset[str(network)] = str(_obf_network)
