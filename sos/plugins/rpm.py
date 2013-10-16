### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin

class Rpm(Plugin, RedHatPlugin):
    """RPM information
    """

    plugin_name = 'rpm'

    option_list = [("rpmq", "queries for package information via rpm -q", "fast", True),
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

        if self.get_option("rpmq"):
            self.add_cmd_output("rpm -qa --qf="
                "\"%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}~~"
                "%{INSTALLTIME:date}\t%{INSTALLTIME}\t%{VENDOR}\n\""
                " --nosignature --nodigest | awk -F '~~' "
                "'{printf \"%-59s %s\\n\",$1,$2}'|sort",
                root_symlink = "installed-rpms")

        if self.get_option("rpmva"):
            self.add_cmd_output("rpm -Va", root_symlink = "rpm-Va", timeout = 3600)
        else:
            pkgs_by_regex = self.policy().package_manager.all_pkgs_by_name_regex
            verify_list = map(pkgs_by_regex, self.verify_list)
            for pkg_list in verify_list:
                for pkg in pkg_list:
                    if 'debuginfo' in pkg \
                    or pkg.endswith('-debuginfo-common'):
                        continue
                    self.add_cmd_output("rpm -V %s" % pkg)
