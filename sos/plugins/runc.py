# Copyright (C) 2017 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Runc(Plugin):

    """runC container runtime"""

    plugin_name = 'runc'
    profiles = ('container',)

    def setup(self):

        self.add_cmd_output('runc list')

        cons = self.get_command_output('runc list -q')
        conlist = [c for c in cons['output'].splitlines()]
        for con in conlist:
            self.add_cmd_output('runc ps %s' % con)
            self.add_cmd_output('runc state %s' % con)
            self.add_cmd_output('runc events --stats %s' % con)


class RedHatRunc(Runc, RedHatPlugin):

    packages = ('runc', )

    def setup(self):
        super(RedHatRunc, self).setup()
