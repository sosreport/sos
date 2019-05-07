# Copyright (C) 2013 Adam Stokes <adam.stokes@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from json import loads as json_loads
from sos.plugins import Plugin, UbuntuPlugin


class Juju(Plugin, UbuntuPlugin):
    """ Juju orchestration tool
    """

    plugin_name = 'juju'
    profiles = ('virt', 'sysmgmt')
    files = ('/usr/bin/juju', '/usr/bin/juju-run', '/snap/bin/juju')

    option_list = [
        ("juju-user", "The user to run juju commands as", "", "ubuntu")
    ]

    # Get the configuration of each application deployed in a model
    def collect_app_config(self, username, modelname, statusfilespath):
        statusinfo = {}
        try:
            with open(statusfilespath, 'r') as fd:
                statusinfo = json_loads(fd.read())
        except Exception:
            return
        if "applications" in statusinfo:
            for appname, appinfo in statusinfo["applications"].items():
                # Get the application config for every application in every
                # model
                self.add_cmd_output(
                    "sudo -i -u {} juju config --format yaml -m {} {}".format(
                        username, modelname, appname
                    )
                )

    # Get some information pertaining to each model
    def collect_model_output(self, username, modelsfilepath):
        modelsinfo = {}
        try:
            with open(modelsfilepath, 'r') as fd:
                modelsinfo = json_loads(fd.read())
        except Exception:
            return
        if "models" in modelsinfo:
            for model in modelsinfo["models"]:
                if "short-name" in model:
                    modelname = model["short-name"]
                    # Run these commands for each model
                    self.add_cmd_output(
                        [
                            ("sudo -i -u {} juju debug-log "
                             "-n 500 --no-tail -m {}"
                             .format(username, modelname)),
                            ("sudo -i -u {} juju model-config "
                             "--format yaml -m {}"
                             .format(username, modelname)),
                        ]
                    )
                    # Get the model status as json so we can dig deeper
                    status = self.get_cmd_output_now(
                        "sudo -i -u {} juju status -m {} --format json".format(
                            username, modelname
                        )
                    )
                    self.collect_app_config(username, modelname, status)

    # Get some high level juju configuration and start processing model info
    def collect_juju_output(self, username):
        # Run these commands once, no model or app option required
        juju_cmds = [
            "juju clouds --format yaml",
            "juju controller-config --format yaml",
            "juju storage --format yaml",
            "juju storage-pools --format yaml",
            "juju spaces --format yaml",
            "juju credentials --format yaml",
            "juju model-defaults --format yaml",
            "juju show-controller --format yaml",
        ]

        # Get the model information as json so we can dig deeper
        models = self.get_cmd_output_now(
            "sudo -i -u {} juju models --format json".format(username)
        )
        self.collect_model_output(username, models)

        # Use sudo to run the commands as the appropriate user and name the
        # files something sane
        for cmd in juju_cmds:
            # The file names can be long and confusing from the juju commands,
            # clean them up and give them an approriate extension if possible
            self.add_cmd_output("sudo -i -u {} {}".format(username, cmd))

    def setup(self):
        # Make sure it looks like juju is configured before continuing
        username = self.get_option("juju-user")
        homedir = os.path.expanduser("~" + username)

        if os.path.exists(homedir + "/.local/share/juju"):
            self.collect_juju_output(username)

    # TODO Add more keys as we see fit
    def postproc(self):
        juju_config_keys = [
            "corosync_key",
            "password",
            "root-password",
            "sst-password",
            "credentials",
            "client_password",
            "endpoint-tls-ca",
            "docker-logins",
            "license-key",
            "registry-credentials",
            "admin-password",
            "ldap-password",
            "mem-password",
            "nsx-password",
            "plumgrid-password",
            ]

        # Handle the case where the key and value are on separate lines.
        # In Juju, a yaml key might be set and have no subkey 'value'.
        # This is the case when the subkey for the key 'source' has
        # the value 'unset'.
        # Hence, we need to run a conditional statement below in order
        # to match the case when a certain key we want to substitute
        # is unset, meaning that it has no 'value' subkey set, so, we
        # need to match for the string right below it which is 'type: .*'
        # In the case that indeed the 'source' subkey is set to anything
        # else other than 'unset' we will match until the subkey 'value'
        # and we can do the substitution for the whole match.
        # No stars added to the substitution as this will look weird
        # on the case that we hit the 'source: unset' case and wil show
        # as 'source: unset********'.
        juju_config_regex = (
            r"(?m)(.*(%s):[\s\S]+?source: "
            r"(unset)?(?(3)[\s\S]+?type: .*|[\s\S]+?value: )).*"
            % "|".join(juju_config_keys)
        )

        juju_config_subst = r"\1"

        # Replace all Certificate / Private key information from files
        self.do_cmd_private_sub('juju')

        self.do_cmd_output_sub(
            "*juju*config*yaml*", juju_config_regex, juju_config_subst
        )

# vim: set et ts=4 sw=4 :
