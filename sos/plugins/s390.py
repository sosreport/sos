# Copyright (C) 2007 Red Hat, Inc., Justin Payne <jpayne@redhat.com>

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


class S390(Plugin, RedHatPlugin):
    """IBM S/390
    """

    plugin_name = 's390'
    profiles = ('system', 'hardware')

    # Check for s390 arch goes here

    def check_enabled(self):
        return (self.policy().get_arch() == "s390")

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
            "/etc/zipl.conf",
            "/etc/zfcp.conf",
            "/etc/sysconfig/dumpconf",
            "/etc/src_vipa.conf",
            "/etc/ccwgroup.conf",
            "/etc/chandev.conf"])
        self.add_cmd_output([
            "lscss",
            "lsdasd",
            "lstape",
            "find /proc/s390dbf -type f",
            "qethconf list_all",
            "lsqeth",
            "lszfcp"
        ])
        r = self.call_ext_prog("ls /dev/dasd?")
        dasd_dev = r['output']
        for x in dasd_dev.split('\n'):
            self.add_cmd_output([
                "dasdview -x -i -j -l -f %s" % (x,),
                "fdasd -p %s" % (x,)
            ])


# vim: set et ts=4 sw=4 :
