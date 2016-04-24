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


class saphana(Plugin, RedHatPlugin):
    """SAP HANA"""

    plugin_name = 'saphana'
    profiles = ['sap']

    files = ['/hana']

    def setup(self):

        sids = []

        if os.path.isdir("/hana/shared"):
            s = os.listdir("/hana/shared")
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

                if os.path.isdir("/hana/shared/%s/" % sid):
                    i = os.listdir("/hana/shared/%s/" % sid)
                    for inst in i:
                        if "HDB" in inst:
                            inst = inst.strip()[-2:]

                            # get GREEN/RED status
                            self.add_cmd_output(
                                'su - %s -c "sapcontrol -nr %s \
                                -function GetProcessList"'
                                % (sidadm, inst),
                                suggest_filename="%s_%s_status"
                                % (sid, inst)
                            )

                            path = '/usr/sap/%s/HDB%s/exe/python_support'
                            path %= (sid, inst)

                            if os.path.isdir("%s" % path):
                                # SCALE OUT - slow
                                self.add_cmd_output(
                                    'su - %s -c "python \
                                    %s/landscapeHostConfiguration.py"'
                                    % (sidadm, path),
                                    suggest_filename="%s_%s_landscapeConfig"
                                    % (sid, inst)
                                )

# vim: et ts=4 sw=4
