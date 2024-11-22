# Copyright (C) 2014 Red Hat, Inc.,Poornima M. Kshirsagar <pkshiras@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import hashlib
import json
import os
from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, PluginOpt)
from sos.policies.distros.redhat import RHELPolicy


class Python(Plugin):
    """Captures information on the installed python runtime(s), as well as
    python modules installed via pip.
    """

    short_desc = 'Python runtime'

    plugin_name = 'python'
    profiles = ('system',)

    packages = ('python',)

    python_version = "python -V"

    def setup(self):
        self.add_cmd_output(
            self.python_version, suggest_filename="python-version"
        )
        pips = self.exec_cmd("whereis pip -b")
        if pips['status'] == 0:
            # output is like:
            # pip: /usr/bin/pip2.7 /usr/bin/pip3.6
            # where we must skip the first word
            for pip in pips['output'].split()[1:]:
                self.add_cmd_output(f"{pip} list installed")


class UbuntuPython(Python, DebianPlugin, UbuntuPlugin):

    python_version = "python3 -V"
    packages = ('python3',)


class RedHatPython(Python, RedHatPlugin):
    """In addition to the base information, on Red Hat family distributions the
    python plugin also supports the 'hashes' option. If enabled, this plugin
    will generate a json-formatted listing of all pyfiles within the
    distribution-standard python package installation locations.
    """

    packages = ('python', 'python36', 'python2', 'python3', 'platform-python')
    option_list = [
        PluginOpt('hashes', default=False,
                  desc='collect hashes for all python files')
    ]

    def setup(self):
        self.add_cmd_output(['python2 -V', 'python3 -V'])
        if isinstance(self.policy, RHELPolicy) and \
                self.policy.dist_version() == 8:
            self.python_version = "/usr/libexec/platform-python -V"
        super().setup()

    def collect(self):
        if self.get_option('hashes'):
            with self.collection_file('digests.json') as hfile:
                hfile.write(json.dumps(self.get_hashes(), indent=4))

    def get_hashes(self):
        """ Get the hashes for Python files """
        digests = {
            'digests': []
        }
        py_paths = [
            '/usr/lib',
            '/usr/lib64',
            '/usr/local/lib',
            '/usr/local/lib64'
        ]

        for py_path in py_paths:
            for root, _, files in os.walk(self.path_join(py_path)):
                for _file in files:
                    if not _file.endswith('.py'):
                        continue
                    filepath = self.path_join(root, _file)
                    try:
                        with open(filepath, 'rb') as file:
                            digest = hashlib.sha256()
                            data = file.read(1024)
                            while data:
                                digest.update(data)
                                data = file.read(1024)

                            digest = digest.hexdigest()
                            digests['digests'].append({
                                'filepath': filepath,
                                'sha256': digest
                            })
                    except IOError:
                        self._log_error("Unable to read python file at "
                                        f"{filepath}")
        return digests

# vim: set et ts=4 sw=4 :
