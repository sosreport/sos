# Copyright (C) 2015 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Mpt(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """ LSI Message Passing Technology
    """
    files = ('/proc/mpt',)
    profiles = ('storage', )
    plugin_name = 'mpt'

    def setup(self):
        self.add_copy_spec("/proc/mpt")

# vim: set et ts=4 sw=4 :
