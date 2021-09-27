# Copyright (C) 2019 Red Hat, Inc., Miguel Martin <mmartinv@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt
from datetime import datetime


class oVirtEngineBackup(Plugin, RedHatPlugin):

    short_desc = 'oVirt Engine database backup'

    packages = ("ovirt-engine-tools-backup",)
    plugin_name = "ovirt_engine_backup"
    option_list = [
        PluginOpt('backupdir', default='/var/lib/ovirt-engine-backup',
                  desc='Directory where backups are generated'),
        PluginOpt('tmpdir', default='/tmp',
                  desc='temp dir to use for engine-backup')
    ]
    profiles = ("virt",)

    def setup(self):
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_filename = self.path_join(
            self.get_option("backupdir"),
            "engine-db-backup-%s.tar.gz" % (now)
        )
        log_filename = self.path_join(
            self.get_option("backupdir"),
            "engine-db-backup-%s.log" % (now)
        )
        cmd = ("engine-backup --mode=backup --scope=db"
               " --file=%s --log=%s --tmpdir=%s") % (
            backup_filename,
            log_filename,
            self.get_option("tmpdir")
        )
        res = self.collect_cmd_output(cmd, suggest_filename="engine-backup")
        if res['status'] == 0:
            self.add_copy_spec([
                backup_filename,
                log_filename
            ])

# vim: set et ts=4 sw=4 :
