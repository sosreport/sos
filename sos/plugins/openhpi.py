# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class OpenHPI(Plugin, RedHatPlugin):
    """Open Hardware Platform Interface
    """

    plugin_name = 'openhpi'
    profiles = ('system', 'hardware')

    def setup(self):
        self.add_copy_spec([
            "/etc/openhpi/openhpi.conf",
            "/etc/openhpi/openhpiclient.conf"
        ])

    def postproc(self):
        self.do_file_sub("/etc/openhpi/openhpi.conf",
                         r'(\s*[Pp]ass.*\s*=\s*).*', r'\1********')


# vim: set et ts=4 sw=4 :
