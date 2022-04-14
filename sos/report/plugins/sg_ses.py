# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin

class SgSES(Plugin, RedHatPlugin, DebianPlugin):

    short_desc = 'SCSI Enclosure Services (SES) device'
    plugin_name = 'sg_ses'
    profiles = ('storage', 'hardware',)
    packages = ('sg3_utils')

    """
    Sample output of : lsscsi -g
    [15:1:121:0] enclosu DELL     MD1400           1.07  -          /dev/sg3 
    """
    def setup(self):
        scsi_types = ["enclosu"]
        result = self.collect_cmd_output('lsscsi -g')
        if result['status'] == 0:
            for line in result['output'].splitlines():
                if (line.split()[1] in scsi_types):
                    devsg = line.split()[-1]
                    self.add_cmd_output("sg_ses -p2 -b1 %s" % devsg)

# vim: set et ts=4 sw=4 :
