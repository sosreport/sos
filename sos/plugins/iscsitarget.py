# Copyright (C) 2007-2012 Red Hat, Inc., Ben Turner <bturner@redhat.com>
# Copyright (C) 2012 Adam Stokes <adam.stokes@canonical.com>

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

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class IscsiTarget(Plugin):
    """iSCSI target
    """

    plugin_name = "iscsitarget"
    profiles = ('storage',)


class RedHatIscsiTarget(IscsiTarget, RedHatPlugin):

    packages = ('scsi-target-utils',)

    def setup(self):
        super(RedHatIscsiTarget, self).setup()
        self.add_copy_spec("/etc/tgt/targets.conf")
        self.add_cmd_output("tgtadm --lld iscsi --op show --mode target")


class DebianIscsiTarget(IscsiTarget, DebianPlugin, UbuntuPlugin):

    packages = ('iscsitarget',)

    def setup(self):
        super(DebianIscsiTarget, self).setup()
        self.add_copy_spec([
            "/etc/iet",
            "/etc/sysctl.d/30-iscsitarget.conf",
            "/etc/default/iscsitarget"
        ])

# vim: set et ts=4 sw=4 :
