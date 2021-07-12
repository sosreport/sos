# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import unittest

from ipaddress import ip_interface
from sos.cleaner.parsers.ip_parser import SoSIPParser
from sos.cleaner.parsers.mac_parser import SoSMacParser
from sos.cleaner.parsers.hostname_parser import SoSHostnameParser
from sos.cleaner.parsers.keyword_parser import SoSKeywordParser
from sos.cleaner.mappings.ip_map import SoSIPMap
from sos.cleaner.mappings.mac_map import SoSMacMap
from sos.cleaner.mappings.hostname_map import SoSHostnameMap
from sos.cleaner.mappings.keyword_map import SoSKeywordMap


class CleanerMapTests(unittest.TestCase):

    def setUp(self):
        self.mac_map = SoSMacMap()
        self.ip_map = SoSIPMap()
        self.host_map = SoSHostnameMap()
        self.host_map.load_domains_from_options(['redhat.com'])
        self.kw_map = SoSKeywordMap()

    def test_mac_map_obfuscate_valid_v4(self):
        _test = self.mac_map.get('12:34:56:78:90:ab')
        self.assertNotEqual(_test, '12:34:56:78:90:ab')

    def test_mac_map_obfuscate_valid_v6(self):
        _test = self.mac_map.get('12:34:56:ff:fe:78:90:ab')
        self.assertNotEqual(_test, '12:34:56:ff:fe:78:90:ab')

    def test_mac_map_obfuscate_valid_v6_quad(self):
        _test = self.mac_map.get('1234:56ff:fe78:90ab')
        self.assertNotEqual(_test, '1234:56ff:fe78:90ab')

    def test_mac_map_skip_ignores(self):
        _test = self.mac_map.get('ff:ff:ff:ff:ff:ff')
        self.assertEquals(_test, 'ff:ff:ff:ff:ff:ff')

    def test_mac_map_avoid_duplicate_obfuscation(self):
        _test = self.mac_map.get('ab:cd:ef:fe:dc:ba')
        _dup = self.mac_map.get(_test)
        self.assertEquals(_test, _dup)

    def test_ip_map_obfuscate_v4_with_cidr(self):
        _test = self.ip_map.get('192.168.1.0/24')
        self.assertNotEqual(_test, '192.168.1.0/24')

    def test_ip_map_obfuscate_no_cidr(self):
        _test = self.ip_map.get('192.168.2.2')
        self.assertNotEqual(_test, '192.168.2.2')

    def test_ip_map_obfuscate_same_subnet(self):
        _net = ip_interface(self.ip_map.get('192.168.3.0/24'))
        _test = ip_interface(self.ip_map.get('192.168.3.1'))
        self.assertTrue(_test.ip in _net.network)

    def test_ip_map_get_same_with_or_without_cidr(self):
        _hostwsub = self.ip_map.get('192.168.4.1/24')
        _hostnosub = self.ip_map.get('192.168.4.1')
        self.assertEqual(_hostwsub.split('/')[0], _hostnosub)

    def test_ip_skip_ignores(self):
        _test = self.ip_map.get('127.0.0.1')
        self.assertEquals(_test, '127.0.0.1')

    def test_hostname_obfuscate_domain_options(self):
        _test = self.host_map.get('www.redhat.com')
        self.assertNotEqual(_test, 'www.redhat.com')

    def test_hostname_obfuscate_same_item(self):
        _test1 = self.host_map.get('example.redhat.com')
        _test2 = self.host_map.get('example.redhat.com')
        self.assertEqual(_test1, _test2)

    def test_hostname_obfuscate_just_domain(self):
        _test = self.host_map.get('redhat.com')
        self.assertEqual(_test, 'obfuscateddomain0.com')

    def test_hostname_no_obfuscate_non_loaded_domain(self):
        _test = self.host_map.get('foobar.com')
        self.assertEqual(_test, 'foobar.com')

    def test_hostname_no_obfuscate_non_loaded_fqdn(self):
        _test = self.host_map.get('example.foobar.com')
        self.assertEqual(_test, 'example.foobar.com')

    def test_keyword_single(self):
        _test = self.kw_map.get('foobar')
        self.assertEqual(_test, 'obfuscatedword0')


class CleanerParserTests(unittest.TestCase):

    def setUp(self):
        self.ip_parser = SoSIPParser(config={})
        self.mac_parser = SoSMacParser(config={})
        self.host_parser = SoSHostnameParser(config={}, opt_domains='foobar.com')
        self.kw_parser = SoSKeywordParser(config={}, keywords=['foobar'])
        self.kw_parser_none = SoSKeywordParser(config={})

    def test_ip_parser_valid_ipv4_line(self):
        line = 'foobar foo 10.0.0.1/24 barfoo bar'
        _test = self.ip_parser.parse_line(line)[0]
        self.assertNotEqual(line, _test)

    def test_ip_parser_invalid_ipv4_line(self):
        line = 'foobar foo 10.1.2.350 barfoo bar'
        self.assertRaises(ValueError, self.ip_parser.parse_line, line)

    def test_ip_parser_package_version_line(self):
        line = 'mycoolpackage-1.2.3.4.5'
        _test = self.ip_parser.parse_line(line)[0]
        self.assertEqual(line, _test)

    def test_mac_parser_valid_ipv4_line(self):
        line = 'foobar foo 13:24:35:46:57:68 bar barfoo'
        _test = self.mac_parser.parse_line(line)[0]
        self.assertNotEqual(line, _test)

    def test_mac_parser_valid_ipv6_line(self):
        line = 'foobar foo AA:BB:CC:FF:FE:DD:EE:FF bar barfoo'
        _test = self.mac_parser.parse_line(line)[0]
        self.assertNotEqual(line, _test)

    def test_hostname_load_hostname_string(self):
        fqdn = 'myhost.subnet.example.com'
        self.host_parser.load_hostname_into_map(fqdn)

    def test_hostname_valid_domain_line(self):
        self.host_parser.load_hostname_into_map('myhost.subnet.example.com')
        line = 'testing myhost.subnet.example.com in a string'
        _test = self.host_parser.parse_line(line)[0]
        self.assertNotEqual(line, _test)

    def test_hostname_short_name_in_line(self):
        self.host_parser.load_hostname_into_map('myhost.subnet.example.com')
        line = 'testing just myhost in a line'
        _test = self.host_parser.parse_line(line)[0]
        self.assertNotEqual(line, _test)

    def test_keyword_parser_valid_line(self):
        line = 'this is my foobar test line'
        _test = self.kw_parser.parse_line(line)[0]
        self.assertNotEqual(line, _test)

    def test_keyword_parser_no_change_by_default(self):
        line = 'this is my foobar test line'
        _test = self.kw_parser_none.parse_line(line)[0]
        self.assertEqual(line, _test)
