# Copyright (C) 2016 Red Hat, Inc., Tomas Tomecek <ttomecek@redhat>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import os

from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Npm(Plugin, IndependentPlugin):

    short_desc = 'Information from available npm modules'
    plugin_name = 'npm'
    profiles = ('system',)
    option_list = [
        PluginOpt('project_path', default='', val_type=str,
                  desc='Collect npm modules of project at this path')
    ]

    # in Fedora, Debian, Ubuntu and Suse the package is called npm
    packages = ('npm',)

    def _get_npm_output(self, cmd, filename, working_directory=None):
        # stderr output is already part of the json, key "problems"
        self.add_cmd_output(
            cmd,
            suggest_filename=filename,
            stderr=False,
            runat=working_directory
        )

    def setup(self):
        if self.get_option("project_path"):
            project_path = os.path.abspath(os.path.expanduser(
                self.get_option("project_path")))
            self._get_npm_output("npm ls --json", "npm_ls_project",
                                 working_directory=project_path)
            self._get_npm_output("npm config list -l",
                                 "npm_config_list_project",
                                 working_directory=project_path)

        self._get_npm_output("npm ls -g --json", "npm_ls_global")
        self._get_npm_output("npm config list -l", "npm_config_list_global")


class NpmViaNodeJS(Npm):
    """
    some distribution methods don't provide 'npm' via npm package
    """

    # upstream doesn't have an npm package, it's just nodejs
    # also in Fedora 24+ it is just nodejs, no npm package
    packages = ('nodejs', )

# TODO: in RHEL npm and nodejs is available via software collections
#       this should be handled separately

# vim: set et ts=4 sw=4 :
