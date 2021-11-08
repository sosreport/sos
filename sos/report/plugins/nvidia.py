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
    commands = ('nvidia-smi',)

    def setup(self):
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

        self.add_cmd_output(["nvidia-smi %s" % cmd for cmd in subcmds])

        query = ('gpu_name,gpu_bus_id,vbios_version,temperature.gpu,'
                 'utilization.gpu,memory.total,memory.free,memory.used,'
                 'clocks.applications.graphics,clocks.applications.memory')
        querypages = ('timestamp,gpu_bus_id,gpu_serial,gpu_uuid,'
                      'retired_pages.address,retired_pages.cause')
        self.add_cmd_output("nvidia-smi --query-gpu=%s --format=csv" % query)
        self.add_cmd_output(
            "nvidia-smi --query-retired-pages=%s --format=csv" % querypages
        )
        self.add_journal(boot=0, identifier='nvidia-persistenced')

# vim: set et ts=4 sw=4 :
