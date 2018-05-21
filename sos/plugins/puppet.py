# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from glob import glob


class Puppet(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Puppet service
    """

    plugin_name = 'puppet'
    profiles = ('services',)

    def setup(self):
        self.add_copy_spec([
            "/etc/puppet/*.conf",
            "/etc/puppet/rack/*",
            "/etc/puppet/manifests/*",
            "/var/log/puppet/*.log",
        ])

    def postproc(self):
        for device_conf in glob("/etc/puppet/device.conf*"):
            self.do_file_sub(
                device_conf,
                r"(.*url*.ssh://.*:).*(@.*)",
                r"\1%s\2" % ('***')
            )

        return
# vim: et ts=4 sw=4
