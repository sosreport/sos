# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from sos.plugins import Plugin, RedHatPlugin


def get_directory_listing(path):
    try:
        dir_list = os.listdir(path)
    except:
        dir_list = []
    return dir_list


class sapnw(Plugin, RedHatPlugin):
    """SAP NetWeaver"""

    plugin_name = 'sapnw'
    profiles = ['sap']

    files = ['/usr/sap']

    def collect_list_instances(self):
        # list installed instances
        inst_out = self.get_cmd_output_now("/usr/sap/hostctrl/exe/saphostctrl \
                                           -function ListInstances",
                                           suggest_filename="SAPInstances")
        if not inst_out:
            return

        sidsunique = set()
        # Cycle through all the instances, get 'sid', 'instance_number'
        # and 'vhost' to determine the proper profile
        p = open(inst_out, "r").read().splitlines()
        for line in p:
            if "DAA" not in line:
                fields = line.strip().split()
                sid = fields[3]
                inst = fields[5]
                vhost = fields[7]
                sidsunique.add(sid)
                for line in get_directory_listing("/usr/sap/%s/SYS/profile/"
                                                  % sid):
                    if sid in line and inst in line and vhost in line:
                        ldenv = 'LD_LIBRARY_PATH=/usr/sap/%s/SYS/exe/run' % sid
                        # TODO: I am assuming unicode here
                        # nuc should be accounted
                        pt = '/usr/sap/%s/SYS/exe/uc/linuxx86_64' % sid
                        profile = line.strip()
                        # collect profiles
                        self.add_cmd_output(
                            "env -i %s %s/sappfpar \
                            all pf=/usr/sap/%s/SYS/profile/%s"
                            % (ldenv, pt, sid, profile),
                            suggest_filename="%s_parameters" % profile)

                        # collect instance status
                        self.add_cmd_output(
                            "env -i %s %s/sapcontrol -nr %s \
                            -function GetProcessList" % (ldenv, pt, inst),
                            suggest_filename="%s_%s_GetProcList"
                            % (sid, inst))

                        # collect version info for the various components
                        self.add_cmd_output(
                            "env -i %s %s/sapcontrol -nr %s \
                            -function GetVersionInfo" % (ldenv, pt, inst),
                            suggest_filename="%s_%s_GetVersInfo"
                            % (sid, inst))

                        # collect <SID>adm user environment
                        lowsid = sid.lower()
                        self.add_cmd_output(
                            "su - %sadm -c \"sapcontrol -nr %s -function \
                            GetEnvironment\"" % (lowsid, inst),
                            suggest_filename="%s_%sadm_%s_userenv"
                            % (sid, lowsid, inst))

        # traverse the sids list, collecting info about dbclient
        for sid in sidsunique:
            for line in get_directory_listing("/usr/sap/%s/" % sid):
                if 'DVEB' in line:
                    self.add_cmd_output(
                        "grep 'client driver' /usr/sap/%s/%s/work/dev_w0"
                        % (sid, line), suggest_filename="%s_dbclient"
                        % sid)

    def collect_list_dbs(self):
        # list installed sap dbs
        db_out = self.get_cmd_output_now("/usr/sap/hostctrl/exe/saphostctrl \
                                         -function ListDatabases",
                                         suggest_filename="SAPDatabases")
        if not db_out:
            return

        dbl = open(db_out, "r").read().splitlines()
        for line in dbl:
            if "Instance name" in line:
                fields = line.strip().split()
                dbadm = fields[2][:-1]
                dbtype = fields[8][:-1]
                sid = dbadm[3:].upper()

                if dbtype == 'db6':
                    # IBM DB2
                    self.add_cmd_output(
                        "su - %s -c \"db2 get dbm cfg\""
                        % dbadm, suggest_filename="%s_%s_db2_info"
                        % (sid, dbadm))

                if dbtype == 'sap':
                    # SAP MAXDB
                    sid = fields[2][:-1]
                    self.add_copy_spec(
                        "/sapdb/%s/data/config/%s.pah" % (sid, sid))

                if dbtype == 'ora':
                    # Oracle
                    sid = fields[2][:-1]
                    self.add_copy_spec("/oracle/%s/*/dbs/init.ora" % sid)

                if dbtype == 'syb':
                    # Sybase
                    sid = fields[2][:-1]
                    self.add_copy_spec("/sybase/%s/ASE*/%s.cfg" % (sid, sid))

    def setup(self):
        self.collect_list_instances()
        self.collect_list_dbs()

        # run sapconf in check mode
        self.add_cmd_output("sapconf -n",
                            suggest_filename="sapconf_checkmode")

# vim: et ts=4 sw=4
