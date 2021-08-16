# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class sapnw(Plugin, RedHatPlugin):

    short_desc = 'SAP NetWeaver'
    plugin_name = 'sapnw'
    profiles = ('sap',)
    files = ('/usr/sap',)

    def collect_list_instances(self):
        # list installed instances
        inst_out = self.collect_cmd_output(
            "/usr/sap/hostctrl/exe/saphostctrl -function ListInstances",
            suggest_filename="SAPInstances"
        )
        if inst_out['status'] != 0:
            return

        # set the common strings that will be formatted later in each a_c_s
        prof_cmd = "env -i %s %s/sappfpar all pf=/usr/sap/%s/SYS/profile/%s"
        inst_cmd = "env -i %s %s/sapcontrol -nr %s -function GetProcessList"
        vers_cmd = "env -i %s %s/sapcontrol -nr %s -function GetVersionInfo"
        user_cmd = 'su - %sadm -c "sapcontrol -nr %s -function GetEnvironment"'

        sidsunique = set()
        # Cycle through all the instances, get 'sid', 'instance_number'
        # and 'vhost' to determine the proper profile
        for inst_line in inst_out['output'].splitlines():
            if ("DAA" not in inst_line and not
                    inst_line.startswith("No instances found")):
                fields = inst_line.strip().split()
                if len(fields) < 8:
                    continue
                sid = fields[3]
                inst = fields[5]
                vhost = fields[7]
                sidsunique.add(sid)
                path = "/usr/sap/%s/SYS/profile/" % sid
                if not self.path_exists(path):
                    continue
                for line in self.listdir(path):
                    if all(f in line for f in [sid, inst, vhost]):
                        ldenv = 'LD_LIBRARY_PATH=/usr/sap/%s/SYS/exe/run' % sid
                        # TODO: I am assuming unicode here
                        # nuc should be accounted
                        pt = '/usr/sap/%s/SYS/exe/uc/linuxx86_64' % sid
                        profile = line.strip()

                        # collect profiles
                        self.add_cmd_output(
                            prof_cmd % (ldenv, pt, sid, profile),
                            suggest_filename="%s_parameters" % profile
                        )

                        # collect instance status
                        self.add_cmd_output(
                            inst_cmd % (ldenv, pt, inst),
                            suggest_filename="%s_%s_GetProcList" % (sid, inst)
                        )

                        # collect version info for the various components
                        self.add_cmd_output(
                            vers_cmd % (ldenv, pt, inst),
                            suggest_filename="%s_%s_GetVersInfo" % (sid, inst)
                        )

                        # collect <SID>adm user environment
                        lowsid = sid.lower()
                        fname = "%s_%sadm_%s_userenv" % (sid, lowsid, inst)
                        self.add_cmd_output(
                            user_cmd % (lowsid, inst),
                            suggest_filename=fname
                        )

        # traverse the sids list, collecting info about dbclient
        for sid in sidsunique:
            self.add_copy_spec("/usr/sap/%s/*DVEB*/work/dev_w0" % sid)

    def collect_list_dbs(self):
        # list installed sap dbs
        db_out = self.collect_cmd_output(
            "/usr/sap/hostctrl/exe/saphostctrl -function ListDatabases",
            suggest_filename="SAPDatabases"
        )

        if db_out['status'] != 0:
            return

        for line in db_out['output'].splitlines():
            if "Instance name" in line:
                fields = line.strip().split()
                dbadm = fields[2][:-1]
                dbtype = fields[8][:-1]
                sid = dbadm[3:].upper()

                if dbtype == 'db6':
                    # IBM DB2
                    self.add_cmd_output(
                        "su - %s -c \"db2 get dbm cfg\"" % dbadm,
                        suggest_filename="%s_%s_db2_info" % (sid, dbadm)
                    )

                elif dbtype == 'sap':
                    # SAP MAXDB
                    sid = fields[2][:-1]
                    self.add_copy_spec(
                        "/sapdb/%s/data/config/%s.pah" % (sid, sid)
                    )

                elif dbtype == 'ora':
                    # Oracle
                    sid = fields[2][:-1]
                    self.add_copy_spec("/oracle/%s/*/dbs/init.ora" % sid)

                elif dbtype == 'syb':
                    # Sybase
                    sid = fields[2][:-1]
                    self.add_copy_spec("/sybase/%s/ASE*/%s.cfg" % (sid, sid))

    def setup(self):
        self.collect_list_instances()
        self.collect_list_dbs()

        # run sapconf in check mode
        #
        # since the command creates a limits.d file on its own,
        # we must predicate it by presence of the file
        if self.path_exists('/etc/security/limits.d/99-sap-limits.conf') \
                or self.get_option('allow_system_changes'):
            self.add_cmd_output("sapconf -n",
                                suggest_filename="sapconf_checkmode")

# vim: et ts=4 sw=4
