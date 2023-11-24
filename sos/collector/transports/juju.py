# Copyright (c) 2023 Canonical Ltd., Chi Wai Chan <chiwai.chan@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


import subprocess
import os
import shutil

from sos.collector.exceptions import JujuNotInstalledException
from sos.collector.transports import RemoteTransport
from sos.utilities import sos_get_command_output, parse_version


class JujuSSH(RemoteTransport):
    """
    A "transport" that leverages `juju ssh` to perform commands on the remote
    hosts.

    This transport is expected to be used in juju managed environment, and the
    user should have the necessary credential for accessing the controller.
    When using this transport, the --nodes option will be expected to be a
    comma separated machine IDs, **not** IP addr, since `juju ssh` identifies
    the ssh target by machine ID.

    Examples:

    sos collect --nodes 0,1,2 --no-local --transport juju --batch

    """

    name = "juju_ssh"
    default_user = "ubuntu"

    def _check_juju_installed(self):
        cmd = "juju version"
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as err:
            self.log_error("Failed to check `juju` version")
            raise JujuNotInstalledException from err
        return True

    def _chmod(self, fname):
        cmd = f"{self.remote_exec} sudo chmod o+r {fname}"
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError:
            self.log_error(f"Failed to make {fname} world-readable")
            raise
        return True

    def _connect(self, password=""):
        self._connected = self._check_juju_installed()
        return self._connected

    def _disconnect(self):
        return True

    @property
    def connected(self):
        return self._connected

    @property
    def remote_exec(self):
        model, target_option = self.address.split(":")
        model_option = f"-m {model}" if model else ""
        option = f"{model_option} {target_option}"
        return f"juju ssh {option}"

    def _copy_file_to_remote(self, fname, dest):
        model, unit = self.address.split(":")
        model_option = f"-m {model}" if model else ""
        cmd = f"juju scp {model_option} -- {fname} {unit}:{dest}"
        res = sos_get_command_output(cmd, timeout=15)
        return res["status"] == 0

    def _get_juju_version(self):
        """Grab the version of juju"""
        res = sos_get_command_output("juju version")
        return res['output'].split("-", maxsplit=1)[0]

    def _retrieve_file(self, fname, dest):
        self._chmod(fname)  # juju scp needs the archive to be world-readable
        model, unit = self.address.split(":")
        model_option = f"-m {model}" if model else ""

        if parse_version(self._get_juju_version()) >= parse_version("3"):
            # From juju 3.0 onwards the juju client is a strictly confined
            # snap. Strict confinement prevents the snap from writing to
            # arbitrary paths on the host (such as sos' tmpdir under /tmp or
            # the snap's own private tmp namespace). It can, however, write
            # into the invoking user's $HOME thanks to the 'home' snap
            # interface. So we scp the file into a staging directory under
            # $HOME and then move it to the requested destination ourselves.
            #
            # This avoids reaching into the snap's private confinement dir
            # (/tmp/snap-private-tmp/...) and removes the previous requirement
            # of running sos collect as root/with sudo for juju.
            staging_dir = os.path.join(
                os.path.expanduser("~"), ".cache", "sos-collect-juju"
            )
            os.makedirs(staging_dir, exist_ok=True)
            staged_file = os.path.join(staging_dir, os.path.basename(fname))

            cmd = (
                f"juju scp {model_option} -- -r "
                f"{unit}:{fname} {staging_dir}"
            )
            res = sos_get_command_output(cmd)
            if res["status"] == 0:
                shutil.move(staged_file, dest)
        else:
            cmd = f"juju scp {model_option} -- -r {unit}:{fname} {dest}"
            res = sos_get_command_output(cmd)
        return res["status"] == 0


# vim: set et ts=4 sw=4 :
