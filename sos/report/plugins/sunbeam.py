# Copyright (C) 2024 Canonical Ltd., Arif Ali <arif.ali@canonical.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import pwd
import yaml
from sos.report.plugins import Plugin, UbuntuPlugin, PluginOpt


class Sunbeam(Plugin, UbuntuPlugin):

    short_desc = "Sunbeam Openstack Controller"

    plugin_name = "sunbeam"
    profiles = ('cloud',)
    packages = ('openstack',)

    common_dir = '/var/snap/openstack/common'

    option_list = [
        PluginOpt('sunbeam-user', default='ubuntu', val_type=str,
                  desc='The user used for sunbeam installation'),
        PluginOpt('juju-allow-login', default=False, val_type=bool,
                  desc='Allow sos to login to juju'),
    ]

    def setup(self):

        self.add_service_status('snap.openstack.*')

        self.add_copy_spec([
            f'{self.common_dir}/hooks.log',
            f'{self.common_dir}/state/daemon.yaml',
            f'{self.common_dir}/state/truststore/sunbeam.maas.yaml',
            f'{self.common_dir}/state/database/info.yaml',
            f'{self.common_dir}/state/database/cluster.yaml',
            '/var/snap/openstack/current/config.yaml',
        ])

        sunbeam_user = self.get_option("sunbeam-user")
        try:
            user_pwd = pwd.getpwnam(sunbeam_user)
        except KeyError:
            # The user doesn't exist, this will skip the rest
            self._log_warn(
                f'User "{sunbeam_user}" does not exist, will not collect juju '
                'information. Use `-k sunbeam.sunbeam-user` option to define '
                'the user to use to collect data for sunbeam')
            return

        if user_pwd:
            self.add_cmd_output([
                'sunbeam cluster list',
                'sunbeam cluster list --format yaml',
                'sunbeam manifest list',
                'sunbeam deployment list',
            ], snap_cmd=True, runas=sunbeam_user)

            manifest_raw = self.collect_cmd_output(
                'sunbeam manifest list --format yaml',
                runas=sunbeam_user
            )

            if manifest_raw['status'] == 0:
                manifests = yaml.safe_load(manifest_raw['output'])
                for manifest in manifests:
                    self.add_cmd_output(
                        f'sunbeam manifest show {manifest["manifestid"]}',
                        snap_cmd=True, runas=sunbeam_user
                    )

            deployment_raw = self.collect_cmd_output(
                'sunbeam deployment list --format yaml',
                runas=sunbeam_user
            )

            if deployment_raw['status'] == 0:
                deployments = yaml.safe_load(deployment_raw['output'])
                for deployment in deployments['deployments']:
                    self.add_cmd_output([
                        f'sunbeam deployment show {deployment["name"]}',
                        f'sunbeam deployment show {deployment["name"]} '
                        '--format yaml',
                    ], snap_cmd=True, runas=sunbeam_user)

            sb_snap_homedir = f'{user_pwd.pw_dir}/snap/openstack/common'

            self.add_copy_spec([
                f"{sb_snap_homedir}/*.log",
                f"{sb_snap_homedir}/etc/**/*.log",
                f"{sb_snap_homedir}/etc/**/terraform.tfvars.json",
                f"{sb_snap_homedir}/logs/*.log",
                f"{sb_snap_homedir}/reports/*.yaml",
            ])

            if self.get_option("juju-allow-login"):
                self.exec_cmd(
                    f'su - {sunbeam_user} -c "sunbeam utils juju-login"')

            # This checks if the juju user is logged in, and if it is, then we
            # collect the juju information. It could be that the user was
            # already logged in from a prior session
            juju_whoami = self.exec_cmd('juju whoami', runas=sunbeam_user)
            juju_status = self.exec_cmd('juju status', runas=sunbeam_user,
                                        timeout=30)
            logged_in = False
            if juju_whoami['status'] == 0 or juju_status['status'] == 0:
                try:
                    j_whoami = juju_whoami['output'].splitlines()[0]
                    j_status = juju_status['output'].splitlines()[0]

                    if "Controller" in j_whoami or "Controller" in j_status:
                        self._get_juju_cmd_details(sunbeam_user)
                        logged_in = True
                except IndexError:
                    # One of the commands may not have gone through and hence
                    # not logged in
                    pass

            if not logged_in:
                self._log_warn(
                    "juju is not logged in, will not collect juju "
                    "information. Use `-k sunbeam.juju-allow-login=True` to "
                    "login or use `juju login` as the sunbeam user to "
                    "login")

    def _get_juju_cmd_details(self, user):
        self.add_cmd_output("juju controllers", runas=user, snap_cmd=True)
        juju_controllers = self.collect_cmd_output(
            "juju controllers --format json", runas=user)

        if juju_controllers['status'] == 0:
            juju_ctrl_json = json.loads(juju_controllers['output'])
            for controller in juju_ctrl_json['controllers'].keys():

                self.add_cmd_output([
                    f'juju models -c {controller}',
                    f'juju model-defaults -c {controller}',
                    f'juju controller-config -c {controller}',
                    f'juju controller-config -c {controller} --format json',
                ], runas=user, snap_cmd=True)

                juju_models = self.collect_cmd_output(
                    f'juju models -c {controller} --format json',
                    runas=user)

                if juju_models['status'] == 0:
                    juju_status_json = json.loads(juju_models['output'])

                    for model in juju_status_json['models']:

                        model_name = f'{controller}:{model["name"]}'

                        self.add_cmd_output([
                            f'juju status -m {model_name}',
                            f'juju status -m {model_name} --format json',
                            f'juju model-config -m {model_name}',
                            f'juju model-config -m {model_name} --format json',
                        ], runas=user, snap_cmd=True)

    def postproc(self):

        self.do_file_private_sub(
            f'{self.common_dir}/state/truststore/sunbeam.maas.yaml'
        )

        self.do_cmd_private_sub('juju controllers')
        self.do_cmd_private_sub('juju controller-config')

# vim: et ts=4 sw=4
