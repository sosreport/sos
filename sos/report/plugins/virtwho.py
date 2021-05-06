# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class VirtWho(Plugin, RedHatPlugin):

    short_desc = 'Virt-Who agent'

    plugin_name = 'virtwho'
    profiles = ('virt', 'system')
    packages = ('virt-who',)

    def setup(self):
        self.add_copy_spec(["/etc/virt-who.d/*", "/etc/virt-who.conf"])
        self.add_cmd_output("virt-who -dop")

    def postproc(self):
        # the regexp path catches both /etc/virt-who.d/ and /etc/virt-who.conf
        self.do_path_regex_sub(r"\/etc\/virt-who\.",
                               r"(password=)(\S*)",
                               r"\1********")

# vim: set et ts=4 sw=4 :
