# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin
import re


class Kpatch(Plugin, RedHatPlugin):

    short_desc = 'Kpatch information'

    plugin_name = 'kpatch'

    packages = ('kpatch',)

    def setup(self):
        kpatch_list = self.collect_cmd_output("kpatch list")
        if not kpatch_list['status'] == 0:
            return
        kpatches = kpatch_list['output'].splitlines()
        for patch in kpatches:
            if not re.match(r"^kpatch-.*\(.*\)", patch):
                continue
            (module, version) = patch.split()
            self.add_cmd_output("kpatch info " + module)


# vim: set et ts=4 sw=4 :
