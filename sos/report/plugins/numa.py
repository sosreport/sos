# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin
import os.path


class Numa(Plugin, IndependentPlugin):

    short_desc = 'NUMA state and configuration'

    plugin_name = 'numa'
    profiles = ('hardware', 'system', 'memory', 'performance')

    packages = ('numad', 'numactl')

    def setup(self):
        numa_path = "/sys/devices/system/node"

        self.add_file_tags({
            "%s/node.*/cpulist": 'numa_cpus'
        })

        self.add_copy_spec([
            "/etc/numad.conf",
            "/etc/logrotate.d/numad"
        ])
        self.add_copy_spec("/var/log/numad.log*")
        self.add_cmd_output([
            "numastat",
            "numastat -m",
            "numastat -n",
            "numactl --show",
            "numactl --hardware",
        ])

        self.add_copy_spec([
            os.path.join(numa_path, "node*/meminfo"),
            os.path.join(numa_path, "node*/cpulist"),
            os.path.join(numa_path, "node*/distance"),
            os.path.join(numa_path, "node*/hugepages/hugepages-*/*")
        ])

# vim: set et ts=4 sw=4 :
