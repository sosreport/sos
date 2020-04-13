# Copyright (C) 2007 Red Hat, Inc., Justin Payne <jpayne@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class S390(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """IBM S/390
    """

    plugin_name = 's390'
    profiles = ('system', 'hardware')

    # Check for s390 arch goes here

    def check_enabled(self):
        return ("s390" in self.policy.get_arch())

    # Gather s390 specific information

    def setup(self):
        self.add_copy_spec([
            "/proc/cio_ignore",
            "/proc/crypto",
            "/proc/dasd/devices",
            "/proc/dasd/statistics",
            "/proc/qeth",
            "/proc/qeth_perf",
            "/proc/qeth_ipa_takeover",
            "/proc/sys/appldata/*",
            "/proc/sys/kernel/hz_timer",
            "/proc/sysinfo",
            "/sys/bus/ccwgroup/drivers/qeth/0.*/*",
            "/sys/bus/ccw/drivers/zfcp/0.*/*",
            "/sys/bus/ccw/drivers/zfcp/0.*/0x*/*",
            "/sys/bus/ccw/drivers/zfcp/0.*/0x*/0x*/*",
            "/sys/kernel/debug/s390dbf",
            "/etc/zipl.conf",
            "/etc/zfcp.conf",
            "/etc/sysconfig/dumpconf",
            "/etc/src_vipa.conf",
            "/etc/ccwgroup.conf",
            "/etc/chandev.conf"
        ])

        # skip flush as it is useless for sos collection
        self.add_forbidden_path("/sys/kernel/debug/s390dbf/*/flush")

        self.add_cmd_output([
            "lscss",
            "lsdasd",
            "lstape",
            "qethconf list_all",
            "lsqeth",
            "lszfcp",
            "lszcrypt",
            "icainfo",
            "icastats"
        ])

        r = self.exec_cmd("ls /dev/dasd?")
        dasd_dev = r['output']
        for x in dasd_dev.split('\n'):
            self.add_cmd_output([
                "dasdview -x -i -j -l -f %s" % (x,),
                "fdasd -p %s" % (x,)
            ])


# vim: set et ts=4 sw=4 :
