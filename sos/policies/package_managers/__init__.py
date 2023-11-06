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

from sos.utilities import sos_get_command_output


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
                       sos collect), use this to execute commands
    :vartype remote_exec: ``SoSTransport.run_command()``
    """

    query_command = None
    verify_command = None
    verify_filter = None
    files_command = None
    query_path_command = None
    chroot = None
    files = None

    def __init__(self, chroot=None, remote_exec=None):
        self._packages = {}
        self.files = []
        self.remote_exec = remote_exec

        if chroot:
            self.chroot = chroot

    @property
    def packages(self):
        if not self._packages:
            self._generate_pkg_list()
        return self._packages

    @property
    def manager_name(self):
        return self.__class__.__name__.lower().split('package')[0]

    def exec_cmd(self, command, timeout=30, need_root=False, env=None,
                 use_shell=False, chroot=None):
        """
        Runs a package manager command, either via sos_get_command_output() if
        local, or via a SoSTransport's run_command() if this needs to be run
        remotely, as in the case of remote nodes for use during `sos collect`.

        :param command:     The command to execute
        :type command:      ``str``

        :param timeout:     Timeout for command to run, in seconds
        :type timeout:      ``int``

        :param need_root:   Does the command require root privileges?
        :type need_root:    ``bool``

        :param env:         Environment variables to set
        :type env:          ``dict`` with keys being env vars to define

        :param use_shell:   If running remotely, does the command require
                            obtaining a shell?
        :type use_shell:      ``bool``

        :param chroot:      If necessary, chroot command execution to here
        :type chroot:       ``None`` or ``str``

        :returns:   The output of the command
        :rtype:     ``str``
        """
        if self.remote_exec:
            ret = self.remote_exec(command, timeout, need_root, env, use_shell)
        else:
            ret = sos_get_command_output(command, timeout, chroot=chroot,
                                         env=env)
        if ret['status'] == 0:
            return ret['output']
        # In the case of package managers, we don't want to potentially iterate
        # over stderr, so prevent the package methods from doing anything at
        # all by returning nothing.
        return ''

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

    def _parse_pkg_list(self, pkg_list):
        """
        Using the output of `query_command`, build the _packages dict.

        This should be overridden by distinct package managers and be a
        generator for _generate_pkg_list which will insert the packages into
        the _packages dict.

        This method should yield a tuple of name, version, release for each
        package parsed. If the package manager or distribution does not use a
        release field, set it to None.

        :param pkg_list: The output of the result of `query_command`
        :type pkg_list:  ``str``
        """
        raise NotImplementedError

    def _generate_pkg_list(self):
        """Generates a dictionary of packages for internal use by the package
        manager in the format::

            {'package_name': {'name': 'package_name',
                              'version': 'major.minor.version',
                              'release': 'package release' or None,
                              'pkg_manager': 'package manager name'}}

        """
        if self.query_command:
            cmd = self.query_command
            pkg_list = self.exec_cmd(cmd, timeout=30, chroot=self.chroot)

            for pkg in self._parse_pkg_list(pkg_list):
                self._packages[pkg[0]] = {
                    'name': pkg[0],
                    'version': pkg[1].split('.'),
                    'release': pkg[2],
                    'pkg_manager': self.manager_name
                }

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

    def all_files(self):
        """
        Get a list of files known by the package manager

        :returns: All files known by the package manager
        :rtype: ``list``
        """
        if self.files_command and not self.files:
            cmd = self.files_command
            files = self.exec_cmd(cmd, timeout=180, chroot=self.chroot)
            self.files = files.splitlines()
        return self.files

    def pkg_by_path(self, path):
        """Given a path, return the package that owns that path.

        :param path:    The filepath to check for package ownership
        :type path:     ``str``

        :returns:       The package name or 'unknown'
        :rtype:         ``str``
        """
        if not self.query_path_command:
            return 'unknown'
        try:
            cmd = f"{self.query_path_command} {path}"
            pkg = self.exec_cmd(cmd, timeout=5, chroot=self.chroot)
            return pkg.splitlines() or 'unknown'
        except Exception:
            return 'unknown'

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


class MultiPackageManager(PackageManager):
    """
    This class is used to leverage multiple individual package managers as a
    single entity on systems that support multiple concurrent package managers.

    Policies that use this approach will need to specify a primary package
    manager, and at least one fallback manager. When queries are sent to this
    manager, the primary child manager is checked first. If there is a valid,
    not None, response (e.g. a given package is installed) then that response
    is used. However, if the response is empty or None, the fallback managers
    are then queried in the order they were passed to MultiPackageManager
    during initialization.

    :param primary: The primary package manager to rely on
    :type primary:  A subclass of `PackageManager`

    :param fallbacks: A list of package managers to use if the primary does not
                      provide a response
    :type fallbacks: ``list`` of `PackageManager` subclasses
    """

    def __init__(self, primary, fallbacks, chroot=None, remote_exec=None):
        super(MultiPackageManager, self).__init__(chroot=chroot,
                                                  remote_exec=remote_exec)

        if not issubclass(primary, PackageManager):
            raise Exception(
                f"Primary package manager must be PackageManager subclass, not"
                f" {primary.__class__}"
            )

        if not isinstance(fallbacks, list):
            raise Exception('Fallbacks must be specified in a list')

        for pm in fallbacks:
            if not issubclass(pm, PackageManager):
                raise Exception(
                    f"Fallback package managers must be PackageManager "
                    f"subclass, not {pm.__class__}"
                )

        self.primary = primary(chroot=chroot, remote_exec=remote_exec)
        self.fallbacks = [
            pm(chroot=chroot, remote_exec=remote_exec) for pm in fallbacks
        ]

        if not self.fallbacks:
            raise Exception(
                'Must define at least one fallback package manager'
            )

        self._managers = [self.primary]
        self._managers.extend(self.fallbacks)

    def all_files(self):
        if not self.files:
            for pm in self._managers:
                self.files.extend(pm.all_files())
        return self.files

    def _generate_pkg_list(self):
        self._packages.update(self.primary.packages)
        for pm in self.fallbacks:
            _pkgs = pm.packages
            for pkg in _pkgs.keys():
                if pkg not in self._packages:
                    self._packages[pkg] = _pkgs[pkg]

    def _pm_wrapper(self, method):
        """
        This wrapper method is used to provide implicit iteration through the
        primary and any defined fallback managers that are set for a given
        instance of MultiPackageManager.

        Important note: we pass the _name_ of the method to run here as a
        string, and not any actual method as we rely on iteratively looking up
        the actual method in each package manager.

        :param method: The name of the method we're wrapping for the purpose of
                       iterating through defined package managers
        :type method:  ``str``
        """
        def pkg_func(*args, **kwargs):
            ret = None
            for pm in self._managers:
                if not ret or ret == 'unknown':
                    _wrapped_func = getattr(pm, method)
                    ret = _wrapped_func(*args, **kwargs)
            return ret
        return pkg_func

    def __getattribute__(self, item):
        # if the attr is callable, then we need to iterate over our child
        # managers until we get a response, unless it is _generate_pkg_list in
        # which case we only want to use the one actually defined here, or
        # _pm_wrapper, which we need to avoid this override for to not hit
        # recursion hell.
        if item in ['_generate_pkg_list', '_pm_wrapper', 'all_files']:
            return super().__getattribute__(item)
        attr = super().__getattribute__(item)
        if hasattr(attr, '__call__'):
            return self._pm_wrapper(item)
        return attr

# vim: set et ts=4 sw=4 :
