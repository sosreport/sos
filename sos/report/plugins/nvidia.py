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
    commands = ('nvidia-smi', 'nvidia-ctk', 'dcgmi')
    files = (
        '/proc/driver/nvidia',
        '/var/log/nvidia-installer.log',
    )
    services = (
        'nvidia-persistenced',
        'nvidia-fabricmanager',
        'nvidia-imex',
        'nvidia-dcgm',
        'dcgm',
        'nvidia-toolkit-firstboot',
    )

    def setup(self):
        self.add_copy_spec([
            "/etc/cdi/nvidia.yaml",
            "/var/log/nvidia-installer.log*",
            "/var/lib/dkms/nvidia*/*/build/make.log",
            "/var/lib/dkms/nvidia*/*/*/log/make.log",
            "/var/lib/dkms/nvidia*/*/*/*/log/make.log",
            "/var/log/fabricmanager.log*",
            "/usr/share/nvidia/nvswitch/fabricmanager.cfg",
            "/etc/nvidia-imex/*.cfg",
            "/var/log/nvidia-imex*.log*",
            "/var/log/nv-hostengine.log*",
        ])

        subcmds = [
            '--list-gpus',
            '-q -d PERFORMANCE',
            '-q -d SUPPORTED_CLOCKS',
            '-q -d PAGE_RETIREMENT',
            '-q -d ROW_REMAPPER',
            '-q',
            '-q -d ECC',
            'nvlink -s',
            'nvlink -e',
            'topo -m',
            'topo -p2p r',
            'vgpu',
            'vgpu -q',
        ]
        ctk_subcmds = [
            'cdi list',
            '--version',
        ]
        dcgmi_subcmds = [
            '--version',
            'discovery -l',
        ]
        self.add_cmd_output([f"nvidia-smi {cmd}" for cmd in subcmds])
        self.add_cmd_output([f"nvidia-ctk {cmd}" for cmd in ctk_subcmds])
        self.add_cmd_output([f"dcgmi {cmd}" for cmd in dcgmi_subcmds])

        query = ('gpu_name,gpu_bus_id,vbios_version,temperature.gpu,'
                 'utilization.gpu,memory.total,memory.free,memory.used,'
                 'clocks.applications.graphics,clocks.applications.memory')
        telemetry_query = (
            'index,gpu_name,gpu_bus_id,uuid,serial,vbios_version,pstate,'
            'clocks.current.sm,clocks.max.sm,'
            'power.draw,power.limit,temperature.gpu,temperature.memory,'
            'clocks_throttle_reasons.active,'
            'clocks_throttle_reasons.hw_slowdown,'
            'clocks_throttle_reasons.hw_thermal_slowdown,'
            'clocks_throttle_reasons.hw_power_brake_slowdown,'
            'clocks_throttle_reasons.sw_power_cap,'
            'ecc.errors.uncorrected.volatile.total,'
            'ecc.errors.uncorrected.aggregate.total,'
            'retired_pages.sbe,retired_pages.dbe,retired_pages.pending'
        )
        querypages = ('timestamp,gpu_bus_id,gpu_serial,gpu_uuid,'
                      'retired_pages.address,retired_pages.cause')
        self.add_cmd_output(f"nvidia-smi --query-gpu={query} --format=csv")
        self.add_cmd_output(
            f"nvidia-smi --query-gpu={telemetry_query} --format=csv"
        )
        self.add_cmd_output(
            f"nvidia-smi --query-retired-pages={querypages} --format=csv"
        )
        self.add_copy_spec(["/sys/class/mdev_bus", "/sys/bus/mdev"])

# vim: set et ts=4 sw=4 :
