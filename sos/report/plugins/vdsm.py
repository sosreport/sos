# Copyright (C) 2018 Red Hat, Inc.

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin

import glob
import json
import re


# This configuration is based on vdsm.storage.lvm.LVM_CONF_TEMPLATE.
#
# locking_type is set to 0 in order to match lvm sos commands. With this
# configuration we don't take any locks, so we will never block because
# there is a stuck lvm command.
# locking_type=0
#
# To prevent modifications to volume group metadata (for e.g. due to a
# automatically detected inconsistency), metadata_read_only is set to 1.
# metadata_read_only=1
#
# use_lvmetad is set to 0 in order not to show cached, old lvm metadata.
# use_lvmetad=0
#
# preferred_names, use_devicesfile and filter config values are set to
# capture Vdsm devices.
# preferred_names=[ '^/dev/mapper/' ]
# filter=[ 'a|^/dev/mapper/.*|', 'r|.*|' ]
LVM_CONFIG = """
global {
    locking_type=0
    metadata_read_only=1
    use_lvmetad=0
}
devices {
    preferred_names=["^/dev/mapper/"]
    ignore_suspended_devices=1
    write_cache_state=0
    disable_after_error_count=3
    use_devicesfile=0
    filter=["a|^/dev/disk/by-id/dm-uuid-mpath-|", "r|.+|"]
}
"""
LVM_CONFIG = re.sub(r"\s+", " ", LVM_CONFIG).strip()


class Vdsm(Plugin, RedHatPlugin):

    short_desc = 'VDSM - Virtual Desktop and Server Manager'
    packages = (
        'vdsm',
        'vdsm-client',
    )

    plugin_name = 'vdsm'

    def setup(self):
        self.add_forbidden_path('/etc/pki/vdsm/keys')
        self.add_forbidden_path('/etc/pki/vdsm/*/*-key.*')
        self.add_forbidden_path('/etc/pki/libvirt/private')
        self.add_forbidden_path('/var/lib/vdsm/storage/transient_disks')

        self.add_service_status(['vdsmd', 'supervdsmd'])

        self.add_copy_spec([
            '/tmp/vds_installer*',
            '/tmp/vds_bootstrap*',
            '/etc/vdsm/*',
            '/etc/pki/vdsm/'
        ])

        self.add_copy_spec('/var/log/vdsm/*')

        self._add_vdsm_forbidden_paths()
        self.add_copy_spec([
            '/run/vdsm/*',
            '/usr/libexec/vdsm/hooks',
            '/var/lib/vdsm',
        ])

        qemu_pids = self.get_process_pids('qemu-kvm')
        if qemu_pids:
            files = ["cmdline", "status", "mountstats"]
            self.add_copy_spec([
                "/proc/%s/%s" % (pid, name)
                for pid in qemu_pids
                for name in files
            ])
        self.add_cmd_output([
            "ls -ldZ /etc/vdsm",
            "su vdsm -s /bin/sh -c 'tree -l /rhev/data-center'",
            "su vdsm -s /bin/sh -c 'ls -lR /rhev/data-center'"
        ])
        self.add_cmd_output([
            "lvm vgs -v -o +tags --config \'%s\'" % LVM_CONFIG,
            "lvm lvs -v -o +tags --config \'%s\'" % LVM_CONFIG,
            "lvm pvs -v -o +all --config \'%s\'" % LVM_CONFIG
        ])

        self.add_cmd_output([
            'vdsm-client Host getCapabilities',
            'vdsm-client Host getStats',
            'vdsm-client Host getAllVmStats',
            'vdsm-client Host getVMFullList',
            'vdsm-client Host getDeviceList',
            'vdsm-client Host hostdevListByCaps',
            'vdsm-client Host getAllTasksInfo',
            'vdsm-client Host getAllTasksStatuses'
        ])

        try:
            res = self.collect_cmd_output(
                'vdsm-client Host getConnectedStoragePools'
            )
            if res['status'] == 0:
                pools = json.loads(res['output'])
                for pool in pools:
                    self.add_cmd_output(
                        'vdsm-client StoragePool getSpmStatus'
                        ' storagepoolID={}'.format(pool)
                    )
        except ValueError as e:
            self._log_error(
                'vdsm-client Host getConnectedStoragePools: %s' % (e)
            )

        try:
            res = self.collect_cmd_output('vdsm-client Host getStorageDomains')
            if res['status'] == 0:
                sd_uuids = json.loads(res['output'])
                dump_volume_chains_cmd = 'vdsm-tool dump-volume-chains %s'
                self.add_cmd_output([
                    dump_volume_chains_cmd % uuid for uuid in sd_uuids
                ])
        except ValueError as e:
            self._log_error(
                'vdsm-client Host getStorageDomains: %s' % (e)
            )

    def _add_vdsm_forbidden_paths(self):
        """Add confidential sysprep vfds under /run/vdsm to
         forbidden paths """

        for file_path in glob.glob("/run/vdsm/*"):
            if file_path.endswith(('.vfd', '/isoUploader', '/storage')):
                self.add_forbidden_path(file_path)
