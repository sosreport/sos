# Copyright (C) 2018 Red Hat, Inc. Daniel Walsh <dwalsh@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin, PluginOpt


class Podman(Plugin, RedHatPlugin, UbuntuPlugin):
    """Podman is a daemonless container management engine, and this plugin is
    meant to provide diagnostic information for both the engine and the
    containers that podman is managing.

    General status information will be collected from podman commands, while
    detailed inspections of certain components will provide more insight
    into specific container problems. This detailed inspection is provided for
    containers, images, networks, and volumes. Per-entity inspections will be
    recorded in subdirs within sos_commands/podman/ for each of those types.
    """

    short_desc = 'Podman containers'
    plugin_name = 'podman'
    profiles = ('container',)
    packages = ('podman',)

    option_list = [
        PluginOpt('all', default=False,
                  desc='collect for all containers, even terminated ones',
                  long_desc=(
                    'Enable collection for all containers that exist on the '
                    'system regardless of their running state. This may cause '
                    'a significant increase in sos archive size, especially '
                    'when combined with the \'logs\' option.')),
        PluginOpt('logs', default=False,
                  desc='collect stdout/stderr logs for containers',
                  long_desc=(
                    'Capture \'podman logs\' output for discovered containers.'
                    ' This may be useful or not depending on how/if the '
                    'container produces stdout/stderr output. Use cautiously '
                    'when also using the \'all\' option.')),
        PluginOpt('size', default=False,
                  desc='collect image sizes for podman ps'),
        PluginOpt('allusers', default=False,
                  desc='collect for all users, including non root users')
    ]

    def setup(self):
        self.add_cmd_tags({
            'podman images': 'podman_list_images',
            'podman ps': 'podman_list_containers'
        })

        subcmds = [
            'info',
            'image trust show',
            'images',
            'images --digests',
            'pod ps',
            'port --all',
            'ps',
            'ps -a',
            'stats --no-stream --all',
            'version',
            'volume ls',
            'system df -v',
        ]

        # Collect directory listings
        self.add_dir_listing([
            '/etc/cni',
            '/etc/containers'
        ], recursive=True)

        # Always collect for root (None represents root user)
        self._collect_for_user(None, '', subcmds)

        # Only collect for non-root users if allusers option is enabled
        if self.get_option('allusers'):
            non_root_users = self._get_non_root_users()
            for user in non_root_users:
                if self._user_has_containers(user):
                    self._collect_for_user(user, f'{user}/', subcmds)

    def _collect_for_user(self, user, subdir, subcmds):
        """Collect all podman data for a specific user"""
        self._collect_basic_info(user, subdir, subcmds)
        self._collect_networks(user, subdir)

        containers = self._get_containers_list(user)
        images = self._get_images_list(user)
        volumes = self._get_volumes_list(user)

        self._inspect_containers(user, subdir, containers)
        self._inspect_images(user, subdir, images)
        self._inspect_volumes(user, subdir, volumes)
        self._collect_logs(user, subdir, containers)

    def _get_non_root_users(self):
        """Get list of non-root users from the system"""
        users = []
        result = self.exec_cmd("lslogins -u -o USER --noheadings")
        if result['status'] == 0:
            for line in result['output'].splitlines():
                user = line.strip()
                if user and user != "root":
                    users.append(user)
        return users

    def _user_has_containers(self, user):
        """Check if user has any containers before collecting data"""
        cmd = self.exec_cmd("podman ps -aq", runas=user)
        return cmd['status'] == 0 and cmd['output'].strip()

    def _collect_basic_info(self, user, subdir, subcmds):
        """Collect basic podman information and status"""
        self.add_cmd_output(
            [f"podman {s}" for s in subcmds],
            subdir=subdir,
            runas=user
        )

        # separately grab ps -s as this can take a *very* long time
        if self.get_option('size'):
            self.add_cmd_output(
                'podman ps -as',
                priority=100,
                subdir=subdir,
                runas=user
            )

    def _collect_networks(self, user, subdir):
        """Collect podman network information"""
        self.collect_cmd_output(
            'podman network ls',
            subdir=f'{subdir}networks',
            tags='podman_list_networks',
            runas=user
        )
        pnets = self.exec_cmd(
            'podman network ls',
            runas=user,
            stderr=False
        )
        if pnets['status'] == 0:
            nets = [
                pn.split()[0]
                for pn in pnets['output'].splitlines()[1:]
            ]
            self.add_cmd_output(
                [f"podman network inspect {net}" for net in nets],
                subdir=f'{subdir}networks',
                tags='podman_network_inspect',
                runas=user
            )

    def _get_containers_list(self, user):
        """Get list of container IDs for the specified user"""
        if user is None:
            # Use built-in method for root user
            return [
                c[0] for c in self.get_containers(
                    runtime='podman',
                    get_all=self.get_option('all')
                )
            ]

        # For non-root users, use podman ps -q
        cmd = "podman ps -q"
        if self.get_option('all'):
            cmd = "podman ps -aq"

        containers_data = self.exec_cmd(cmd, runas=user, stderr=False)
        if containers_data['status'] == 0:
            return [
                line.strip()
                for line in containers_data['output'].splitlines()
                if line.strip()
            ]
        return []

    def _get_images_list(self, user):
        """Get list of images for the specified user"""
        if user is None:
            # Use built-in method for root user
            return self.get_container_images(runtime='podman')

        # For non-root users, collect image information manually
        img_format = '{{.Repository}}:{{.Tag}} {{.ID}}'
        image_data = self.exec_cmd(
            f'podman images --no-trunc --format "{img_format}"',
            runas=user,
            stderr=False
        )

        if image_data['status'] == 0:
            return [
                line.rsplit(" ", 1)
                for line in image_data['output'].strip().split("\n")
                if line.strip()
            ]
        return []

    def _get_volumes_list(self, user):
        """Get list of volumes for the specified user"""
        if user is None:
            # Use built-in method for root user
            return self.get_container_volumes(runtime='podman')

        # For non-root users, collect volume information manually
        vol_format = '{{.Name}}'
        vols = self.exec_cmd(
            f'podman volume ls --format "{vol_format}"',
            runas=user,
            stderr=False
        )
        if vols['status'] == 0:
            return [
                v for v in vols['output'].splitlines()
                if v.strip()
            ]
        return []

    def _inspect_containers(self, user, subdir, containers):
        """Collect detailed inspection data for containers"""
        for container in containers:
            self.add_cmd_output(
                f"podman inspect {container}",
                subdir=f'{subdir}containers',
                tags='podman_container_inspect',
                runas=user
            )

    def _inspect_images(self, user, subdir, images):
        """Collect detailed inspection data for images"""
        for img in images:
            name, img_id = img
            insp = name if 'none' not in name else img_id
            self.add_cmd_output(
                f"podman inspect {insp}",
                subdir=f'{subdir}images',
                tags='podman_image_inspect',
                runas=user
            )
            self.add_cmd_output(
                f"podman image tree {insp}",
                subdir=f'{subdir}images/tree',
                tags='podman_image_tree',
                runas=user
            )

    def _inspect_volumes(self, user, subdir, volumes):
        """Collect detailed inspection data for volumes"""
        for vol in volumes:
            self.add_cmd_output(
                f"podman volume inspect {vol}",
                subdir=f'{subdir}volumes',
                tags='podman_volume_inspect',
                runas=user
            )

    def _collect_logs(self, user, subdir, containers):
        """Collect container logs if logs option is enabled"""
        if self.get_option('logs'):
            for con in containers:
                self.add_cmd_output(
                    f"podman logs -t {con}",
                    subdir=f'{subdir}containers',
                    priority=50,
                    runas=user
                )

    def postproc(self):
        # Attempts to match key=value pairs inside container inspect output
        # for potentially sensitive items like env vars that contain passwords.
        # Typically, these will be seen in env elements or similar, and look
        # like this:
        #             "Env": [
        #                "mypassword=supersecret",
        #                "container=oci"
        #             ],
        # This will mask values when the variable name looks like it may be
        # something worth obfuscating.

        env_regexp = r'(?P<var>(pass|key|secret|PASS|KEY|SECRET).*?)=' \
                      '(?P<value>.*?)"'
        self.do_cmd_output_sub('*inspect*', env_regexp,
                               r'\g<var>=********"')

# vim: set et ts=4 sw=4 :
