# Copyright (C) 2024 Red Hat, Inc., Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import pwd
from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


class Instructlab(Plugin, IndependentPlugin):
    """
    This plugin is used to capture information about
    Instructlab installations.
    InstructLab is an open source project for enhancing
    large language models (LLMs) used in generative
    artificial intelligence (gen AI) applications.
    Instructlab can run either as a container, or directly
    outside a container.
    """

    short_desc = 'Instructlab'
    plugin_name = 'instructlab'
    profiles = ('ai',)
    containers = ('instructlab', 'ilab',)
    commands = ('ilab',)

    option_list = [
        PluginOpt('ilab-user', default='cloud-user', val_type=str,
                  desc='user that runs instructlab'),
        PluginOpt('ilab-conf-dir', default='', val_type=str,
                  desc='instructlab data directory'),
        PluginOpt('get-cache', default=False,
                  desc='Capture models and osci cached data')
    ]

    def setup(self):
        cont_share_conf_path = "/usr/share/instructlab/config"
        cont_opt_path = "/opt/app-root/src"
        # .cache dir contains the models and oci directories
        # which can be quite big. We'll gather this only if
        # specifying it via command line option
        cache_dir = ".cache/instructlab"
        # .config is where the configuration yaml files can
        # be found. We gather this always.
        config_dir = ".config/instructlab"
        # In the .local directory we can find datasets,
        # chat logs, taxonomies, and other very useful data
        # We gather this always.
        local_share_dir = ".local/share/instructlab"

        # container paths
        cont_cache_path = self.path_join(cont_opt_path, cache_dir)
        cont_config_path = self.path_join(cont_opt_path, config_dir)
        cont_local_path = self.path_join(cont_opt_path, local_share_dir)

        self.add_forbidden_path([
            self.path_join(cont_local_path,
                           "taxonomy/.git"),
            self.path_join(cont_local_path, "taxonomy/.github"),
            self.path_join(cont_opt_path,
                           "src/.local/share/instructlab/taxonomy/.git"),
            self.path_join(cont_opt_path,
                           "src/.local/share/instructlab/taxonomy/.github"),
        ])

        subcmds = [
            'taxonomy diff',
            'taxonomy diff --taxonomy-base=empty',
            'system info',
            'model list',
            'config show',
        ]

        data_dirs = [
            'data',
            'generated',
            'taxonomy',
            'taxonomy_data',
            'chatlogs',
            'checkpoints',
            'datasets',
            'internal',
            'phased',
        ]

        # If containerized, run commands in containers
        try:
            ilab_con = self.get_all_containers_by_regex("instructlab*")[0][1]
        except Exception:  # pylint: disable=broad-except
            ilab_con = None

        self.add_copy_spec(
            [f"{cont_share_conf_path}/rhel_ai_config.yaml",
             f"{cont_config_path}/config.yaml"],
            container=ilab_con
        )
        self.add_copy_spec(
            [self.path_join(cont_local_path, data_dir)
             for data_dir in data_dirs],
            container=ilab_con
        )
        self.add_cmd_output(
            [f"ilab {sub}" for sub in subcmds],
            container=ilab_con
        )
        self.add_dir_listing(
            cont_cache_path,
            recursive=True,
            container=ilab_con
        )
        if self.get_option('get-cache'):
            self.add_copy_spec(
                f"{cont_cache_path}",
                container=ilab_con
            )
        self.add_container_logs(list(self.containers))

        ilab_user = self.get_option("ilab-user")
        try:
            user_pwd = pwd.getpwnam(ilab_user)
        except KeyError:
            # The user doesn't exist, this will skip the rest
            self._log_warn(
                f'User "{ilab_user}" does not exist, will not '
                'collect Instructlab information. Use '
                '`-k instructlab.ilab-user` option to define '
                'the user to use to collect data for Instructlab')
            return

        if user_pwd:
            ilab_dir = user_pwd.pw_dir
            if self.get_option("ilab-conf-dir"):
                ilab_dir = self.path_join(
                    ilab_dir, self.get_option('ilab-conf-dir')
                )
            data_dirs_base = self.path_join(ilab_dir, local_share_dir)

            self.add_copy_spec(self.path_join(ilab_dir, config_dir))
            self.add_copy_spec([
                self.path_join(data_dirs_base, data_dir)
                for data_dir in data_dirs
            ])
            self.add_dir_listing(
                self.path_join(ilab_dir, cache_dir),
                recursive=True
            )

            if self.get_option("get-cache"):
                self.add_copy_spec(
                    self.path_join(ilab_dir, cache_dir)
                )

# vim: set et ts=4 sw=4 :
