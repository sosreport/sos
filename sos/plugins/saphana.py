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
import os.path
import sos.plugintools


class saphana(sos.plugintools.PluginBase):
    """SAP HANA"""

    files = ['/hana', ]
    packages = ["compat-sap-c++", ]

    def setup(self):

        sids = []

        s = os.listdir("/hana/shared")
        for sid in s:
            if len(sid) == 3:
                sid = sid.strip()
                sids.append(sid)

        for sid in sids:
            sidadm = '%sadm' % sid.lower()

            prefix = 'su - %s -c' % sidadm

            self.collectExtOutput('%s "HDB info"' % prefix,
                                  suggest_filename="%s_HDB_info" % sid)

            self.collectExtOutput('%s "hdbsrvutil -v"' % prefix,
                                  suggest_filename="%s_version" % sid)

            self.collectExtOutput('%s \'hdbcons "mm l -s -S -p"\'' % prefix,
                                  suggest_filename="%s_memusage" % sid)

            self.collectExtOutput('%s \'hdbcons -e hdbindexserver \
                                  "replication info"\'' % prefix,
                                  suggest_filename="%s_replicainfo" % sid)

            i = os.listdir("/hana/shared/%s/" % sid)
            for inst in i:
                if "HDB" in inst:
                    inst = inst.strip()[-2:]

                    # get GREEN/RED status
                    self.collectExtOutput(
                        'su - %s -c "sapcontrol -nr %s \
                        -function GetProcessList"'
                        % (sidadm, inst),
                        suggest_filename="%s_%s_status"
                        % (sid, inst))

                    path = '/usr/sap/%s/HDB%s/exe/python_support' % (sid, inst)
                    # SCALE OUT - slow
                    self.collectExtOutput(
                        'su - %s -c "python \
                        %s/landscapeHostConfiguration.py"'
                        % (sidadm, path),
                        suggest_filename="%s_%s_landscapeHostConfig"
                        % (sid, inst))

# vim: et ts=4 sw=4
