# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class saphana(Plugin, RedHatPlugin):

    short_desc = 'SAP HANA'
    plugin_name = 'saphana'
    profiles = ('sap',)
    files = ('/hana',)

    def setup(self):

        sids = []

        if self.path_isdir("/hana/shared"):
            s = self.listdir("/hana/shared")
            for sid in s:
                if len(sid) == 3:
                    sid = sid.strip()
                    sids.append(sid)

            for sid in sids:
                sidadm = '%sadm' % sid.lower()
                prefix = 'su - %s -c' % sidadm

                self.add_cmd_output('%s "HDB info"' % prefix,
                                    suggest_filename="%s_HDB_info" % sid)

                self.add_cmd_output('%s "hdbsrvutil -v"' % prefix,
                                    suggest_filename="%s_version" % sid)

                self.add_cmd_output('%s \'hdbcons "mm l -s -S -p"\'' % prefix,
                                    suggest_filename="%s_memusage" % sid)

                self.add_cmd_output('%s \'hdbcons -e hdbindexserver \
                                    "replication info"\'' % prefix,
                                    suggest_filename="%s_replicainfo" % sid)

                if self.path_isdir("/hana/shared/%s/" % sid):
                    for inst in self.listdir("/hana/shared/%s/" % sid):
                        if "HDB" in inst:
                            inst = inst.strip()[-2:]
                            self.get_inst_info(sid, sidadm, inst)

    def get_inst_info(self, sid, sidadm, inst):
        proc_cmd = 'su - %s -c "sapcontrol -nr %s -function GetProcessList"'
        status_fname = "%s_%s_status" % (sid, inst)
        self.add_cmd_output(
            proc_cmd % (sidadm, inst),
            suggest_filename=status_fname
        )

        path = "/usr/sap/%s/HDB%s/exe/python_support" % (sid, inst)
        if self.path_isdir(path):
            py_cmd = 'su - %s -c "python %s/landscapeHostConfiguration.py"'
            py_fname = "%s_%s_landscapeConfig" % (sid, inst)
            self.add_cmd_output(
                py_cmd % (sidadm, path),
                suggest_filename=py_fname
            )

# vim: et ts=4 sw=4
