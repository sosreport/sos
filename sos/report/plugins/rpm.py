# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Rpm(Plugin, RedHatPlugin):
    """RPM Package Manager
    """

    plugin_name = 'rpm'
    profiles = ('system', 'packagemanager')

    option_list = [("rpmq", "queries for package information via rpm -q",
                    "fast", True),
                   ("rpmva", "runs a verify on all packages", "slow", False),
                   ("rpmdb", "collect /var/lib/rpm", "slow", False)]

    verify_packages = ('rpm',)

    def setup(self):
        self.add_copy_spec("/var/log/rpmpkgs")

        def add_rpm_cmd(query_fmt, filter_cmd, symlink, suggest):
            rpmq_cmd = 'rpm --nodigest -qa --qf=%s' % query_fmt
            shell_cmd = rpmq_cmd
            if filter_cmd:
                shell_cmd = "sh -c '%s'" % (rpmq_cmd + "|" + filter_cmd)
            self.add_cmd_output(shell_cmd, root_symlink=symlink,
                                suggest_filename=suggest)

        if self.get_option("rpmq"):
            # basic installed-rpms
            query_fmt = '"%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}~~'
            query_fmt = query_fmt + '%{INSTALLTIME:date}\n"'

            filter_cmd = 'awk -F "~~" ' \
                r'"{printf \"%-59s %s\n\",\$1,\$2}"|sort -V'

            add_rpm_cmd(query_fmt, filter_cmd, "installed-rpms", None)

            # extended package data
            query_fmt = '"%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\\t'
            query_fmt = query_fmt + '%{INSTALLTIME:date}\\t%{INSTALLTIME}\\t'
            query_fmt = query_fmt + '%{VENDOR}\\t%{BUILDHOST}\\t'
            query_fmt = query_fmt + '%{SIGPGP}\\t%{SIGPGP:pgpsig}\\n"'

            add_rpm_cmd(query_fmt, None, None, "package-data")

        if self.get_option("rpmva"):
            self.add_cmd_output("rpm -Va", root_symlink="rpm-Va",
                                timeout=180)

        if self.get_option("rpmdb"):
            self.add_cmd_output("lsof +D /var/lib/rpm",
                                suggest_filename='lsof_D_var_lib_rpm')
            self.add_copy_spec("/var/lib/rpm")

# vim: set et ts=4 sw=4 :
