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
from sets import Set
from sos.plugins import Plugin, RedHatPlugin


class sapnw(Plugin, RedHatPlugin):
    """SAP NetWeaver"""

    files = ['/usr/sap']

    def setup(self):

        # list installed instances
        self.add_cmd_output("/usr/sap/hostctrl/exe/saphostctrl \
                            -function ListInstances",
                            suggest_filename="SAPInstances_List")
        # list installed sap dbs
        self.add_cmd_output("/usr/sap/hostctrl/exe/saphostctrl \
                            -function ListDatabases",
                            suggest_filename="SAPDatabases_List")

        # list defined instances and guess profiles out of them
        # (good for HA setups with virtual hostnames)
        # using sap host control agent

        p = self.get_command_output(
            "/usr/sap/hostctrl/exe/saphostctrl -function ListInstances")

        sidsunique = Set([])

        # Cycle through all the instances, get 'sid' 'instance_number'
        # and 'vhost' to determine the proper profile
        for line in p['output'].splitlines():
            if "DAA" not in line:
                fields = line.strip().split()
                sid = fields[3]
                inst = fields[5]
                vhost = fields[7]
                sidsunique.add(sid)
                p = os.listdir("/usr/sap/%s/SYS/profile/" % sid)
                for line in p:
                    if sid in line and inst in line and vhost in line:
                        ldenv = 'LD_LIBRARY_PATH=/usr/sap/%s/SYS/exe/run' % sid
                        pt = '/usr/sap/%s/SYS/exe/uc/linuxx86_64' % sid
                        profile = line.strip()
                        self.add_cmd_output(
                            "env -i %s %s/sappfpar \
                            all pf=/usr/sap/%s/SYS/profile/%s"
                            % (ldenv, pt, sid, profile),
                            suggest_filename="%s_parameters" % profile)

                        # collect instance status
                        self.add_cmd_output(
                            "env -i %s %s/sapcontrol -nr %s \
                            -function GetProcessList" % (ldenv, pt, inst),
                            suggest_filename="%s_%s_GetProcList" % (sid, inst))

                        # collect version info for the various components
                        self.add_cmd_output(
                            "env -i %s %s/sapcontrol -nr %s \
                            -function GetVersionInfo" % (ldenv, pt, inst),
                            suggest_filename="%s_%s_GetVersInfo" % (sid, inst))

                        # collect <SID>adm user environment
                        lowsid = sid.lower()
                        self.add_cmd_output(
                            "su - %sadm -c \"sapcontrol -nr %s -function \
                            GetEnvironment\"" % (lowsid, inst),
                            suggest_filename="%s_%sadm_%s_userenv"
                            % (sid, lowsid, inst))

        # traverse the sids list, collecting info about dbclient
        for sid in sidsunique:
            c = self.get_command_output("ls /usr/sap/%s/" % sid)
            for line in c['output'].splitlines():
                if 'DVEB' in line:
                    self.add_cmd_output(
                        "grep 'client driver' /usr/sap/%s/%s/work/dev_w0"
                        % (sid, line), suggest_filename="%s_dbclient" % sid)

        # get the installed db's
        d = self.get_command_output(
            '/usr/sap/hostctrl/exe/saphostctrl -function ListDatabases')

        for line in d['output'].splitlines():
            if "Instance name" in line:
                fields = line.strip().split()
                dbadm = fields[2][:-1]
                dbtype = fields[8][:-1]
                sid = dbadm[3:].upper()

                if dbtype == 'db6':
                    self.add_cmd_output(
                        "su - %s -c \"db2 get dbm cfg\""
                        % dbadm, suggest_filename="%s_%s_db2_info"
                        % (sid, dbadm))

                if dbtype == 'sap':
                    sid = fields[2][:-1]
                    self.add_cmd_output(
                        "cat /sapdb/%s/data/config/%s.pah"
                        % (sid, sid),
                        suggest_filename="%s_%s_maxdb_info"
                        % (sid, dbadm))

                if dbtype == 'ora':
                    sid = fields[2][:-1]
                    self.add_cmd_output(
                        "cat /oracle/%s/*/dbs/init.ora" % sid,
                        suggest_filename="%s_oracle_init.ora" % sid)

        # if sapconf available run it in check mode
        if os.path.isfile("/usr/bin/sapconf"):
            self.add_cmd_output(
                "/usr/bin/sapconf -n", suggest_filename="sapconf_checkmode")

# vim: et ts=4 sw=4
