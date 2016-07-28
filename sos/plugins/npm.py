# Copyright (C) 2016 Red Hat, Inc., Tomas Tomecek <ttomecek@redhat>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
import os
import pwd
import json

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin, \
    SuSEPlugin


class Npm(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin, SuSEPlugin):
    """
    Get info about available npm modules
    """

    requires_root = False
    plugin_name = 'npm'
    profiles = ('system',)
    option_list = [("project_path",
                    'List npm modules of a project specified by path',
                    'fast',
                    0)]

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

    def _find_modules_in_npm_cache(self):
        """
        since format of `~/.npm` is changing with newer npm releases, let's do
        the easiest thing and don't predict nor expect anything, the structure
        is suppose to be:

        ~/.npm
        |-- asap
        |   `-- 2.0.4
        |-- dezalgo
        |   |-- 1.0.2
        |   `-- 1.0.3
        """
        output = []

        for p in pwd.getpwall():
            user_cache = os.path.join(p.pw_dir, ".npm")
            try:
                # most of these stand for names of modules
                module_names = os.listdir(user_cache)
            except OSError:
                self._log_debug("Skipping directory %s" % user_cache)
                continue
            else:
                for m in module_names:
                    module_path = os.path.join(user_cache, m)
                    try:
                        versions = os.listdir(module_path)
                    except OSError:
                        continue
                    else:
                        output.append({m: versions})
        outfn = self._make_command_filename("npm-cache-modules")
        self.archive.add_string(json.dumps(output), outfn)

    def setup(self):
        if self.get_option("project_path") != 0:
            project_path = os.path.abspath(os.path.expanduser(
                self.get_option("project_path")))
            self._get_npm_output("npm ls --json", "npm-ls-project",
                                 working_directory=project_path)
        self._get_npm_output("npm ls -g --json", "npm-ls-global")
        self._find_modules_in_npm_cache()


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
