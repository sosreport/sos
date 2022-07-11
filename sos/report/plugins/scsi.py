# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from glob import glob
from sos.report.plugins import Plugin, IndependentPlugin


class Scsi(Plugin, IndependentPlugin):
    """
    Collects various information about the SCSI devices install on the host
    system.

    This plugin will capture a large amount of data from the /sys filesystem,
    as well as several different invocations of the `lsscsi` command.

    Additionally, several `sg_persist` commands will be collected for each
    SCSI device identified by sos. Note that in most cases these commands are
    provided by the `sg3_utils` package which may not be present by default.
    """

    short_desc = 'SCSI devices'

    plugin_name = 'scsi'
    profiles = ('storage', 'hardware')

    def setup(self):
        self.add_copy_spec([
            "/proc/scsi",
            "/etc/stinit.def",
            "/sys/bus/scsi",
            "/sys/class/scsi_host",
            "/sys/class/scsi_disk",
            "/sys/class/scsi_device",
            "/sys/class/scsi_generic"
        ])

        scsi_types = ["enclosu"]
        result = self.collect_cmd_output('lsscsi -g')
        if result['status'] == 0:
            for line in result['output'].splitlines():
                if (line.split()[1] in scsi_types):
                    devsg = line.split()[-1]
                    self.add_cmd_output("sg_ses -p2 -b1 %s" % devsg)

        self.add_cmd_output("lsscsi -i", suggest_filename="lsscsi")

        self.add_cmd_output([
            "sg_map -x",
            "lspath",
            "lsmap -all",
            "lsnports",
            "lsscsi -H",
            "lsscsi -d",
            "lsscsi -s",
            "lsscsi -L"
        ])

        scsi_hosts = glob("/sys/class/scsi_host/*")
        self.add_device_cmd("udevadm info -a %(dev)s", devices=scsi_hosts)

        self.add_device_cmd([
            "sg_persist --in -k -d %(dev)s",
            "sg_persist --in -r -d %(dev)s",
            "sg_persist --in -s -d %(dev)s",
            "sg_inq %(dev)s"
        ], devices='block', whitelist=['sd.*'])

# vim: set et ts=4 sw=4 :
