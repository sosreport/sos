# Copyright (C) 2018 Red Hat, Inc., David Vallee Delisle <dvd@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class OpenStackNovajoin(Plugin):

    short_desc = 'OpenStack Novajoin'
    plugin_name = "openstack_novajoin"
    profiles = ('openstack', 'openstack_undercloud')

    def setup(self):
        self.add_copy_spec("/etc/novajoin/")
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/novajoin/")
        else:
            self.add_copy_spec("/var/log/novajoin/*.log")

    def postproc(self):
        regexp = (r"(?i)password=(.*)")
        self.do_file_sub("/etc/novajoin/join.conf", regexp,
                         r"password=*********")
        regexp = (r"(?i)memcache_secret_key=(.*)")
        self.do_file_sub("/etc/novajoin/join.conf", regexp,
                         r"password=*********")


class RedHatNovajoin(OpenStackNovajoin, RedHatPlugin):

    packages = ('python-novajoin',)

    def setup(self):
        super(RedHatNovajoin, self).setup()

# vim: set et ts=4 sw=4 :
