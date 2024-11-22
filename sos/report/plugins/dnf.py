# Copyright (C) 2016 Red Hat, Inc., Sachin Patil <sacpatil@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt


class DNFPlugin(Plugin, RedHatPlugin):
    """
    The DNF plugin collects information for the dnf package manager and how it
    is configured for local system.

    By default, this plugin will collect configuration files from /etc/dnf,
    repo files defined in /etc/yum.repos.d/, module information, and various
    'dnf list' commands.

    When using the 'history-info' option, detailed transaction information will
    be collected for the most recent 50 dnf transactions, and will be saved to
    the sos_commands/dnf/history-info directory.
    """

    short_desc = 'dnf package manager'
    plugin_name = "dnf"
    profiles = ('system', 'packagemanager', 'sysmgmt')

    files = ('/etc/dnf/dnf.conf',)
    packages = ('dnf',)

    option_list = [
        PluginOpt('history-info', default=False,
                  desc='collect detailed transaction history')
    ]

    def get_modules_info(self, modules):
        """ Get DN module information """
        if not modules:
            return
        # take just lines with the module names, i.e. containing "[i]" and
        # not the "Hint: [d]efault, [e]nabled, [i]nstalled,.."
        for line in modules.splitlines():
            if "[i]" in line:
                module = line.split()[0]
                if module != "Hint:":
                    self.add_cmd_output("dnf module info " + module,
                                        tags='dnf_module_info')

    def setup(self):

        self.add_file_tags({
            '/etc/dnf/modules.d/.*.module': 'dnf_modules'
        })

        self.add_copy_spec([
            "/etc/dnf/",
            "/etc/yum.conf",
            "/etc/yum/pluginconf.d/",
            "/etc/yum/vars/",
        ])
        self.add_copy_spec("/etc/yum.repos.d/",
                           tags=['yum_repos_d', 'dnf_repos_d', 'dnf_repo'])

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/dnf.*")
        else:
            self.add_copy_spec("/var/log/dnf.log*")
            self.add_copy_spec("/var/log/dnf.librepo.log*")
            self.add_copy_spec("/var/log/dnf.rpm.log*")

        self.add_cmd_output("dnf module list",
                            tags='dnf_module_list')

        self.add_cmd_output([
            "dnf --version",
            "dnf list extras",
            "package-cleanup --dupes",
            "package-cleanup --problems"
        ])

        self.add_cmd_output("dnf list installed",
                            tags=["yum_list_installed", "dnf_list_installed"])

        self.add_cmd_output('dnf -C repolist',
                            tags=['yum_repolist', 'dnf_repolist'])

        self.add_cmd_output('dnf -C repolist --verbose')

        self.add_forbidden_path([
            "/etc/pki/entitlement/key.pem",
            "/etc/pki/entitlement/*-key.pem"
        ])

        self.add_copy_spec([
            "/etc/pki/product/*.pem",
            "/etc/pki/consumer/cert.pem",
            "/etc/pki/entitlement/*.pem"
        ])

        if not self.get_option("history-info"):
            self.add_cmd_output("dnf history", tags='dnf_history')
        else:
            history = self.collect_cmd_output("dnf history",
                                              tags='dnf_history')
            transactions = -1
            if history['output']:
                for line in history['output'].splitlines():
                    try:
                        transactions = int(line.split('|')[0].strip())
                        break
                    except ValueError:
                        # not a valid line to extract transactions from, ignore
                        pass
            for tr_id in range(1, min(transactions+1, 50)):
                self.add_cmd_output(f"dnf history info {tr_id}",
                                    subdir="history-info",
                                    tags='dnf_history_info')

        # Get list of dnf installed modules and their details.
        module_cmd = "dnf module list --installed"
        modules = self.collect_cmd_output(module_cmd)
        self.get_modules_info(modules['output'])

    def postproc(self):
        # Scrub passwords in repositories and yum/dnf variables
        # Example of scrubbing:
        #
        #   password=hackme
        # To:
        #   password=********
        #
        # Whitespace around '=' is allowed.
        regexp = r"(password(\s)*=(\s)*)(\S+)\n"
        repl = r"\1********\n"
        for file in ["/etc/yum.repos.d/*", "/etc/dnf/vars/*"]:
            self.do_path_regex_sub(file, regexp, repl)

        # Scrub password and proxy_password from /etc/dnf/dnf.conf.
        # This uses the same regex patterns as above.
        #
        # Example of scrubbing:
        #
        #   proxy_password = hackme
        # To:
        #   proxy_password = ********
        #
        self.do_file_sub("/etc/dnf/dnf.conf", regexp, repl)

# vim: set et ts=4 sw=4 :
