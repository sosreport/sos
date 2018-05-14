# Copyright (C) 2016 Red Hat, Inc., Sachin Patil <sacpatil@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin


class DNFPlugin(Plugin, RedHatPlugin):
    """dnf package manager"""
    plugin_name = "dnf"
    profiles = ('system', 'packagemanager', 'sysmgmt')

    files = ('/etc/dnf/dnf.conf',)
    packages = ('dnf',)

    option_list = [
        ("history", "captures transaction history", "fast", False),
        ("history-info", "detailed transaction history", "slow", False),
    ]

    def get_modules_info(self, module_file):
        if module_file:
            try:
                module_out = open(module_file).read()
            except:
                self._log_warn("could not read module list file")
                return
            # take just lines with the module names, i.e. containing "[i]" and
            # not the "Hint: [d]efault, [e]nabled, [i]nstalled,.."
            for line in module_out.splitlines():
                if "[i]" in line:
                    module = line.split()[0]
                    if module != "Hint:":
                        self.add_cmd_output("dnf module info "+module)

    def setup(self):
        self.add_copy_spec([
            "/etc/dnf/dnf.conf",
            "/etc/dnf/plugins/*",
            "/etc/dnf/protected.d/*",
        ])

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/dnf.*", sizelimit=self.limit)
        else:
            self.add_copy_spec("/var/log/dnf.log", sizelimit=self.limit)
            self.add_copy_spec("/var/log/dnf.librepo.log",
                               sizelimit=self.limit)
            self.add_copy_spec("/var/log/dnf.rpm.log", sizelimit=self.limit)

        self.add_cmd_output([
            "dnf --version",
            "dnf list installed *dnf*",
            "dnf list extras",
            "package-cleanup --dupes",
            "package-cleanup --problems"
        ])

        if self.get_option("history"):
            self.add_cmd_output("dnf history")

        if self.get_option("history-info"):
            history = self.call_ext_prog("dnf history")
            transactions = -1
            if history['output']:
                for line in history['output'].splitlines():
                    try:
                        transactions = int(line.split('|')[0].strip())
                        break
                    except ValueError:
                        pass
            for tr_id in range(1, transactions+1):
                self.add_cmd_output("dnf history info %d" % tr_id)

        # Get list of dnf installed modules and their details.
        module_file = self.get_cmd_output_now("dnf module list --installed")
        self.get_modules_info(module_file)

# vim: set et ts=4 sw=4 :
