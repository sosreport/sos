# Copyright (C) 2013 Red Hat, Inc., Lukas Zapletal <lzap@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Foreman(Plugin, RedHatPlugin):
    """Foreman/Satellite 6 systems management
    """

    plugin_name = 'foreman'
    profiles = ('sysmgmt',)
    packages = ('foreman-debug',)

    def setup(self):
        cmd = "foreman-debug"

        path = self.get_cmd_output_path(name="foreman-debug")
        self.add_cmd_output("%s -g -q -a -d %s" % (cmd, path),
                            chroot=self.tmp_in_sysroot(), timeout=900)

# vim: set et ts=4 sw=4 :
