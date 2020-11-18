# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class NfsGanesha(Plugin, IndependentPlugin):

    short_desc = 'NFS-Ganesha file server information'
    plugin_name = 'nfsganesha'
    profiles = ('storage', 'network', 'nfs')
    packages = ('nfs-ganesha',)

    def setup(self):
        self.add_copy_spec([
            "/etc/ganesha",
            "/etc/sysconfig/ganesha",
            "/run/sysconfig/ganesha",
            "/var/log/ganesha/*.log"
        ])

        if self.get_option("all_logs"):
            # Grab rotated logs as well
            self.add_copy_spec("/var/log/ganesha/*.log*")

        self.add_cmd_output([
            "dbus-send --type=method_call --print-reply"
            " --system --dest=org.ganesha.nfsd "
            "/org/ganesha/nfsd/ExportMgr "
            "org.ganesha.nfsd.exportmgr.ShowExports"
        ])

        return


# vim: set et ts=4 sw=4 :
