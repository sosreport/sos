# Copyright (C) 2007 Shijoe George <spanjikk@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Nscd(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Name service caching daemon
    """

    plugin_name = 'nscd'
    profiles = ('services', 'identity', 'system')

    files = ('/etc/nscd.conf',)
    packages = ('nscd',)

    def setup(self):
        self.add_copy_spec("/etc/nscd.conf")

        opt = self.file_grep(r"^\s*logfile", "/etc/nscd.conf")
        if (len(opt) > 0):
            for o in opt:
                f = o.split()
                self.add_copy_spec(f[1])

# vim: set et ts=4 sw=4 :
