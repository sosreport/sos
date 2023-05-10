# Copyright (C) 2023 Red Hat, Inc., Jose Castillo <jcastillo@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Rhc(Plugin, RedHatPlugin):

    """
    RHC is a client tool and daemon that connects the system
    to Red Hat hosted services enabling system and
    subscription management. This plugin captures
    configuration files and the output of 'rhc status'.
    """
    short_desc = 'Red Hat client for remote host configured services'

    plugin_name = "rhc"
    packages = ("rhc", )

    def setup(self):
        self.add_copy_spec([
            "/etc/rhc/*",
        ])

        self.add_cmd_output([
            "rhc status",
        ])

    def postproc(self):
        # hide workers/foreman_rh_cloud.toml FORWARDER_PASSWORD
        # Example for scrubbing FORWARDER_PASSWORD
        #
        # "FORWARDER_PASSWORD=F0rW4rd3RPassW0rD"
        #
        # to
        #
        # "FORWARDER_PASSWORD= ********

        self.do_path_regex_sub("/etc/rhc/workers/foreman_rh_cloud.toml",
                               r"(FORWARDER_PASSWORD\s*=\s*)(.+)(\"\,)",
                               r"\1********\3")
# vim: set et ts=4 sw=4 :
