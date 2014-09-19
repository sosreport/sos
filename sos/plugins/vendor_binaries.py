# Copyright 2014 Red Hat Inc.
# Navid Shaikh <nshaikh@redhat.com>
# Shreyank Gupta <sgupta@redhat.com>
# Poornima M. Kshirsagar <pkshiras@redhat.com>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin
from subprocess import Popen, PIPE
import os


def binaries_directories():
    """
    Return all directories path where binaries present
    """
    dirs = ["/bin/",
            "/usr/bin/",
            "/usr/local/bin/",
            "/sbin/",
            "/usr/sbin/",
            "/usr/local/sbin/",
            "/lib/",
            "/lib64/",
            "/usr/lib/",
            "/usr/lib64/",
            "/usr/local/lib/",
            "/usr/local/lib64",
            "/usr/libexec/",
            "/usr/local/libexec/",
            "/opt/",
            "/usr/opt/",
            "/usr/local/opt/",
            ]
    # extend with the paths in the PATH variable
    dirs.extend(os.environ['PATH'].split(":"))
    if 'LD_LIBRARY_PATH' in os.environ:
        # also include user-defined LD Paths
        dirs.extend(os.environ['LD_LIBRARY_PATH'].split(":"))

    return list(set(dirs))


def get_binaries_inside_directory(directory):
    """
    Get all binaries present inside given directory,
    find all binaries present in subdirectories as well.
    """
    files = [[os.path.join(dirpath, fn) for fn in filenames]
             for dirpath, dirname, filenames in
             os.walk(directory, topdown=False)]
    return [f for sub in files for f in sub]


def match_bin_with_pkg(binary):
    """
    Match given binary to its RPM package
    """
    cmd = ["/bin/rpm", "-qf", binary]
    pkgs = Popen(cmd, stdout=PIPE).stdout.read().strip()
    if ' ' in pkgs:
        return None
    else:
        return pkgs.split('\n')


def get_vendor_binaries():
    """
    Get all binaries which don't come from an installed RPM
    """
    vendor_binaries = []
    bin_dirs = binaries_directories()
    for directory in bin_dirs:
        binaries = get_binaries_inside_directory(directory)
        for binary in binaries:
            # is it a link?
            if os.path.islink(binary):
                binary = os.path.realpath(binary)

            pkgs = []
            if os.path.exists(binary):
                pkgs = match_bin_with_pkg(binary)
            if not pkgs:
                vendor_binaries.append(binary)
    return list(set(vendor_binaries))


class VendorBinaries(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Find non rpm packages and binaries present on system
    """

    plugin_name = 'vendor_binaries'

    def setup(self):
        bins = get_vendor_binaries()
        self.add_string_as_file("\n".join(bins), "vendor-binaries.txt")
