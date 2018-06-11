# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import os.path
import re


class Corosync(Plugin):
    """ Corosync cluster engine
    """

    plugin_name = "corosync"
    profiles = ('cluster',)
    packages = ('corosync',)

    def setup(self):
        self.add_copy_spec([
            "/etc/corosync",
            "/var/lib/corosync/fdata",
            "/var/log/cluster/corosync.log"
        ])
        self.add_cmd_output([
            "corosync-quorumtool -l",
            "corosync-quorumtool -s",
            "corosync-cpgtool",
            "corosync-cfgtool -s",
            "corosync-blackbox",
            "corosync-objctl -a",
            "corosync-cmapctl"
        ])
        self.call_ext_prog("killall -USR2 corosync")

        corosync_conf = "/etc/corosync/corosync.conf"
        if not os.path.exists(corosync_conf):
            return

        # collect user-defined logfiles, matching either of pattern:
        # log_size: filename
        # or
        # logging.log_size: filename
        # (it isnt precise but sufficient)
        pattern = r'^\s*(logging.)?logfile:\s*(\S+)$'
        try:
            with open("/etc/corosync/corosync.conf") as f:
                for line in f:
                    if re.match(pattern, line):
                        self.add_copy_spec(re.search(pattern, line).group(2))
        except IOError as e:
            self._log_warn("could not read from %s: %s", corosync_conf, e)

    def postproc(self):
        self.do_cmd_output_sub(
            "corosync-objctl",
            r"(.*fence.*\.passwd=)(.*)",
            r"\1******"
        )


class RedHatCorosync(Corosync, RedHatPlugin):

    def setup(self):
        super(RedHatCorosync, self).setup()


class DebianCorosync(Corosync, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super(DebianCorosync, self).setup()

    files = ('/usr/sbin/corosync',)

# vim: set et ts=4 sw=4 :
