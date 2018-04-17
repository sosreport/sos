# Copyright (C) 2018 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin


class Buildah(Plugin, RedHatPlugin):
    """Buildah container and image builder
    """

    plugin_name = 'buildah'
    packages = ('buildah',)

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
