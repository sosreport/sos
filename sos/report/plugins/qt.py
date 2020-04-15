# Copyright (C) 2019 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Qt(Plugin, RedHatPlugin):

    short_desc = 'QT widget toolkit'

    plugin_name = 'qt'
    packages = ('qt', )

    def setup(self):
        self.add_env_var([
            'QT_IM_MODULE',
            'QTDIR',
            'QTLIB',
            'QT_PLUGIN_PATH',
            'IMSETTINGS_MODULE'
        ])

# vim: set et ts=4 sw=4 :
