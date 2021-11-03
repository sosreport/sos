# Copyright Red Hat 2021, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import shutil

from sos.collector.transports import RemoteTransport


class LocalTransport(RemoteTransport):
    """
    A 'transport' to represent a local node. No remote connection is actually
    made, and all commands set to be run by this transport are executed locally
    without any wrappers.
    """

    name = 'local_node'

    def _connect(self, password):
        return True

    def _disconnect(self):
        return True

    @property
    def connected(self):
        return True

    def _retrieve_file(self, fname, dest):
        self.log_debug("Moving %s to %s" % (fname, dest))
        shutil.copy(fname, dest)
        return True

    def _format_cmd_for_exec(self, cmd):
        return cmd

    def _read_file(self, fname):
        if os.path.exists(fname):
            with open(fname, 'r') as rfile:
                return rfile.read()
        self.log_debug("No such file: %s" % fname)
        return ''

# vim: set et ts=4 sw=4 :
