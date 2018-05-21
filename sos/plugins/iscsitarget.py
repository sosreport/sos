# Copyright (C) 2007-2012 Red Hat, Inc., Ben Turner <bturner@redhat.com>
# Copyright (C) 2012 Adam Stokes <adam.stokes@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
