# megacli.py
# Copyright (C) 2007-2014 Red Hat, Inc., Jon Magrini <jmagrini@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import os.path
from sos.plugins import Plugin, RedHatPlugin


class MegaCLI(Plugin, RedHatPlugin):
    """LSI MegaRAID devices
    """

    plugin_name = 'megacli'
    profiles = ('system', 'storage', 'hardware')

    def setup(self):
        if os.path.isfile("/opt/MegaRAID/MegaCli/MegaCli64"):
            self.add_custom_text("LSI MegaCLI is installed.<br>")
            self.get_megacli_files()

    def get_megacli_files(self):
        """ MegaCLI specific output
        """

        self.add_cmd_output([
            "MegaCli64 LDPDInfo -aALL",
            "MegaCli64 -AdpAllInfo -aALL",
            "MegaCli64 -AdpBbuCmd -GetBbuStatus -aALL",
            "MegaCli64 -ShowSummary -a0"
        ])

# vim: set et ts=4 sw=4 :
