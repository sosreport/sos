# Copyright (C) 2014 Red Hat, Inc.,Poornima M. Kshirsagar <pkshiras@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin, \
        ArchPlugin
import sos.policies


class Python(Plugin, DebianPlugin, UbuntuPlugin, ArchPlugin):
    """Python runtime
    """

    plugin_name = 'python'
    profiles = ('system',)

    packages = ('python',)

    def setup(self):
        self.add_cmd_output("python -V", suggest_filename="python-version")
        self.add_cmd_output("pip list")


class RedHatPython(Python, RedHatPlugin):

    packages = ('python', 'python36', 'python2', 'platform-python')

    def setup(self):
        self.add_cmd_output(['python2 -V', 'python3 -V'])
        self.add_cmd_output("pip list")
        if isinstance(self.policy, sos.policies.redhat.RHELPolicy) and \
                self.policy.dist_version() > 7:
            self.add_cmd_output(
                '/usr/libexec/platform-python -V',
                suggest_filename='python-version'
            )
        else:
            self.add_cmd_output('python -V', suggest_filename='python-version')

# vim: set et ts=4 sw=4 :
