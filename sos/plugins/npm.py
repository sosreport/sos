# Copyright (C) 2016 Red Hat, Inc., Tomas Tomecek <ttomecek@redhat>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import os
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
        Example 'npm cache ls' output
            ~/.npm
            ~/.npm/acorn
            ~/.npm/acorn/1.2.2
            ~/.npm/acorn/1.2.2/package.tgz
            ~/.npm/acorn/1.2.2/package
            ~/.npm/acorn/1.2.2/package/package.json
            ~/.npm/acorn/4.0.3
            ~/.npm/acorn/4.0.3/package.tgz
            ~/.npm/acorn/4.0.3/package
            ~/.npm/acorn/4.0.3/package/package.json
            ~/.npm/registry.npmjs.org
            ~/.npm/registry.npmjs.org/acorn
            ~/.npm/registry.npmjs.org/acorn/.cache.json

        https://docs.npmjs.com/cli/cache
        """
        output = {}
        # with chroot=True (default) the command fails when run as non-root
        user_cache = self.get_command_output("npm cache ls", chroot=False)
        if user_cache['status'] == 0:
            # filter out dirs with .cache.json ('registry.npmjs.org')
            for package in [l for l in user_cache['output'].splitlines()
                            if l.endswith('package.tgz')]:
                five_tuple = package.split(os.path.sep)
                if len(five_tuple) != 5:  # sanity check
                    continue
                home, cache, name, version, package_tgz = five_tuple
                if name not in output:
                    output[name] = [version]
                else:
                    output[name].append(version)
        self._log_debug("modules in cache: %s" % output)

        outfn = self._make_command_filename("npm_cache_modules")
        self.add_string_as_file(json.dumps(output), outfn)

    def setup(self):
        if self.get_option("project_path") != 0:
            project_path = os.path.abspath(os.path.expanduser(
                self.get_option("project_path")))
            self._get_npm_output("npm ls --json", "npm_ls_project",
                                 working_directory=project_path)
            self._get_npm_output("npm config list -l",
                                 "npm_config_list_project",
                                 working_directory=project_path)

        self._get_npm_output("npm ls -g --json", "npm_ls_global")
        self._get_npm_output("npm config list -l", "npm_config_list_global")
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
