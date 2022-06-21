# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re
import fnmatch

from sos.utilities import shell_out
from pipes import quote


class PackageManager():
    """Encapsulates a package manager. If you provide a query_command to the
    constructor it should print each package on the system in the following
    format::

        package name|package.version

    You may also subclass this class and provide a _generate_pkg_list method to
    build the list of packages and versions.

    :cvar query_command: The command to use for querying packages
    :vartype query_command: ``str`` or ``None``

    :cvar verify_command: The command to use for verifying packages
    :vartype verify_command: ``str`` or ``None``

    :cvar verify_filter: Optional filter to use for controlling package
                         verification
    :vartype verify_filter: ``str or ``None``

    :cvar files_command: The command to use for getting file lists for packages
    :vartype files_command: ``str`` or ``None``

    :cvar chroot: Perform a chroot when executing `files_command`
    :vartype chroot: ``bool``

    :cvar remote_exec: If package manager is on a remote system (e.g. for
                       sos collect), prepend this SSH command to run remotely
    :vartype remote_exec: ``str`` or ``None``
    """

    query_command = None
    verify_command = None
    verify_filter = None
    files_command = None
    chroot = None
    files = None

    def __init__(self, chroot=None, query_command=None,
                 verify_command=None, verify_filter=None,
                 files_command=None, remote_exec=None):
        self._packages = {}
        self.files = []

        self.query_command = query_command or self.query_command
        self.verify_command = verify_command or self.verify_command
        self.verify_filter = verify_filter or self.verify_filter
        self.files_command = files_command or self.files_command

        # if needed, append the remote command to these so that this returns
        # the remote package details, not local
        if remote_exec:
            for cmd in ['query_command', 'verify_command', 'files_command']:
                if getattr(self, cmd) is not None:
                    _cmd = getattr(self, cmd)
                    setattr(self, cmd, "%s %s" % (remote_exec, quote(_cmd)))

        if chroot:
            self.chroot = chroot

    @property
    def packages(self):
        if not self._packages:
            self._generate_pkg_list()
        return self._packages

    def all_pkgs_by_name(self, name):
        """
        Get a list of packages that match name.

        :param name: The name of the package
        :type name: ``str``

        :returns: List of all packages matching `name`
        :rtype: ``list``
        """
        return fnmatch.filter(self.packages.keys(), name)

    def all_pkgs_by_name_regex(self, regex_name, flags=0):
        """
        Get a list of packages that match regex_name.

        :param regex_name: The regex to use for matching package names against
        :type regex_name: ``str``

        :param flags: Flags for the `re` module when matching `regex_name`

        :returns: All packages matching `regex_name`
        :rtype: ``list``
        """
        reg = re.compile(regex_name, flags)
        return [pkg for pkg in self.packages.keys() if reg.match(pkg)]

    def pkg_by_name(self, name):
        """
        Get a single package that matches name.

        :param name: The name of the package
        :type name: ``str``

        :returns: The first package that matches `name`
        :rtype: ``str``
        """
        try:
            return self.packages[name]
        except Exception:
            return None

    def _generate_pkg_list(self):
        """Generates a dictionary of packages for internal use by the package
        manager in the format::

            {'package_name': {'name': 'package_name',
                              'version': 'major.minor.version'}}

        """
        if self.query_command:
            cmd = self.query_command
            pkg_list = shell_out(
                cmd, timeout=0, chroot=self.chroot
            ).splitlines()

            for pkg in pkg_list:
                if '|' not in pkg:
                    continue
                elif pkg.count("|") == 1:
                    name, version = pkg.split("|")
                    release = None
                elif pkg.count("|") == 2:
                    name, version, release = pkg.split("|")
                self._packages[name] = {
                    'name': name,
                    'version': version.split(".")
                }
                release = release if release else None
                self._packages[name]['release'] = release

    def pkg_version(self, pkg):
        """Returns the entry in self.packages for pkg if it exists

        :param pkg: The name of the package
        :type pkg: ``str``

        :returns: Package name and version, if package exists
        :rtype: ``dict`` if found, else ``None``
        """
        if pkg in self.packages:
            return self.packages[pkg]
        return None

    def pkg_nvra(self, pkg):
        """Get the name, version, release, and architecture for a package

        :param pkg: The name of the package
        :type pkg: ``str``

        :returns: name, version, release, and arch of the package
        :rtype: ``tuple``
        """
        fields = pkg.split("-")
        version, release, arch = fields[-3:]
        name = "-".join(fields[:-3])
        return (name, version, release, arch)

    def all_files(self):
        """
        Get a list of files known by the package manager

        :returns: All files known by the package manager
        :rtype: ``list``
        """
        if self.files_command and not self.files:
            cmd = self.files_command
            files = shell_out(cmd, timeout=0, chroot=self.chroot)
            self.files = files.splitlines()
        return self.files

    def build_verify_command(self, packages):
        """build_verify_command(self, packages) -> str
            Generate a command to verify the list of packages given
            in ``packages`` using the native package manager's
            verification tool.

            The command to be executed is returned as a string that
            may be passed to a command execution routine (for e.g.
            ``sos_get_command_output()``.

            :param packages: a string, or a list of strings giving
                             package names to be verified.
            :returns: a string containing an executable command
                      that will perform verification of the given
                      packages.
            :rtype: str or ``NoneType``
        """
        if not self.verify_command:
            return None

        # The re.match(pkg) used by all_pkgs_by_name_regex() may return
        # an empty list (`[[]]`) when no package matches: avoid building
        # an rpm -V command line with the empty string as the package
        # list in this case.
        by_regex = self.all_pkgs_by_name_regex
        verify_list = filter(None, map(by_regex, packages))

        # No packages after regex match?
        if not verify_list:
            return None

        verify_packages = ""
        for package_list in verify_list:
            for package in package_list:
                if any([f in package for f in self.verify_filter]):
                    continue
                if len(verify_packages):
                    verify_packages += " "
                verify_packages += package
        return self.verify_command + " " + verify_packages


# vim: set et ts=4 sw=4 :
