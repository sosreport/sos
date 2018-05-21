# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Anacron(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Anacron job scheduling service"""

    plugin_name = 'anacron'
    profiles = ('system',)
    packages = ('anacron', 'chronie-anacron')

    # anacron may be provided by anacron, cronie-anacron etc.
    # just look for the configuration file which is common
    files = ('/etc/anacrontab',)

# vim: set et ts=4 sw=4 :
