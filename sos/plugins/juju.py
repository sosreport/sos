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
import re
import glob
from sos.plugins import Plugin, UbuntuPlugin
from json import loads as json_loads


class Juju(Plugin, UbuntuPlugin):
    """ Juju orchestration tool
    """

    plugin_name = "juju"
    profiles = ("virt", "sysmgmt")
    files = ("/snap/bin/juju", "/usr/bin/juju")

    option_list = [
        ("juju-user", "The user to run juju commands as", "", "ubuntu")
    ]

    # Get the configuration of each application deployed in a model
    def collect_app_config(self, username, modelname, statusfilespath):
        statusinfo = {}
        # Juju config parameter values to sanitize in the output yaml
        juju_config_keys = [
            "password",
            "credentials",
            "client_password",
            "endpoint-tls-ca",
            "docker-logins",
            "license-key",
            "registry-credentials",
        ]

        # Handle the case where the key and value are on seperate lines
        # in a juju config yaml file
        juju_config_regex = (
            r"(?m)^(\s*)(((%s):((\n\1\s+.*)|\n)+)\1\s+value:\s*).*"
            % "|".join(juju_config_keys)
        )

        juju_config_subst = r"\1\2*********"

        try:
            fp = open(statusfilespath, "r")
            statusinfo = json_loads(fp.read())
            fp.close()
        except Exception:
            return
        if "applications" in statusinfo:
            for appname, appinfo in statusinfo["applications"].items():
                # Get the application config for every application in every
                # model
                cmd = "sudo -i -u {} juju config --format yaml -m {} {}".format(
                    username, modelname, appname
                )
                self.add_cmd_output(cmd)
                self.do_cmd_output_sub(
                    cmd, juju_config_regex, juju_config_subst
                )

    # Get some information pertaining to each model
    def collect_model_output(self, username, modelsfilepath):
        modelsinfo = {}
        try:
            fp = open(modelsfilepath, "r")
            modelsinfo = json_loads(fp.read())
            fp.close()
        except Exception:
            return
        if "models" in modelsinfo:
            for model in modelsinfo["models"]:
                if "short-name" in model:
                    modelname = model["short-name"]
                    # Run these commands for each model
                    self.add_cmd_output(
                        [
                            "su - {} -c 'juju debug-log -n 500 --no-tail -m {}'".format(
                                username, modelname
                            ),
                            "su - {} -c 'juju model-config --format yaml -m {}'".format(
                                username, modelname
                            ),
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

        # Certificates to sanitize in command output
        juju_config_certs = ["ca-cert"]

        # Will match and replace a certificat in a yaml file
        certs_regex = (
            r"((?m)^\s*(%s)\s*:\s*)(\|\s*\n\s+-+BEGIN (.*)"
            r"-+\s(\s+\S+\n)+\s+-+END )\4(-+)" % "|".join(juju_config_certs)
        )

        certs_sub_regex = r"\1*********"

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
            sudocmd = "sudo -i -u {} {}".format(username, cmd)
            self.add_cmd_output(sudocmd)
            self.do_cmd_output_sub(sudocmd, certs_regex, certs_sub_regex)

    def setup(self):
        # Make sure it looks like juju is configured before continuing
        username = self.get_option("juju-user")
        homedir = os.path.expanduser("~" + username)
        if os.path.exists(homedir + "/.local/share/juju"):
            self.collect_juju_output(username)

    # def postproc(self):
    #     juju_config_keys = [
    #         "password",
    #         "credentials",
    #         "client_password",
    #         "endpoint-tls-ca",
    #         "docker-logins",
    #         "license-key",
    #         "registry-credentials",
    #     ]

    #     juju_config_certs = ["ca-cert"]

    #     # Handle the case where the key and value are on seperate lines
    #     # in a juju config yaml file
    #     juju_config_regex = (
    #         r"(?m)^(\s*)(((%s):((\n\1\s+.*)|\n)+)\1\s+value:\s*).*"
    #         % "|".join(juju_config_keys)
    #     )
    #     juju_config_sub_regex = r"\1\2*********"

    #     # Will match and replace a certificat in a yaml file
    #     certs_regex = (
    #         r"((?m)^\s*(%s)\s*:\s*)(\|\s*\n\s+-+BEGIN (.*)"
    #         r"-+\s(\s+\S+\n)+\s+-+END )\4(-+)" % "|".join(juju_config_certs)
    #     )
    #     certs_sub_regex = r"\1*********"

    #     juju_username = self.get_option("juju-user")

    #     self.do_cmd_output_sub(
    #         output_dir + "/.*juju_config.*yaml.*",
    #         juju_config_regex,
    #         juju_config_sub_regex,
    #     )
    #     self.do_cmd_output_sub(
    #         output_dir + "/.*juju.*controller.*yaml.*",
    #         certs_regex,
    #         certs_sub_regex,
    #     )
        # juju_config_files = glob.glob(output_dir + "/juju_config*.yaml")
        # juju_cert_files = glob.glob(output_dir + "/juju*controller*.yaml")

        # for file in juju_config_files:
        #     try:
        #         fp = open(file, "r")
        #         result, replacements = re.subn(
        #             juju_config_regex, juju_config_sub_regex, fp.read()
        #         )
        #         fp.close()
        #         fp = open(file, "w")
        #         fp.write(result)
        #         fp.close()
        #     except Exception as e:
        #         msg = "regex substitution failed for '%s' with: '%s'"
        #         self.log_error(msg % (file, e))

        # for file in juju_cert_files:
        #     try:
        #         fp = open(file, "r")
        #         result, replacements = re.subn(
        #             certs_regex, certs_sub_regex, fp.read()
        #         )
        #         fp.close()
        #         fp = open(file, "w")
        #         fp.write(result)
        #         fp.close()
        #     except Exception as e:
        #         msg = "regex substitution failed for '%s' with: '%s'"
        #         self.log_error(msg % (file, e))


# vim: set et ts=4 sw=4 :
