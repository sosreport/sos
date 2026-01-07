# Copyright (C) 2026 Canonical Ltd.,
#                    Bryan Fraschetti <bryan.fraschetti@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import pwd
from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class PipeWire(Plugin, IndependentPlugin):
    """The PipeWire plugin collects information about the system's input
    and output devices, their configuration, metadata, and map of logical
    signal flow as managed by PipeWire
    """

    short_desc = 'A low-level multimedia framework for audio-visual playback'
    plugin_name = "pipewire"
    profiles = ('system', 'desktop', 'hardware')

    packages = ('pipewire-bin', 'pipewire-utils', 'pipewire')

    # PipeWire is scoped to user-session, but `sudo sos report` will cause
    # the commands to run in root context. If the logged in user is not root,
    # the commands will fail with 'Error: "failed to connect: Host is down"'.
    # Therefore, add an option to specify user context for the commands
    option_list = [
        PluginOpt(
            'user',
            val_type=str,
            default="root",
            desc='Run PipeWire commands as a specific user',
        ),
    ]

    def setup(self):

        user = self.get_option('user')
        uid = pwd.getpwnam(user).pw_uid
        env = {
            "XDG_RUNTIME_DIR": f"/run/user/{uid}",
            "DBUS_SESSION_BUS_ADDRESS": f"unix:path=/run/user/{uid}/bus",
        }

        cmds = [
            "pipewire --version",
            "pw-config paths",
            "pw-config list",
            "pw-cli list-remotes",
            "pw-cli list-objects",
            "pw-cli info all",
            "pw-dump",
            "pw-link -oIv",
            "pw-link -iIv",
            "pw-link -lIv",
            "pw-metadata",
            "pw-metadata -l",
            "pw-dot -ad",
            "spa-acp-tool list-verbose",
            "spa-acp-tool info",
        ]

        for cmd in cmds:
            self.add_cmd_output(cmd, runas=user, env=env)

        self.add_copy_spec([
            "/etc/pipewire/*",
            "pw.dot",  # Convert filetype with dot -T<dst-type> pw.dot > pw.ext
        ])

# vim: set et ts=4 sw=4 :
