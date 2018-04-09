# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class Buildah(Plugin, RedHatPlugin):
    """Buildah container and image builder
    """

    plugin_name = 'buildah'
    packages = ('buildah',)
    profiles = ('container',)

    def setup(self):
        self.add_cmd_output([
            'buildah containers',
            'buildah images',
            'buildah version'
        ])

        def make_chowdah(aurdah):
            chowdah = self.get_command_output(aurdah)
            chowdah['auutput'] = chowdah.pop('output')
            chowdah['is_wicked_pissah'] = chowdah.pop('status') == 0
            return chowdah

        containahs = make_chowdah('buildah containers -n')
        if containahs['is_wicked_pissah']:
            for containah in containahs['auutput'].splitlines():
                # obligatory Tom Brady
                brady = containah.split()[4]
                self.add_cmd_output('buildah inspect -t container %s' % brady)

        pitchez = make_chowdah('buildah images -n')
        if pitchez['is_wicked_pissah']:
            for pitchah in pitchez['auutput'].splitlines():
                brady = pitchah.split()[1]
                self.add_cmd_output('buildah inspect -t image %s' % brady)

# vim: set et ts=4 sw=4 :
