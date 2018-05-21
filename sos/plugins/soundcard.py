# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Soundcard(Plugin):
    """ Sound devices
    """

    plugin_name = "soundcard"
    profiles = ('desktop', 'hardware')

    def setup(self):
        self.add_copy_spec("/proc/asound/*")
        self.add_cmd_output([
            "aplay -l",
            "aplay -L",
            "amixer"
        ])


class RedHatSoundcard(Soundcard, RedHatPlugin):

    def setup(self):
        super(RedHatSoundcard, self).setup()

        self.add_copy_spec([
            "/etc/alsa/*",
            "/etc/asound.*"
        ])


class DebianSoundcard(Soundcard, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super(DebianSoundcard, self).setup()

        self.add_copy_spec("/etc/pulse/*")

# vim: set et ts=4 sw=4 :
