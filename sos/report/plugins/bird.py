# Copyright (C) 2024 Jake Hunsaker <jacob.r.hunsaker@gmail.com>
# Copyright (C) 2019 Alexander Petrovskiy <alexpe@mellanox.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Bird(Plugin, IndependentPlugin):
    """BIRD is an Internet Routing Daemon used in many *nix and nix-like
    distributions. This plugin will capture the configuration files for a local
    bird installation, as well as runtime information and metrics.
    """

    plugin_name = 'bird'
    profiles = ('network', )
    packages = ('bird', )
    services = ('bird', )

    def setup(self):

        try:
            with open('/etc/bird.conf', 'r', encoding='utf-8') as bfile:
                for line in bfile:
                    if line.startswith('log'):
                        # non-file values will be dropped by add_copy_spec()
                        self.add_copy_spec(line.split()[1].strip('"'))
        except Exception as err:
            self._log_debug(f"Unable to parse bird.conf: {err}")

        self.add_copy_spec([
            "/etc/bird/*",
            "/etc/bird.conf"
        ])

        self.add_cmd_output([
            "birdc show status",
            "birdc show memory",
            "birdc show protocols all",
            "birdc show interfaces",
            "birdc show route all",
            "birdc show symbols",
            "birdc show bfd sessions",
            "birdc show babel interfaces",
            "birdc show babel neighbors",
            "birdc show babel entries",
            "birdc show babel routes",
            "birdc show ospf",
            "birdc show ospf neighbors",
            "birdc show ospf interface",
            "birdc show ospf topology",
            "birdc show ospf state all",
            "birdc show ospf lsadb",
            "birdc show rip interfaces",
            "birdc show rip neighbors",
            "birdc show static"
        ])

    def postproc(self):
        self.do_path_regex_sub('/etc/bird(.*)?.conf',
                               r"((.*password)\s\"(.*)\"(.*))",
                               r"\2 *******\4")

# vim: set et ts=4 sw=4 :
