# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Saphana(Plugin, RedHatPlugin):

    short_desc = 'SAP HANA'
    plugin_name = 'saphana'
    profiles = ('sap',)
    files = ('/hana',)

    def setup(self):

        sids = []

        if self.path_isdir("/hana/shared"):
            shared = self.listdir("/hana/shared")
            for sid in shared:
                if len(sid) == 3:
                    sid = sid.strip()
                    sids.append(sid)

            for sid in sids:
                sidadm = f'{sid.lower()}adm'
                prefix = f'su - {sidadm} -c'

                self.add_cmd_output(f'{prefix} "HDB info"',
                                    suggest_filename=f"{sid}_HDB_info")

                self.add_cmd_output(f'{prefix} "hdbsrvutil -v"',
                                    suggest_filename=f"{sid}_version")

                self.add_cmd_output(f'{prefix} \'hdbcons "mm l -s -S -p"\'',
                                    suggest_filename=f"{sid}_memusage")

                self.add_cmd_output(f'{prefix} \'hdbcons -e hdbindexserver \
                                    "replication info"\'',
                                    suggest_filename=f"{sid}_replicainfo")

                if self.path_isdir(f"/hana/shared/{sid}/"):
                    for inst in self.listdir(f"/hana/shared/{sid}/"):
                        if "HDB" in inst:
                            inst = inst.strip()[-2:]
                            self.get_inst_info(sid, sidadm, inst)

    def get_inst_info(self, sid, sidadm, inst):
        """ Collect the given instance info """
        proc_cmd = 'su - %s -c "sapcontrol -nr %s -function GetProcessList"'
        status_fname = f"{sid}_{inst}_status"
        self.add_cmd_output(
            proc_cmd % (sidadm, inst),
            suggest_filename=status_fname
        )

        path = f"/usr/sap/{sid}/HDB{inst}/exe/python_support"
        if self.path_isdir(path):
            py_cmd = 'su - %s -c "python %s/landscapeHostConfiguration.py"'
            py_fname = f"{sid}_{inst}_landscapeConfig"
            self.add_cmd_output(
                py_cmd % (sidadm, path),
                suggest_filename=py_fname
            )

# vim: et ts=4 sw=4
