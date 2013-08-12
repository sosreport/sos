### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import sos.plugintools

class openhpi(sos.plugintools.PluginBase):
    """OpenHPI related information
    """

    def setup(self):
        self.addCopySpecs([
            "/etc/openhpi/openhpi.conf",
            "/etc/openhpi/openhpiclient.conf"
        ])

    def postproc(self):
        self.doRegexSub("/etc/openhpi/openhpi.conf"
                        r'([Pp]assw(or)?d|[Pp]assphrase)[[:space:]]+\=[[:space:]]"(.*)"',
                        r"\1******")
        self.doRegexSub("/etc/openhpi/openhpiclient.conf"
                        r'([Pp]assw(or)?d|[Pp]assphrase)[[:space:]]+\=[[:space:]]"(.*)"',
                        r"\1******")

