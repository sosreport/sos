# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class LibvirtClient(Plugin, IndependentPlugin):

    short_desc = 'client for libvirt virtualization API'

    plugin_name = 'virsh'
    profiles = ('system', 'virt')

    packages = ('libvirt-client',)

    def setup(self):
        # virt-manager logs
        self.add_copy_spec([
            "/root/.cache/virt-manager/*.log",
            "/root/.virt-manager/*.log"
        ])

        cmd = 'virsh -r'

        # get host information
        subcmds = [
            'domcapabilities',
            'capabilities',
            'nodeinfo',
            'freecell --all',
            'node-memory-tune',
            'version',
            'pool-capabilities',
            'nodecpumap',
            'maxvcpus kvm',
            'sysinfo',
            'nodedev-list --tree',
        ]

        for subcmd in subcmds:
            self.add_cmd_output('%s %s' % (cmd, subcmd), foreground=True)

        self.add_cmd_output("%s list --all" % cmd,
                            tags="virsh_list_all", foreground=True)

        # get network, pool and nwfilter elements
        for k in ['net', 'nwfilter', 'pool']:
            k_list = self.collect_cmd_output('%s %s-list %s' % (cmd, k, '--all'
                                             if k in ['net', 'pool'] else ''),
                                             foreground=True)
            if k_list['status'] == 0:
                k_lines = k_list['output'].splitlines()
                # the 'Name' column position changes between virsh cmds
                # catch the rare exceptions when 'Name' is not found
                try:
                    pos = k_lines[0].split().index('Name')
                except Exception:  # pylint: disable=broad-except
                    continue
                for j in filter(lambda x: x, k_lines[2:]):
                    name = j.split()[pos]
                    self.add_cmd_output('%s %s-dumpxml %s' % (cmd, k, name),
                                        foreground=True)

        # cycle through the VMs/domains list, ignore 2 header lines and latest
        # empty line, and dumpxml domain name in 2nd column
        domains_output = self.exec_cmd('%s list --all' % cmd, foreground=True)
        if domains_output['status'] == 0:
            domains_lines = domains_output['output'].splitlines()[2:]
            for domain in filter(lambda x: x, domains_lines):
                domain = domain.split()[1]
                for opt in ['dumpxml', 'dominfo', 'domblklist']:
                    self.add_cmd_output('%s %s %s' % (cmd, opt, domain),
                                        foreground=True)

        nodedev_output = self.exec_cmd(f"{cmd} nodedev-list", foreground=True)
        if nodedev_output['status'] == 0:
            for name in nodedev_output['output'].splitlines():
                self.add_cmd_output(
                    f"{cmd} nodedev-dumpxml {name}",
                    foreground=True
                )

    def postproc(self):
        match_exp = r"(\s*passwd\s*=\s*\")([^\"]*)(\".*)"
        virsh_path_exps = [
            r"/root/\.cache/virt-manager/.*\.log",
            r"/root/\.virt-manager/.*\.log"
        ]
        for path_exp in virsh_path_exps:
            # Scrub passwords in virt-manager logs
            # Example of scrubbing:
            #
            #   passwd="hackme"
            # To:
            #   passwd="******"
            #
            self.do_path_regex_sub(path_exp, match_exp, r"\1******\3")
# vim: et ts=4 sw=4
