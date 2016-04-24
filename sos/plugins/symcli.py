# Copyright (C) 2008 EMC Corporation. Keith Kearnan <kearnan_keith@emc.com>
# Copyright (C) 2014 Red Hat, Inc. Bryn M. Reeves <bmr@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, os
from sos.utilities import is_executable


class Symcli(Plugin, RedHatPlugin):
    """ EMC Symcli
    """

    plugin_name = 'symcli'
    profiles = ('storage', 'hardware')

    def get_symcli_files(self):
        """ EMC Solutions Enabler SYMCLI specific information - files
        """
        self.add_copy_spec([
            "/var/symapi/db/symapi_db.bin",
            "/var/symapi/config/[a-z]*",
            "/var/symapi/log/[a-z]*"
        ])

    def get_symcli_config(self):
        """ EMC Solutions Enabler SYMCLI specific information
        - Symmetrix/DMX - commands
        """
        self.add_cmd_output([
            "/usr/symcli/bin/symcli -def",
            "/usr/symcli/bin/symdg list",
            "/usr/symcli/bin/symdg -v list",
            "/usr/symcli/bin/symcg list",
            "/usr/symcli/bin/symcg -v list",
            "/usr/symcli/bin/symcfg list",
            "/usr/symcli/bin/symcfg -v list",
            "/usr/symcli/bin/symcfg -db",
            "/usr/symcli/bin/symcfg -semaphores list",
            "/usr/symcli/bin/symcfg -dir all -v list",
            "/usr/symcli/bin/symcfg -connections list",
            "/usr/symcli/bin/symcfg -app -v list",
            "/usr/symcli/bin/symcfg -fa all -port list",
            "/usr/symcli/bin/symcfg -ra all -port list",
            "/usr/symcli/bin/symcfg -sa all -port list",
            "/usr/symcli/bin/symcfg list -lock",
            "/usr/symcli/bin/symcfg list -lockn all",
            "/usr/symcli/bin/syminq",
            "/usr/symcli/bin/syminq -v",
            "/usr/symcli/bin/syminq -symmids",
            "/usr/symcli/bin/syminq hba -fibre",
            "/usr/symcli/bin/syminq hba -scsi",
            "/usr/symcli/bin/symhost show -config",
            "/usr/symcli/bin/stordaemon list",
            "/usr/symcli/bin/stordaemon -v list",
            "/usr/symcli/bin/sympd list",
            "/usr/symcli/bin/sympd list -vcm",
            "/usr/symcli/bin/symdev list",
            "/usr/symcli/bin/symdev -v list",
            "/usr/symcli/bin/symdev -rdfa list",
            "/usr/symcli/bin/symdev -rdfa -v list",
            "/usr/symcli/bin/symbcv list",
            "/usr/symcli/bin/symbcv -v list",
            "/usr/symcli/bin/symrdf list",
            "/usr/symcli/bin/symrdf -v list",
            "/usr/symcli/bin/symrdf -rdfa list",
            "/usr/symcli/bin/symrdf -rdfa -v list",
            "/usr/symcli/bin/symsnap list",
            "/usr/symcli/bin/symsnap list -savedevs",
            "/usr/symcli/bin/symclone list",
            "/usr/symcli/bin/symevent list",
            "/usr/symcli/bin/symmask list hba",
            "/usr/symcli/bin/symmask list logins",
            "/usr/symcli/bin/symmaskdb list database",
            "/usr/symcli/bin/symmaskdb -v list database"
        ])

    def check_enabled(self):
        return is_executable("/usr/symcli/bin/symcli")

    def setup(self):
        self.get_symcli_files()
        self.get_symcli_config()

# vim: set et ts=4 sw=4 :
