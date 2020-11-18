# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Ssmtp(Plugin, RedHatPlugin):

    short_desc = 'sSMTP information'

    plugin_name = 'ssmtp'
    profiles = ('mail', 'system')

    packages = ('ssmtp',)

    def setup(self):
        self.add_copy_spec([
            "/etc/ssmtp/ssmtp.conf",
            "/etc/ssmtp/revaliases",
            "/etc/aliases"
        ])

    def postproc(self):
        self.do_file_sub(
            '/etc/ssmtp/ssmtp.conf',
            r'AuthPass=(\S*)',
            r'AuthPass=********'
        )

# vim: set et ts=4 sw=4 :
