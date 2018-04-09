# Copyright (C) 2015 Red Hat, Inc.

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin
import os.path


class AtomicHost(Plugin, RedHatPlugin):
    """ Atomic Host """

    plugin_name = "atomichost"
    profiles = ('container',)
    option_list = [
        ("info", "gather atomic info for each image", "fast", False)
    ]

    def check_enabled(self):
        return self.policy.in_container()

    def setup(self):
        self.add_copy_spec("/etc/ostree/remotes.d")
        self.add_cmd_output("atomic host status")

        if self.get_option('info'):
            # The 'docker images' command may include duplicate rows of
            # output (repeated "IMAGE ID" values). Use a set to filter
            # these out and only obtain 'docker info' data once per image
            # identifier.
            images = self.get_command_output("docker images -q")['output']
            for image in set(images.splitlines()):
                self.add_cmd_output("atomic info {0}".format(image))

# vim: set et ts=4 sw=4 :
