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
from sos.cleaner.parsers.ipv6_parser import SoSIPv6Parser
from sos.cleaner.parsers.username_parser import SoSUsernameParser
from sos.cleaner.mappings.ip_map import SoSIPMap
from sos.cleaner.mappings.mac_map import SoSMacMap
from sos.cleaner.mappings.hostname_map import SoSHostnameMap
from sos.cleaner.mappings.keyword_map import SoSKeywordMap
from sos.cleaner.mappings.ipv6_map import SoSIPv6Map
from sos.cleaner.preppers import SoSPrepper
from sos.cleaner.preppers.hostname import HostnamePrepper
from sos.cleaner.preppers.ip import IPPrepper
from sos.cleaner.archives.sos import SoSReportArchive
from sos.options import SoSOptions

class CleanerMapTests(unittest.TestCase):

    def setUp(self):
        self.mac_map = SoSMacMap()
        self.ip_map = SoSIPMap()
        self.host_map = SoSHostnameMap()
        self.host_map.sanitize_item('redhat.com')
        self.kw_map = SoSKeywordMap()
        self.ipv6_map = SoSIPv6Map()

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
        self.assertEqual(_test, 'ff:ff:ff:ff:ff:ff')

    def test_mac_map_avoid_duplicate_obfuscation(self):
        _test = self.mac_map.get('ab:cd:ef:fe:dc:ba')
        _dup = self.mac_map.get(_test)
        self.assertEqual(_test, _dup)

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
        self.assertEqual(_test, '127.0.0.1')

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

    def test_ipv6_obfuscate_global(self):
        _net = '2022:1104:abcd::'
        _ob_net = self.ipv6_map.get(_net)
        self.assertNotEqual(_net, _ob_net, 'Address was unchanged')
        self.assertTrue(_ob_net.startswith('534f'), 'Global address does not start with identifier')
        _host = '2022:1104:abcd::1234'
        _ob_host = self.ipv6_map.get(_host)
        self.assertNotEqual(_host, _ob_host, 'Host address was unchanged')
        self.assertTrue(_host.startswith(_net), 'Host address not in network')

    def test_ipv6_link_local(self):
        _test = 'fe80::1234'
        _ob_test = self.ipv6_map.get(_test)
        self.assertTrue(_ob_test.startswith('fe80'), 'Link-local identifier not maintained')
        self.assertNotEqual(_test, _ob_test, 'Device address was unchanged')

    def test_ipv6_private(self):
        _net = 'fd00:abcd::'
        _host = 'fd00:abcd::1234'
        _ob_net = self.ipv6_map.get(_net).split('/')[0]
        _ob_host = self.ipv6_map.get(_host)
        self.assertTrue(_ob_net.startswith('fd53'), 'Private network does not start with identifier')
        self.assertTrue(_ob_host.startswith(_ob_net), 'Private address not in same network')
        self.assertNotEqual(_net, _ob_net, 'Private network was unchanged')

    def test_ipv6_short_network(self):
        _net = 'ff02::'
        _ob_net = self.ipv6_map.get(_net)
        self.assertTrue(_ob_net.startswith(('53', '54')), f'Short network does not start with identifier: {_ob_net}')

    def test_ipv6_consistent_obfuscation(self):
        _test = '2022:1104:abcd::ef09'
        _new = self.ipv6_map.get(_test)
        _second = self.ipv6_map.get(_test)
        self.assertEqual(_new, _second, "Same address produced two different results")

    def test_ipv6_global_no_collision(self):
        """Tests that generating more than 256 global network obfuscations does
        not produce any repeats"""
        _nets = []
        for i in range(1, 300):
            _nets.append(self.ipv6_map.get(f"f{i:03}::abcd").split('::')[0])
        # if there are any duplicates, then the length of the set will not match
        self.assertTrue(len(set(_nets)) == len(_nets), "Duplicate global network obfuscations produced")
        self.assertTrue(_nets[-1].startswith('54'), "First hextet of global network obfuscation over 256 not expected '54'")

class CleanerParserTests(unittest.TestCase):

    def setUp(self):
        self.ip_parser = SoSIPParser(config={})
        self.ipv6_parser = SoSIPv6Parser(config={})
        self.mac_parser = SoSMacParser(config={})
        self.host_parser = SoSHostnameParser(config={})
        self.host_parser.mapping.add('foobar.com')
        self.kw_parser = SoSKeywordParser(config={})
        self.kw_parser.mapping.add('foobar')
        self.kw_parser_none = SoSKeywordParser(config={})
        self.kw_parser.generate_item_regexes()
        self.uname_parser = SoSUsernameParser(config={})
        self.uname_parser.mapping.add('DOMAIN\myusername')

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

    def test_mac_parser_with_quotes(self):
        line = "foobar foo '12:34:56:78:90:AA' bar barfoo"
        _test = self.mac_parser.parse_line(line)[0]
        self.assertNotEqual(line, _test)
        dline = 'foobar foo "aa:12:bb:34:cc:56" bar barfoo'
        _dtest = self.mac_parser.parse_line(dline)[0]
        self.assertNotEqual(dline, _dtest)

    def test_mac_parser_with_quotes_ipv6(self):
        line = "foobar foo 'FF:EE:DD:FF:FE:CC:BB:AA' bar barfoo"
        _test = self.mac_parser.parse_line(line)[0]
        self.assertNotEqual(line, _test)
        dline = 'foobar foo "DD:EE:FF:FF:FE:BB:CC:AA" bar barfoo'
        _dtest = self.mac_parser.parse_line(dline)[0]
        self.assertNotEqual(dline, _dtest)

    def test_mac_parser_with_quotes_ipv6_quad(self):
        line = "foobar foo 'AABB:CCDD:EEFF:FFAA' bar barfoo"
        _test = self.mac_parser.parse_line(line)[0]
        self.assertNotEqual(line, _test)
        dline = 'foobar foo "AAFF:FFEE:DDCC:BBAA" bar barfoo'
        _dtest = self.mac_parser.parse_line(dline)[0]
        self.assertNotEqual(dline, _dtest)

    def test_hostname_load_hostname_string(self):
        fqdn = 'myhost.subnet.example.com'
        self.host_parser.mapping.add(fqdn)

    def test_hostname_valid_domain_line(self):
        self.host_parser.mapping.add('myhost.subnet.example.com')
        line = 'testing myhost.subnet.example.com in a string'
        _test = self.host_parser.parse_line(line)[0]
        self.assertNotEqual(line, _test)

    def test_hostname_short_name_in_line(self):
        self.host_parser.mapping.add('myhost.subnet.example.com')
        line = 'testing just myhost in a line'
        _test = self.host_parser.parse_line(line)[0]
        self.assertNotEqual(line, _test)

    def test_obfuscate_whole_fqdn_for_given_domainname(self):
        self.host_parser.mapping.add('sostestdomain.domain')
        line = 'let obfuscate soshost.sostestdomain.domain'
        _test = self.host_parser.parse_line(line)[0]
        self.assertFalse('soshost' in _test)
        self.assertFalse('sostestdomain' in _test)

    def test_hostname_no_obfuscate_underscore(self):
        line = 'pam_env.so _why.not_'
        _test = self.host_parser.parse_line(line)[0]
        self.assertEqual(line, _test)

    def test_keyword_parser_valid_line(self):
        line = 'this is my foobar test line'
        _test = self.kw_parser.parse_line(line)[0]
        self.assertNotEqual(line, _test)

    def test_keyword_parser_no_change_by_default(self):
        line = 'this is my foobar test line'
        _test = self.kw_parser_none.parse_line(line)[0]
        self.assertEqual(line, _test)

    def test_ipv6_parser_strings(self):
        t1 = 'testing abcd:ef01::1234 as a compressed address'
        t2 = 'testing abcd:ef01::5678:1234 as a separate address'
        t3 = 'testing 2607:c540:8c00:3318::34/64 as another address'
        t4 = 'testing 2007:1234:5678:90ab:0987:6543:21fe:dcba as a full address'
        t1_test = self.ipv6_parser.parse_line(t1)[0]
        t2_test = self.ipv6_parser.parse_line(t2)[0]
        t3_test = self.ipv6_parser.parse_line(t3)[0]
        t4_test = self.ipv6_parser.parse_line(t4)[0]
        self.assertNotEqual(t1, t1_test, f"Parser did not match and obfuscate '{t1}'")
        self.assertNotEqual(t2, t2_test, f"Parser did not match and obfuscate '{t2}'")
        self.assertNotEqual(t3, t3_test, f"Parser did not match and obfuscate '{t3}'")
        self.assertNotEqual(t4, t4_test, f"Parser did not match and obfuscate '{t4}'")

    def test_ipv6_no_match_signature(self):
        modstr = '2D:4F:6E:55:4F:E8:5E:D2:D2:A3:73:62:AB:FD:F9:C5:A5:53:31:93'
        mod_test = self.ipv6_parser.parse_line(modstr)[0]
        self.assertEqual(modstr, mod_test, "Parser matched module signature, and should not")

    def test_ipv6_no_match_log_false_positive(self):
        logln = 'Automatically imported trusted_ca::ca from trusted_ca/ca into production'
        log_test = self.ipv6_parser.parse_line(logln)[0]
        self.assertEqual(logln, log_test, "IPv6 parser incorrectly matched a log line of 'trusted_ca::ca'")

    def test_ad_username(self):
        line = "DOMAIN\myusername"
        _test = self.uname_parser.parse_line(line)[0]
        self.assertNotEqual(line, _test)


class PrepperTests(unittest.TestCase):
    """
    Ensure that the translations for different parser/mapping methods are
    working
    """

    def setUp(self):
        self.prepper = SoSPrepper(SoSOptions())
        self.archive = SoSReportArchive(
            archive_path='tests/test_data/sosreport-cleanertest-2021-08-03-qpkxdid.tar.xz',
            tmpdir='/tmp'
        )
        self.host_prepper = HostnamePrepper(SoSOptions(domains=[]))
        self.ipv4_prepper = IPPrepper(SoSOptions())

    def test_parser_method_translation(self):
        self.assertEqual([], self.prepper.get_parser_file_list('hostname', None))

    def test_mapping_method_translation(self):
        self.assertEqual([], self.prepper.get_items_for_map('foobar', None))

    def test_hostname_prepper_map_items(self):
        self.assertEqual(['cleanertest'], self.host_prepper.get_items_for_map('hostname', self.archive))

    def test_ipv4_prepper_parser_files(self):
        self.assertEqual(['sos_commands/networking/ip_-o_addr'], self.ipv4_prepper.get_parser_file_list('ip', self.archive))

    def test_ipv4_prepper_invalid_parser_files(self):
        self.assertEqual([], self.ipv4_prepper.get_parser_file_list('foobar', self.archive))

