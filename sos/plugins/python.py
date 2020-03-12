# Copyright (C) 2014 Red Hat, Inc.,Poornima M. Kshirsagar <pkshiras@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
import sos.policies
import os
import json
import hashlib


class Python(Plugin, DebianPlugin, UbuntuPlugin):
    """Python runtime
    """

    plugin_name = 'python'
    profiles = ('system',)

    packages = ('python',)

    python_version = "python -V"

    def setup(self):
        self.add_cmd_output(
            self.python_version, suggest_filename="python-version"
        )
        self.add_cmd_output("pip list")


class RedHatPython(Python, RedHatPlugin):

    packages = ('python', 'python36', 'python2', 'platform-python')
    option_list = [
        ('hashes', "gather hashes for all python files", 'slow',
         False)]

    def setup(self):
        self.add_cmd_output(['python2 -V', 'python3 -V'])
        if isinstance(self.policy, sos.policies.redhat.RHELPolicy) and \
                self.policy.dist_version() > 7:
            self.python_version = "/usr/libexec/platform-python -V"
        super(RedHatPython, self).setup()

        if self.get_option('hashes'):
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
                for root, _, files in os.walk(py_path):
                    for file_ in files:
                        filepath = os.path.join(root, file_)
                        if filepath.endswith('.py'):
                            try:
                                with open(filepath, 'rb') as f:
                                    digest = hashlib.sha256()
                                    chunk = 1024
                                    while True:
                                        data = f.read(chunk)
                                        if data:
                                            digest.update(data)
                                        else:
                                            break

                                    digest = digest.hexdigest()

                                    digests['digests'].append({
                                        'filepath': filepath,
                                        'sha256': digest
                                    })
                            except IOError:
                                self._log_error(
                                    "Unable to read python file at %s" %
                                    filepath
                                )

            self.add_string_as_file(json.dumps(digests), 'digests.json')

# vim: set et ts=4 sw=4 :
