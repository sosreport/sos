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


class Rpm(Plugin, RedHatPlugin):
    """RPM Package Manager
    """

    plugin_name = 'rpm'
    profiles = ('system', 'packagemanager')

    option_list = [("rpmq", "queries for package information via rpm -q",
                    "fast", True),
                   ("rpmva", "runs a verify on all packages", "slow", False)]

    verify_list = [
        'kernel$', 'glibc', 'initscripts',
        'pam_.*',
        'java.*', 'perl.*',
        'rpm', 'yum',
        'spacewalk.*',
    ]

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
                '"{printf \\"%-59s %s\\n\\",\$1,\$2}"|sort -f'

            add_rpm_cmd(query_fmt, filter_cmd, "installed-rpms", None)

            # extended package data
            query_fmt = '"%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\\t'
            query_fmt = query_fmt + '%{INSTALLTIME:date}\\t%{INSTALLTIME}\\t'
            query_fmt = query_fmt + '%{VENDOR}\\t%{BUILDHOST}\\t'
            query_fmt = query_fmt + '%{SIGPGP}\\t%{SIGPGP:pgpsig}\\n"'

            add_rpm_cmd(query_fmt, None, None, "package-data")

        if self.get_option("verify"):
            if self.get_option("rpmva"):
                self.add_cmd_output("rpm -Va", root_symlink="rpm-Va",
                                    timeout=180)
            else:
                pkgs_by_regex = \
                    self.policy().package_manager.all_pkgs_by_name_regex
                verify_list = map(pkgs_by_regex, self.verify_list)
                verify_pkgs = ""
                for pkg_list in verify_list:
                    for pkg in pkg_list:
                        if 'debuginfo' in pkg or 'devel' in pkg:
                            continue
                        verify_pkgs = "%s %s" % (verify_pkgs, pkg)
                self.add_cmd_output("rpm -V %s" % verify_pkgs)


# vim: set et ts=4 sw=4 :
