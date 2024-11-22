# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
from sos.report.plugins import Plugin, IndependentPlugin


class Composer(Plugin, IndependentPlugin):

    short_desc = 'OSBuild Composer'

    plugin_name = 'composer'
    profiles = ('sysmgmt', 'virt', )

    packages = (
        'composer-cli',
        'weldr-client',
        'cockpit-composer',
        'osbuild-composer',
    )

    def _get_entries(self, cmd):
        entries = []
        ent_file = self.collect_cmd_output(cmd)
        if ent_file['status'] == 0:
            for line in ent_file['output'].splitlines():
                entries.append(line)
        return entries

    def setup(self):
        self.add_copy_spec([
            "/etc/osbuild-composer/osbuild-composer.toml",
            "/etc/osbuild-worker/osbuild-worker.toml",
            "/etc/lorax/composer.conf",
            "/etc/osbuild-composer",
            "/var/log/lorax-composer/composer.log",
            "/var/log/lorax-composer/dnf.log",
            "/var/log/lorax-composer/program.log",
            "/var/log/lorax-composer/server.log"
        ])
        blueprints = self._get_entries("composer-cli blueprints list")
        for blueprint in blueprints:
            self.add_cmd_output(f"composer-cli blueprints show {blueprint}")

        sources = self._get_entries("composer-cli sources list")
        for src in sources:
            self.add_cmd_output(f"composer-cli sources info {src}")

        composes = self._get_entries("composer-cli compose list")
        for compose in composes:
            # the first column contains the compose id
            self.add_cmd_output(
                f"composer-cli compose log {compose.split(' ')[0]}"
            )

        self.add_journal(units=[
            "osbuild-composer.service",
            "osbuild-worker@*.service",
        ])

# vim: set et ts=4 sw=4 :
