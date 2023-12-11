# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin, RedHatPlugin
from sos.utilities import is_executable


class Slurm(Plugin, UbuntuPlugin, RedHatPlugin):

    short_desc = "Slurm Workload Manager"

    plugin_name = 'slurm'
    profiles = ('hpc',)
    packages = (
        # Ubuntu
        'slurm-wlm',
        'slurmd',
        'slurmdbd',
        'slurmctld',
        # EL
        'slurm',
        'slurm-slurmctld',
        'slurm-slurmd',
        'slurm-slurmdbd',
    )
    services = (
        'slurmd',
        'slurmdbd',
        'slurmctld',
    )

    def setup(self):
        """ Slurm Workload Manager
        """

        self.add_copy_spec([
            '/etc/slurm/*.conf',
            '/var/run/slurm/conf/*.conf',
        ])

        if is_executable('sinfo'):
            self.add_cmd_output([
                'sinfo --all --list-reasons --long',
                'sinfo --all --long',
            ])

        if is_executable('squeue'):
            self.add_cmd_output([
                'squeue --all --long',
            ])

        scontrol_cmds = [
            'aliases',
            'assoc_mgr',
            'bbstat',
            'burstBuffer',
            'config',
            'daemons',
            'dwstat',
            'federation',
            'frontend',
            'job',
            'licenses',
            'node',
            'partition',
            'reservation',
            'slurmd',
            'step',
            'topology',
        ]

        if is_executable('scontrol'):
            self.add_cmd_output(
                [f"scontrol show {i}" for i in scontrol_cmds]
            )

        config_file = '/etc/slurm/slurm.conf'

        if not self.path_exists(config_file):
            config_file = '/var/run/slurm/conf/slurm.conf'

        slurmd_log_file = '/var/log/slurmd.log'
        slurmctld_log_file = '/var/log/slurmctld.log'

        try:
            with open(config_file, 'r') as cf:
                for line in cf.read().splitlines():
                    if not line:
                        continue
                    words = line.split('=')
                    if words[0].strip() == 'SlurmdLogFile':
                        slurmd_log_file = words[1].strip()
                    if words[0].strip() == 'SlurmctldLogFile':
                        slurmctld_log_file = words[1].strip()
        except IOError as error:
            self._log_error('Could not open conf file %s: %s' %
                            (config_file, error))

        if not self.get_option("all_logs"):
            self.add_copy_spec([
                slurmd_log_file,
                slurmctld_log_file,
            ])
        else:
            self.add_copy_spec([
                f"{slurmd_log_file}*",
                f"{slurmctld_log_file}*",
            ])

    def postproc(self):
        conf_paths = [
            "/etc/slurm",
            "/var/run/slurm/conf",
        ]

        slurm_keys = [
            'AccountingStoragePass',
            'JobCompPass',
        ]
        slurm_keys_regex = r"(^\s*(%s)\s*=\s*)(.*)" % "|".join(slurm_keys)
        slurmdbd_key_regex = r'(^\s*(StoragePass)\s*=\s*)(.*)'

        sub = r'\1********'

        for conf_path in conf_paths:
            self.do_file_sub(
                f'{conf_path}/slurm.conf',
                slurm_keys_regex, sub
            )
            self.do_file_sub(
                f'{conf_path}/slurmdbd.conf',
                slurmdbd_key_regex, sub
            )
