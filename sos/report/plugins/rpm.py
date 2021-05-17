# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Rpm(Plugin, RedHatPlugin):

    short_desc = 'RPM Package Manager'

    plugin_name = 'rpm'
    profiles = ('system', 'packagemanager')

    option_list = [("rpmq", "queries for package information via rpm -q",
                    "fast", True),
                   ("rpmva", "runs a verify on all packages", "slow", False),
                   ("rpmdb", "collect /var/lib/rpm", "slow", False)]

    verify_packages = ('rpm',)

    def setup(self):
        self.add_copy_spec("/var/log/rpmpkgs")

        if self.get_option("rpmq"):
            rpmq = "rpm --nodigest -qa --qf=%s"
            # basic installed-rpms
            nvra = '"%-59{NVRA} %{INSTALLTIME:date}\n"'
            irpms = "sh -c '%s | sort -V'" % rpmq % nvra

            self.add_cmd_output(irpms, root_symlink='installed-rpms',
                                tags='installed_rpms')

            # extended package data
            extpd = (
                '"%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\\t'
                '%{INSTALLTIME:date}\\t%{INSTALLTIME}\\t'
                '%{VENDOR}\\t%{BUILDHOST}\\t'
                '%{SIGPGP}\\t%{SIGPGP:pgpsig}\\n"'
            )

            self.add_cmd_output(rpmq % extpd, suggest_filename='package-data',
                                tags=['installed_rpms', 'package_data'])

        if self.get_option("rpmva"):
            self.plugin_timeout = 1000
            self.add_cmd_output("rpm -Va", root_symlink="rpm-Va",
                                timeout=900, priority=100)

        if self.get_option("rpmdb"):
            self.add_cmd_output("lsof +D /var/lib/rpm",
                                suggest_filename='lsof_D_var_lib_rpm')
            self.add_copy_spec("/var/lib/rpm")

        self.add_cmd_output("rpm --showrc")

# vim: set et ts=4 sw=4 :
