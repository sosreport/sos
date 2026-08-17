# Copyright (C) 2026 Red Hat, Inc.

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class SysRoles(Plugin, RedHatPlugin):

    short_desc = 'RHEL System Roles fingerprint data'

    plugin_name = 'sysroles'
    packages = ('rhel-system-roles',)
    files = ('/var/log/sysroles.jsonl',)

    def setup(self):
        self.add_copy_spec('/var/log/sysroles.jsonl')

# vim: set et ts=4 sw=4 :
