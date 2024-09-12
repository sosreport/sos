# Copyright (C) 2019 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos.report.plugins import Plugin, IndependentPlugin


class Nvidia(Plugin, IndependentPlugin):

    short_desc = 'Nvidia GPU information'
    plugin_name = 'nvidia'
    commands = ('nvidia-smi', 'nvidia-ctk',)
    services = ('nvidia-persistenced', 'nvidia-fabricmanager',
                'nvidia-toolkit-firstboot')

    def setup(self):
        self.add_copy_spec("/etc/cdi/nvidia.yaml")

        subcmds = [
            '--list-gpus',
            '-q -d PERFORMANCE',
            '-q -d SUPPORTED_CLOCKS',
            '-q -d PAGE_RETIREMENT',
            '-q',
            '-q -d ECC',
            'nvlink -s',
            'nvlink -e'
        ]
        ctk_subcmds = [
            'cdi list',
            '--version',
        ]
        self.add_cmd_output([f"nvidia-smi {cmd}" for cmd in subcmds])
        self.add_cmd_output([f"nvidia-ctk {cmd}" for cmd in ctk_subcmds])

        query = ('gpu_name,gpu_bus_id,vbios_version,temperature.gpu,'
                 'utilization.gpu,memory.total,memory.free,memory.used,'
                 'clocks.applications.graphics,clocks.applications.memory')
        querypages = ('timestamp,gpu_bus_id,gpu_serial,gpu_uuid,'
                      'retired_pages.address,retired_pages.cause')
        self.add_cmd_output(f"nvidia-smi --query-gpu={query} --format=csv")
        self.add_cmd_output(
            f"nvidia-smi --query-retired-pages={querypages} --format=csv"
        )

# vim: set et ts=4 sw=4 :
