# Copyright (C) 2016 Red Hat, Inc., Sachin Patil <sacpatil@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class DNFPlugin(Plugin, RedHatPlugin):

    short_desc = 'dnf package manager'
    plugin_name = "dnf"
    profiles = ('system', 'packagemanager', 'sysmgmt')

    files = ('/etc/dnf/dnf.conf',)
    packages = ('dnf',)

    option_list = [
        ("history", "captures transaction history", "fast", False),
        ("history-info", "detailed transaction history", "slow", False),
    ]

    def get_modules_info(self, modules):
        if not modules:
            return
        # take just lines with the module names, i.e. containing "[i]" and
        # not the "Hint: [d]efault, [e]nabled, [i]nstalled,.."
        for line in modules.splitlines():
            if "[i]" in line:
                module = line.split()[0]
                if module != "Hint:":
                    self.add_cmd_output("dnf --assumeno module info " + module,
                                        tags='dnf_module_info')

    def setup(self):

        self.add_file_tags({
            '/etc/dnf/modules.d/.*.modules': 'dnf_modules'
        })

        self.add_copy_spec("/etc/dnf/")

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/dnf.*")
        else:
            self.add_copy_spec("/var/log/dnf.log*")
            self.add_copy_spec("/var/log/dnf.librepo.log*")
            self.add_copy_spec("/var/log/dnf.rpm.log*")

        self.add_cmd_output("dnf --assumeno module list",
                            tags='dnf_module_list')

        self.add_cmd_output([
            "dnf --version",
            "dnf --assumeno list installed *dnf*",
            "dnf --assumeno list extras",
            "package-cleanup --dupes",
            "package-cleanup --problems"
        ])

        if self.get_option("history") and not self.get_option("history-info"):
            self.add_cmd_output("dnf history")

        if self.get_option("history-info"):
            history = self.collect_cmd_output("dnf history")
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
        module_cmd = "dnf --assumeno module list --installed"
        modules = self.collect_cmd_output(module_cmd)
        self.get_modules_info(modules['output'])

# vim: set et ts=4 sw=4 :
