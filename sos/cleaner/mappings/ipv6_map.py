# Copyright 2022 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import ipaddress

from random import getrandbits
from sos.cleaner.mappings import SoSMap


def generate_hextets(hextets):
    """Generate a random set of hextets, based on the length of the source
    hextet. If any hextets are compressed, keep that compression.

    E.G. '::1234:bcd' will generate a leading empty '' hextet, followed by two
    4-character hextets.

    :param hextets:     The extracted hextets from a source address
    :type hextets:      ``list``

    :returns:           A set of randomized hextets for use in an obfuscated
                        address
    :rtype:             ``list``
    """
    return [random_hex(4) if h else '' for h in hextets]


def random_hex(length):
    """Generate a string of size length of random hex characters.

    :param length:  The number of characters to generate
    :type length:   ``int``

    :returns:       A string of ``length`` hex characters
    :rtype:         ``str``
    """
    return f"{getrandbits(4*length):0{length}x}"


class SoSIPv6Map(SoSMap):
    """Mapping for IPv6 addresses and networks.

    Much like the IP map handles IPv4 addresses, this map is designed to take
    IPv6 strings and obfuscate them consistently to maintain network topology.
    To do this, addresses will be manipulated by the ipaddress library.

    If an IPv6 address is encountered without a netmask, it is assumed to be a
    /64 address.
    """

    networks = {}

    ignore_matches = [
        r'^::1/.*',
        r'::/0',
        r'fd53:.*',
        r'^53..:'
    ]

    first_hexes = ['534f']

    compile_regexes = False
    version = 1

    def conf_update(self, config):
        """Override the base conf_update() so that we can load the existing
        networks into ObfuscatedIPv6Network() objects for the current run.
        """
        if 'networks' not in config:
            return
        for network in config['networks']:
            _orig = ipaddress.ip_network(network)
            _obfuscated = config['networks'][network]['obfuscated']
            _net = self._get_network(_orig, _obfuscated)
            self.dataset[_net.original_address] = _net.obfuscated_address
            for host in config['networks'][network]['hosts']:
                _ob_host = config['networks'][network]['hosts'][host]
                _net.add_obfuscated_host_address(host, _ob_host)
                self.dataset[host] = _ob_host

    def sanitize_item(self, ipaddr):
        _prefix = ipaddr.split('/')[-1] if '/' in ipaddr else ''
        _ipaddr = ipaddr
        if not _prefix:
            # assume a /64 default per protocol
            _ipaddr += "/64"
        try:
            _addr = ipaddress.ip_network(_ipaddr)
            # ipaddr was an actual network per protocol
            _net = self._get_network(_addr)
            _ipaddr = _net.obfuscated_address
        except ValueError:
            # A ValueError is raised from the ipaddress module when passing
            # an address such as 2620:52:0:2d80::4fe/64, which has host bits
            # '::4fe' set - the /64 is generally interpreted only for network
            # addresses. We use this behavior to properly obfuscate the network
            # before obfuscating a host address within that network
            _addr = ipaddress.ip_network(_ipaddr, strict=False)
            _net = self._get_network(_addr)
            if _net.network_addr not in self.dataset:
                self.dataset[_net.original_address] = _net.obfuscated_address
            # then, get the address within the network
            _hostaddr = ipaddress.ip_address(_ipaddr.split('/')[0])
            _ipaddr = _net.obfuscate_host_address(_hostaddr)

        if _prefix and '/' not in _ipaddr:
            return f"{_ipaddr}/{_prefix}"
        return _ipaddr

    def _get_network(self, address, obfuscated=''):
        """Attempt to find an existing ObfuscatedIPv6Network object from which
        to either find an existing obfuscated match, or create a new one. If
        no such object already exists, create it.
        """
        _addr = address.compressed
        if _addr not in self.networks:
            self.networks[_addr] = ObfuscatedIPv6Network(address, obfuscated,
                                                         self.first_hexes)
        return self.networks[_addr]


class ObfuscatedIPv6Network():
    """An abstraction class that represents a network that is (to be) handled
    by sos.

    Each distinct IPv6 network that we encounter will have a representative
    instance of this class, from which new obfuscated subnets and host
    addresses will be generated.

    This class should be built from an ``ipaddress.IPv6Network`` object. If
    an obfuscation string is not passed, one will be created during init.
    """

    def __init__(self, addr, obfuscation='', used_hexes=None):
        """Basic setup for the obfuscated network. Minor validation on the addr
        used to create the instance, as well as on an optional ``obfuscation``
        which if set, will serve as the obfuscated_network address.

        :param addr:        The *un*obfuscated network to be handled
        :type addr:         ``ipaddress.IPv6Network``

        :param obfuscation: An optional pre-determined string representation of
                            the obfuscated network address
        :type obfuscation:  ``str``

        :param used_hexes:  A list of already used hexes for the first hextet
                            of a potential global address obfuscation
        :type used_hexes:   ``list``
        """
        if not isinstance(addr, ipaddress.IPv6Network):
            raise Exception('Invalid network: not an IPv6Network object')
        self.addr = addr
        self.prefix = addr.prefixlen
        self.network_addr = addr.network_address.compressed
        self.hosts = {}
        if used_hexes is None:
            self.first_hexes = ['534f']
        else:
            self.first_hexes = used_hexes
        if not obfuscation:
            self._obfuscated_network = self._obfuscate_network_address()
        else:
            if not isinstance(obfuscation, str):
                raise TypeError(f"Pre-determined obfuscated network address "
                                f"must be str, not {type(obfuscation)}")
            self._obfuscated_network = obfuscation.split('/')[0]

    @property
    def obfuscated_address(self):
        return f"{self._obfuscated_network}/{self.prefix}"

    @property
    def original_address(self):
        return self.addr.compressed

    def _obfuscate_network_address(self):
        """Generate the obfuscated pair for the network address. This is
        determined based on the netmask of the network this class was built
        on top of.
        """
        if self.addr.is_global:
            return self._obfuscate_global_address()
        if self.addr.is_link_local:
            # link-local addresses are always fe80::/64. This is not sensitive
            # in itself, and retaining the information that an address is a
            # link-local address is important for problem analysis, so don't
            # obfuscate this network information.
            return self.network_addr
        if self.addr.is_private:
            return self._obfuscate_private_address()
        return self.network_addr

    def _obfuscate_global_address(self):
        """Global unicast addresses have a 48-bit global routing prefix and a
        16-bit subnet. We set the global routing prefix to a static
        sos-specific identifier that could never be seen in the wild,
        '534f:'

        We then randomize the subnet hextet.
        """
        _hextets = self.network_addr.split(':')[1:]
        _ob_hex = ['534f']
        if all(not c for c in _hextets):
            # we have only a single defined hextet, e.g. ff00::/64, so we need
            # to not use the standard first-hex identifier or we'll overlap
            # every similar address obfuscation.
            # Set the leading bits to 53, but increment upwards from there for
            # when we exceed 256 networks obfuscated in this manner.
            _start = 53 + (len(self.first_hexes) // 256)
            _ob_hex = f"{_start}{random_hex(2)}"
            while _ob_hex in self.first_hexes:
                # prevent duplicates
                _ob_hex = f"{_start}{random_hex(2)}"
            self.first_hexes.append(_ob_hex)
            _ob_hex = [_ob_hex]
        _ob_hex.extend(generate_hextets(_hextets))
        return ':'.join(_ob_hex)

    def _obfuscate_private_address(self):
        """The first 8 bits will always be 'fd', the next 40 bits are meant
        to be a global ID, followed by 16 bits for the subnet. To keep things
        relatively simply we maintain the first hextet as 'fd53', and then
        randomize any remaining hextets
        """
        _hextets = self.network_addr.split(':')[1:]
        _ob_hex = ['fd53']
        _ob_hex.extend(generate_hextets(_hextets))
        return ':'.join(_ob_hex)

    def obfuscate_host_address(self, addr):
        """Given an unobfuscated address, generate an obfuscated match for it,
        and save it to this network for tracking during the execution of clean.

        Note: another way to do this would be to convert the obfuscated network
        to bytes, and add a random amount to that based on the number of
        addresses that the network can support and from that new bytes count
        craft a new IPv6 address. This has the advantage of absolutely
        guaranteeing the new address is within the network space (whereas the
        method employed below could *theoretically* generate an overlapping
        address), but would in turn remove any ability to compress obfuscated
        addresses to match the general format/syntax of the address it is
        replacing. For the moment, it is assumed that being able to maintain a
        quick mental note of "unobfuscated device ff00::1 is obfuscated device
        53ad::a1b2" is more desireable than "ff00::1 is now obfuscated as
        53ad::1234:abcd:9876:a1b2:".

        :param addr:        The unobfuscated IPv6 address
        :type addr:         ``ipaddress.IPv6Address``

        :returns:           An obfuscated address within this network
        :rtype:             ``str``
        """
        def _generate_address():
            return ''.join([
                self._obfuscated_network,
                ':'.join(generate_hextets(_host.split(':')))
            ])

        if addr.compressed not in self.hosts:
            # separate host from the address by removing its network prefix
            _n = self.network_addr.rstrip(':')
            _host = addr.compressed[len(_n):].lstrip(':')
            _ob_host = _generate_address()
            while _ob_host in self.hosts.values():
                _ob_host = _generate_address()
            self.add_obfuscated_host_address(addr.compressed, _ob_host)
        return self.hosts[addr.compressed]

    def add_obfuscated_host_address(self, host, obfuscated):
        """Adds an obfuscated pair to the class for tracking and ongoing
        consistency in obfuscation.
        """
        self.hosts[host] = obfuscated
