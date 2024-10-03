# Copyright (C) 2024 Canonical Ltd., Arif Ali <arif.ali@canonical.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos_tests import StageTwoReportTest


class AptConfScrubTest(StageTwoReportTest):
    """Ensure that sources.list and apt conf are picked up and properly
    scrubbed

    :avocado: tags=stagetwo,scrub
    """

    sos_cmd = '-o apt'
    ubuntu_only = True
    files = [
        ('apt-proxy.conf', '/etc/apt/apt.conf.d/50-apt-proxy'),
        ('apt-sources.list', '/etc/apt/sources.list'),
        ('apt-sources.sources', '/etc/apt/sources.list.d/ubuntu.sources'),
    ]

    def test_apt_sources_and_apt_confs_collected(self):
        self.assertFileCollected('/etc/apt/apt.conf.d/50-apt-proxy')
        self.assertFileCollected('/etc/apt/sources.list')
        self.assertFileCollected('/etc/apt/ubuntu.sources')

    def test_apt_sources_and_proxy_scrubbed(self):
        # Ensure that we scrubbed all passwords
        files_to_check = [
            '/etc/apt/apt.conf.d/50-apt-proxy',
            '/etc/apt/sources.list',
            '/etc/apt/sources.list.d/ubuntu.sources',
        ]
        password = 'somesecretpassword'
        for file in files_to_check:
            self.assertFileNotHasContent(file, password)

# vim: set et ts=4 sw=4 :
