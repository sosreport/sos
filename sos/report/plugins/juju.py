# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import pwd
import json
import re
from sos.report.plugins import Plugin, UbuntuPlugin, PluginOpt


class Juju(Plugin, UbuntuPlugin):
    """The Juju plugin is aimed at collecting Juju-related logs,
    configurations, and controller/model state(s).

    Logs and agent configuration information (/var/log/juju and /var/lib/juju)
    is collected by default since these are useful for troubleshooting.

    The Juju state collection is disabled by default and can be enabled with
    the 'juju-state' option. Collecting Juju state is safe in theory, but it
    does act on the live controller(s)/model(s) and is therefore optional.

    The default Juju state collection collects all controllers and models that
    the 'juju-user' (default=ubuntu) has access to.

    Specific controllers or models can be collected using the 'controllers'
    and 'models' options.

    Important: the string list is whitespace delimited, not colon delimited
    (sos plugin standard). This is due to the underlying Juju CLI accepting
    specific models in the format 'controller:model' and whitespaces are not
    allowed in either controller and model names.

    Example: models="controller_a:model_x controller_b:model_y"
    """

    short_desc = 'Juju orchestration tool'

    plugin_name = 'juju'
    profiles = ('virt', 'sysmgmt',)

    # Using files instead of packages here because there is no identifying
    # package on a juju machine.
    files = ('/var/log/juju',)

    option_list = [
        PluginOpt(
            "juju-state",
            default=False,
            val_type=bool,
            desc="Include Juju state in the report",
        ),
        PluginOpt(
            "juju-user",
            default="ubuntu",
            val_type=str,
            desc="Juju client user.",
        ),
        PluginOpt(
            "controllers",
            default="",
            val_type=str,
            desc="Collect Juju state for specified controllers. Uses a \
            whitespace delimited list.",
        ),
        PluginOpt(
            "models",
            default="",
            val_type=str,
            desc="Collect Juju state for specified models. Uses a whitespace \
            delimited list.",
        ),
    ]

    agent_name = ""

    def setup(self):
        # Juju service names are not consistent through deployments,
        # so we need to use a wildcard to get the correct service names.
        for service in self.get_service_names("juju*"):
            self.add_journal(service)
            self.add_service_status(service)

        juju_agent_cmds = {
            'juju_engine_report': 'depengine',
            'juju_goroutines': 'debug/pprof/goroutine?debug=1',
            'juju_heap_profile': 'debug/pprof/heap?debug=1',
            'juju_metrics': 'metrics',
            'juju_pubsub_report': 'pubsub',
            'juju_presence_report': 'presence',
            'juju_statepool_report': 'statepool',
            'juju_statetracker_report': ('debug/pprof/juju/state/tracker?'
                                         'debug=1'),
            'juju_unit_status': 'units?action=status',
        }

        if self.path_exists("/var/lib/juju/agents"):
            for cmd, agent_cmd in juju_agent_cmds.items():
                self.add_cmd_output(
                    self._juju_agent(agent_cmd),
                    suggest_filename=cmd
                )

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
            self.add_forbidden_path("/var/lib/juju/tools")
        else:
            # We need this because we want to collect to the limit of all
            # logs in the directory.
            self.add_copy_spec("/var/log/juju/*.log")

        # Only include the Juju state report if this plugin option is set
        if not self.get_option("juju-state"):
            return

        juju_user = self.get_option("juju-user")
        try:
            pwd.getpwnam(juju_user)
        except KeyError:
            self._log_warn(
                f'User "{juju_user}" does not exist, '
                "will not collect Juju information."
            )
            return

        if self.get_option("controllers") and self.get_option("models"):
            self._log_warn(
                "Options: controllers, models are mutually exclusive. "
                "Will not collect Juju information."
            )
            return

        controllers_json = self.collect_cmd_output(
            "juju controllers --format=json", runas=juju_user
        )
        if controllers_json["status"] == 0:
            desired_controllers = set(
                self.get_option("controllers").split(" ")
            )
            # If a controller option is supplied, use it. Otherwise, get all
            #  controllers
            if desired_controllers and desired_controllers != {""}:
                controllers = desired_controllers
            else:
                controllers = set(
                    json.loads(controllers_json["output"])[
                        "controllers"
                    ].keys()
                )
        else:
            controllers = {}

        # Specific models
        if self.get_option("models"):
            for model in self.get_option("models").split(" "):
                command = f"juju status -m {model} --format=json"
                self.add_cmd_output(command, runas=juju_user)

        # All controllers and all models OR specific controllers and all
        #  models for each
        else:
            for controller in controllers:
                models_json = self.exec_cmd(
                    f"juju models --all -c {controller} --format=json",
                    runas=juju_user,
                )
                if models_json["status"] == 0:
                    models = json.loads(models_json["output"])["models"]
                    for model in models:
                        short_name = model["short-name"]
                        command = (
                            f"juju status -m {controller}:{short_name} "
                            f"--format=json"
                        )
                        self.add_cmd_output(command, runas=juju_user)

    def _juju_agent(self, command):
        if self.agent_name == "":
            for dir_name in self.listdir("/var/lib/juju/agents"):
                if re.search('machine-*|controller-*|application-*', dir_name):
                    self.agent_name = dir_name
                    break

        return f"juju-introspect --agent={self.agent_name} {command}"

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

        # Redact keys from Nova compute logs
        self.do_path_regex_sub("/var/log/juju/unit-nova-compute-(.*).log(.*)",
                               r"auth\(key=(.*)\)", r"auth(key=******)")

        # Redact certificates
        self.do_file_private_sub(agents_path)
        self.do_cmd_private_sub('juju controllers')

# vim: set et ts=4 sw=4 :
