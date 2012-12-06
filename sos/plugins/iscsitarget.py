## Copyright (C) 2007-2012 Red Hat, Inc., Ben Turner <bturner@redhat.com>
## Copyright (C) 2012 Adam Stokes <adam.stokes@canonical.com>

### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin

class iscsitarget(Plugin):
    """iscsi-target related information
    """

    plugin_name = "iscsitarget"

class RedHatIscsiTarget(Plugin, RedHatPlugin):
    """iscsi-target related information for Red Hat distributions
    """

    packages = ('scsi-target-utils',)

    def setup(self):
        self.addCopySpec("/etc/tgt/targets.conf")
        self.collectExtOutput("tgtadm --lld iscsi --op show --mode target")

class DebianIscsiTarget(iscsitarget, DebianPlugin, UbuntuPlugin):
    """iscsi-target related information for Debian based distributions
    """

    packages = ('iscsitarget',)

    def setup(self):
        super(DebianIscsi, self).setup()
        self.addCopySpecs([
            "/etc/iet",
            "/etc/sysctl.d/30-iscsitarget.conf",
            "/etc/default/iscsitarget"
            ])
