# Copyright (C) 2007-2012 Red Hat, Inc., Ben Turner <bturner@redhat.com>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin


class Iscsi(Plugin):
    """iscsi-initiator related information
    """

    plugin_name = "iscsi"


class RedHatIscsi(Iscsi, RedHatPlugin):
    """iscsi-initiator related information Red Hat based distributions
    """

    packages = ('iscsi-initiator-utils',)

    def setup(self):
        super(RedHatIscsi, self).setup()
        self.add_copy_specs([
            "/etc/iscsi/iscsid.conf",
            "/etc/iscsi/initiatorname.iscsi",
            "/var/lib/iscsi"
        ])
        self.add_cmd_outputs([
            "iscsiadm -m session -P 3",
            "iscsiadm -m node -P 3",
            "iscsiadm -m iface -P 1",
            "iscsiadm -m node --op=show"
        ])

# vim: et ts=4 sw=4
