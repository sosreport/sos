# Copyright (C) 2025 Canonical Ltd.,
#                    Bryan Fraschetti <bryan.fraschetti@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class PulseAudio(Plugin, IndependentPlugin):
    """The PulseAudio plugin collects information about the system's inputs
    sources, output sinks, detected sound cards, and pulse audio's
    configuration
    """

    short_desc = 'The sound server audio middleware'
    plugin_name = "pulseaudio"
    profiles = ('system', 'desktop', 'hardware')

    packages = ('pulseaudio-utils', 'pulseaudio')

    pactl_cmd = "pactl"
    pulseaudio_cmd = "pulseaudio"

    def setup(self):
        pactl_subcmds = [
            'list sinks',
            'list sources',
            'list cards',
            'info',
            'stat',
            '--version'
        ]

        pulseaudio_subcmds = [
            '--dump-conf',
            '--dump-modules',
            '--check'
        ]

        self.add_cmd_output([
            f"{self.pactl_cmd} {subcmd}" for subcmd in pactl_subcmds
        ])
        self.add_cmd_output([
            f"{self.pulseaudio_cmd} {subcmd}" for subcmd in pulseaudio_subcmds
        ])

        self.add_copy_spec("/etc/pulse/*")

# vim: set et ts=4 sw=4 :
