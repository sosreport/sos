# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin, PluginOpt
import pwd
import json

class Juju(Plugin, UbuntuPlugin):

    short_desc = 'Juju orchestration tool'

    plugin_name = 'juju'
    profiles = ('virt', 'sysmgmt')

    # Using files instead of packages here because there is no identifying
    # package on a juju machine.
    files = ('/var/log/juju',)

    option_list = [
        PluginOpt('is-feature', default=False, val_type=bool,
                  desc='Apply PR feature functionality'),
        PluginOpt('juju-user', default='ubuntu', val_type=str,
                  desc='Juju client user'),
        PluginOpt('controllers', default='', val_type=str,
                  desc='collect for specified Juju controllers'), 
        PluginOpt('models', default='', val_type=str,
                  desc='collect for specified Juju models'),
    ]

    def setup(self):
        # Juju service names are not consistent through deployments,
        # so we need to use a wildcard to get the correct service names.
        for service in self.get_service_names("juju*"):
            self.add_journal(service)
            self.add_service_status(service)

        # Get agent configs for each agent.
        self.add_copy_spec("/var/lib/juju/agents/*/agent.conf")

        # Get a directory listing of /var/log/juju and /var/lib/juju
        self.add_dir_listing([
            '/var/log/juju*',
            '/var/lib/juju*'
        ], recursive=True)

        if self.get_option("all_logs"):
            # /var/lib/juju used to be in the default capture moving here
            # because it usually was way to big.  However, in most cases you
            # want all logs you want this too.
            self.add_copy_spec([
                "/var/log/juju",
                "/var/lib/juju",
                "/var/lib/juju/**/.*",
            ])
            self.add_forbidden_path("/var/lib/juju/kvm")
        else:
            # We need this because we want to collect to the limit of all
            # logs in the directory.
            self.add_copy_spec("/var/log/juju/*.log")

        # Only run the feature code if this plugin option is set
        if not self.get_option("is-feature"):
            return

        juju_user = self.get_option("juju-user")
        try:
            pwd.getpwnam(juju_user)
        except KeyError:
            # The user doesn't exist, this will skip the rest
            self._log_warn(f'User "{juju_user}" does not exist, will not collect Juju information.')
            return

        user_context = f'sudo -u {juju_user}'

        controllers_json = self.collect_cmd_output(f"{user_context} juju controllers --format=json")
        if controllers_json['status'] == 0:
            desired_controllers = set(self.get_option('controllers').split(' '))
            # If a controller option is supplied, use it. Otherwise, get all controllers
            if desired_controllers and desired_controllers != {''}:
                controllers = desired_controllers
            else:
                controllers = set(json.loads(controllers_json["output"])["controllers"].keys())
        else:
            controllers =  {}

        if self.get_option('controllers') and self.get_option('models'):
            self._log_warn('Options: controllers, models are mutually exclusive.')
            return

        # Specific models
        if self.get_option('models'):
            models = self.get_option('models').split(' ')
            commands = [f"{user_context} juju status -m {model} --format=json" for model in models]
            for command in commands:
                self.collect_cmd_output(command)

        # All controllers and all models OR specific controllers and all models for each
        else:
            for controller in controllers:
                models_json = self.exec_cmd(f"{user_context} juju models --all -c {controller} --format=json")
                if models_json['status'] == 0:
                    models = [model['short-name'] for model in json.loads(models_json['output'])["models"]]
                    commands = [f"{user_context} juju status -m {controller}:{model} --format=json" for model in models]
                    for command in commands:
                        self.collect_cmd_output(command)

    def postproc(self):
        agents_path = "/var/lib/juju/agents/*"
        protect_keys = [
            "sharedsecret",
            "apipassword",
            "oldpassword",
            "statepassword",
        ]

        # Redact simple yaml style "key: value".
        keys_regex = fr"(^\s*({'|'.join(protect_keys)})\s*:\s*)(.*)"
        sub_regex = r"\1*********"
        self.do_path_regex_sub(agents_path, keys_regex, sub_regex)
        # Redact certificates
        self.do_file_private_sub(agents_path)

# vim: set et ts=4 sw=4 :
