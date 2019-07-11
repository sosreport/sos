# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class KDump(Plugin):
    """Kdump crash dumps
    """

    plugin_name = "kdump"
    profiles = ('system', 'debug')

    def setup(self):
        self.add_copy_spec([
            "/proc/cmdline"
        ])


class RedHatKDump(KDump, RedHatPlugin):

    files = ('/etc/kdump.conf',)
    packages = ('kexec-tools',)

    def find_crash_dir(self, conf_file):
        """ Get crash directory as specified in /etc/kdump.conf
            by line:

            path /path/to/dir

            Use /var/crash/ as default.
        """
        try:
            with open(conf_file, 'r') as conf_f:
                for line in conf_f:
                    words = line.split()[:2]
                    if len(words) > 1 and words[0] == "path":
                        return words[1]
        except (OSError, IOError) as e:
            self._log_warn("Could not read %s: %s" % (conf_file, e))

        return "/var/crash/"

    def setup(self):
        conf_file = "/etc/kdump.conf"
        crash_dir = self.find_crash_dir(conf_file)
        self.add_copy_spec([
            conf_file,
            "/etc/udev/rules.d/*kexec.rules",
            "%s/*/vmcore-dmesg.txt" % crash_dir
        ])


class DebianKDump(KDump, DebianPlugin, UbuntuPlugin):

    files = ('/etc/default/kdump-tools',)
    packages = ('kdump-tools',)

    def setup(self):
        self.add_copy_spec([
            "/etc/default/kdump-tools"
        ])

# vim: set et ts=4 sw=4 :
