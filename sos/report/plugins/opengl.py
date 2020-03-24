# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class OpenGL(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """OpenGL
    """

    plugin_name = 'opengl'
    profiles = ('hardware', 'desktop', 'gpu')
    files = ('/usr/bin/glxinfo',)

    def setup(self):
        self.add_cmd_output([
            "glxinfo",
        ])

# vim: set et ts=4 sw=4 :
