from __future__ import with_statement

import os
import re
import platform
import time
import fnmatch
import tempfile
import random
import string
from os import environ

from sos.utilities import (ImporterHelper,
                           import_module,
                           shell_out)
from sos.plugins import IndependentPlugin, ExperimentalPlugin
from sos import _sos as _
from textwrap import fill
from six import print_
from six.moves import input


def import_policy(name):
    policy_fqname = "sos.policies.%s" % name
    try:
        return import_module(policy_fqname, Policy)
    except ImportError:
        return None


def load(cache={}, sysroot=None):
    if 'policy' in cache:
        return cache.get('policy')

    import sos.policies
    helper = ImporterHelper(sos.policies)
    for module in helper.get_modules():
        for policy in import_policy(module):
            if policy.check():
                cache['policy'] = policy(sysroot=sysroot)

    if 'policy' not in cache:
        cache['policy'] = GenericPolicy()

    return cache['policy']


class PackageManager(object):
    """Encapsulates a package manager. If you provide a query_command to the
    constructor it should print each package on the system in the following
    format::

        package name|package.version

    You may also subclass this class and provide a get_pkg_list method to
    build the list of packages and versions.
    """

    query_command = None
    verify_command = None
    verify_filter = None
    chroot = None

    def __init__(self, chroot=None, query_command=None,
                 verify_command=None, verify_filter=None):
        self.packages = {}

        self.query_command = query_command if query_command else None
        self.verify_command = verify_command if verify_command else None
        self.verify_filter = verify_filter if verify_filter else None

        if chroot:
            self.chroot = chroot

    def all_pkgs_by_name(self, name):
        """
        Return a list of packages that match name.
        """
        return fnmatch.filter(self.all_pkgs().keys(), name)

    def all_pkgs_by_name_regex(self, regex_name, flags=0):
        """
        Return a list of packages that match regex_name.
        """
        reg = re.compile(regex_name, flags)
        return [pkg for pkg in self.all_pkgs().keys() if reg.match(pkg)]

    def pkg_by_name(self, name):
        """
        Return a single package that matches name.
        """
        pkgmatches = self.all_pkgs_by_name(name)
        if (len(pkgmatches) != 0):
            return self.all_pkgs_by_name(name)[-1]
        else:
            return None

    def get_pkg_list(self):
        """Returns a dictionary of packages in the following
        format::

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
                self.packages[name] = {
                    'name': name,
                    'version': version.split(".")
                }
                release = release if release else None
                self.packages[name]['release'] = release

        return self.packages

    def all_pkgs(self):
        """
        Return a list of all packages.
        """
        if not self.packages:
            self.packages = self.get_pkg_list()
        return self.packages

    def pkg_nvra(self, pkg):
        fields = pkg.split("-")
        version, release, arch = fields[-3:]
        name = "-".join(fields[:-3])
        return (name, version, release, arch)

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
            :returntype: str or ``NoneType``
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


class Policy(object):

    msg = _("""\
This command will collect system configuration and diagnostic information \
from this %(distro)s system. An archive containing the collected information \
will be generated in %(tmpdir)s.

For more information on %(vendor)s visit:

  %(vendor_url)s

The generated archive may contain data considered sensitive and its content \
should be reviewed by the originating organization before being passed to \
any third party.

No changes will be made to system configuration.
%(vendor_text)s
""")

    distro = "Unknown"
    vendor = "Unknown"
    vendor_url = "http://www.example.com/"
    vendor_text = ""
    PATH = ""
    default_scl_prefix = ""
    name_pattern = 'legacy'

    _in_container = False
    _host_sysroot = '/'

    def __init__(self, sysroot=None):
        """Subclasses that choose to override this initializer should call
        super() to ensure that they get the required platform bits attached.
        super(SubClass, self).__init__(). Policies that require runtime
        tests to construct PATH must call self.set_exec_path() after
        modifying PATH in their own initializer."""
        self._parse_uname()
        self.case_id = None
        self.package_manager = PackageManager()
        self._valid_subclasses = []
        self.set_exec_path()
        self._host_sysroot = sysroot

    def get_valid_subclasses(self):
        return [IndependentPlugin] + self._valid_subclasses

    def set_valid_subclasses(self, subclasses):
        self._valid_subclasses = subclasses

    def del_valid_subclasses(self):
        del self._valid_subclasses

    valid_subclasses = property(get_valid_subclasses,
                                set_valid_subclasses,
                                del_valid_subclasses,
                                "list of subclasses that this policy can "
                                "process")

    def check(self):
        """
        This function is responsible for determining if the underlying system
        is supported by this policy.
        """
        return False

    def in_container(self):
        """ Returns True if sos is running inside a container environment.
        """
        return self._in_container

    def host_sysroot(self):
        return self._host_sysroot

    def dist_version(self):
        """
        Return the OS version
        """
        pass

    def get_preferred_archive(self):
        """
        Return the class object of the prefered archive format for this
        platform
        """
        from sos.archive import TarFileArchive
        return TarFileArchive

    def get_archive_name(self):
        """
        This function should return the filename of the archive without the
        extension.

        This uses the policy's name_pattern attribute to determine the name.
        There are two pre-defined naming patterns - 'legacy' and 'friendly'
        that give names like the following:

        legacy - 'sosreport-tux.123456-20171224185433'
        friendly - 'sosreport-tux-mylabel-123456-2017-12-24-ezcfcop.tar.xz'

        A custom name_pattern can be used by a policy provided that it
        defines name_pattern using a format() style string substitution.

        Usable substitutions are:

            name  - the short hostname of the system
            label - the label given by --label
            case  - the case id given by --case-id or --ticker-number
            rand  - a random string of 7 alpha characters

        Note that if a datestamp is needed, the substring should be set
        in the name_pattern in the format accepted by strftime().

        """
        name = self.get_local_name().split('.')[0]
        case = self.case_id
        label = self.commons['cmdlineopts'].label
        rand = ''.join(random.choice(string.ascii_lowercase) for x in range(7))

        if self.name_pattern == 'legacy':
            nstr = "sosreport-{name}{case}{date}"
            case = '.' + case if case else ''
            date = '-%Y%m%d%H%M%S'
        elif self.name_pattern == 'friendly':
            nstr = "sosreport-{name}{label}{case}{date}-{rand}"
            case = '-' + case if case else ''
            label = '-' + label if label else ''
            date = '-%Y-%m-%d'
        else:
            nstr = self.name_pattern

        nstr = nstr.format(
            name=name,
            label=label,
            case=case,
            date=date,
            rand=rand
        )
        return time.strftime(nstr)

    def get_tmp_dir(self, opt_tmp_dir):
        if not opt_tmp_dir:
            return tempfile.gettempdir()
        return opt_tmp_dir

    def get_default_scl_prefix(self):
        return self.default_scl_prefix

    def match_plugin(self, plugin_classes):
        if len(plugin_classes) > 1:
            for p in plugin_classes:
                # Give preference to the first listed tagging class
                # so that e.g. UbuntuPlugin is chosen over DebianPlugin
                # on an Ubuntu installation.
                if issubclass(p, self.valid_subclasses[0]):
                    return p
        return plugin_classes[0]

    def validate_plugin(self, plugin_class, experimental=False):
        """
        Verifies that the plugin_class should execute under this policy
        """
        valid_subclasses = [IndependentPlugin] + self.valid_subclasses
        if experimental:
            valid_subclasses += [ExperimentalPlugin]
        return any(issubclass(plugin_class, class_) for
                   class_ in valid_subclasses)

    def pre_work(self):
        """
        This function is called prior to collection.
        """
        pass

    def post_work(self):
        """
        This function is called after the sosreport has been generated.
        """
        pass

    def pkg_by_name(self, pkg):
        return self.package_manager.pkg_by_name(pkg)

    def _parse_uname(self):
        (system, node, release,
         version, machine, processor) = platform.uname()
        self.system = system
        self.hostname = node
        self.release = release
        self.smp = version.split()[1] == "SMP"
        self.machine = machine

    def set_commons(self, commons):
        self.commons = commons

    def _set_PATH(self, path):
        environ['PATH'] = path

    def set_exec_path(self):
        self._set_PATH(self.PATH)

    def is_root(self):
        """This method should return true if the user calling the script is
        considered to be a superuser"""
        return (os.getuid() == 0)

    def get_preferred_hash_name(self):
        """Returns the string name of the hashlib-supported checksum algorithm
        to use"""
        return "md5"

    def display_results(self, archive, directory, checksum):
        # Display results is called from the tail of SoSReport.final_work()
        #
        # Logging is already shutdown and all terminal output must use the
        # print() call.

        # make sure a report exists
        if not archive and not directory:
            return False

        self._print()

        if archive:
            self._print(_("Your sosreport has been generated and saved "
                        "in:\n  %s") % archive)
        else:
            self._print(_("sosreport build tree is located at : %s" %
                        directory))

        self._print()
        if checksum:
            self._print(_("The checksum is: ") + checksum)
            self._print()
            self._print(_("Please send this file to your support "
                        "representative."))
        self._print()

    def _print(self, msg=None):
        """A wrapper around print that only prints if we are not running in
        quiet mode"""
        if not self.commons['cmdlineopts'].quiet:
            if msg:
                print_(msg)
            else:
                print_()

    def get_msg(self):
        """This method is used to prepare the preamble text to display to
        the user in non-batch mode. If your policy sets self.distro that
        text will be substituted accordingly. You can also override this
        method to do something more complicated."""
        width = 72
        _msg = self.msg % {'distro': self.distro, 'vendor': self.vendor,
                           'vendor_url': self.vendor_url,
                           'vendor_text': self.vendor_text,
                           'tmpdir': self.commons['tmpdir']}
        _fmt = ""
        for line in _msg.splitlines():
            _fmt = _fmt + fill(line, width, replace_whitespace=False) + '\n'
        return _fmt


class GenericPolicy(Policy):
    """This Policy will be returned if no other policy can be loaded. This
    should allow for IndependentPlugins to be executed on any system"""

    def get_msg(self):
        return self.msg % {'distro': self.system}


class LinuxPolicy(Policy):
    """This policy is meant to be an abc class that provides common
    implementations used in Linux distros"""

    distro = "Linux"
    vendor = "None"
    PATH = "/bin:/sbin:/usr/bin:/usr/sbin"

    _preferred_hash_name = None

    def __init__(self, sysroot=None):
        super(LinuxPolicy, self).__init__(sysroot=sysroot)

    def get_preferred_hash_name(self):

        if self._preferred_hash_name:
            return self._preferred_hash_name

        checksum = "md5"
        try:
            fp = open("/proc/sys/crypto/fips_enabled", "r")
        except:
            self._preferred_hash_name = checksum
            return checksum

        fips_enabled = fp.read()
        if fips_enabled.find("1") >= 0:
            checksum = "sha256"
        fp.close()
        self._preferred_hash_name = checksum
        return checksum

    def default_runlevel(self):
        try:
            with open("/etc/inittab") as fp:
                pattern = r"id:(\d{1}):initdefault:"
                text = fp.read()
                return int(re.findall(pattern, text)[0])
        except:
            return 3

    def kernel_version(self):
        return self.release

    def host_name(self):
        return self.hostname

    def is_kernel_smp(self):
        return self.smp

    def get_arch(self):
        return self.machine

    def get_local_name(self):
        """Returns the name usd in the pre_work step"""
        return self.host_name()

    def sanitize_case_id(self, case_id):
        return re.sub(r"[^-a-z,A-Z.0-9]", "", case_id)

    def lsmod(self):
        """Return a list of kernel module names as strings.
        """
        lines = shell_out("lsmod", timeout=0).splitlines()
        return [line.split()[0].strip() for line in lines]

    def pre_work(self):
        # this method will be called before the gathering begins

        cmdline_opts = self.commons['cmdlineopts']
        caseid = cmdline_opts.case_id if cmdline_opts.case_id else ""

        if not cmdline_opts.batch and not \
                cmdline_opts.quiet:
            try:
                self.case_id = input(_("Please enter the case id "
                                       "that you are generating this "
                                       "report for [%s]: ") % caseid)
                self._print()
            except KeyboardInterrupt:
                self._print()
                raise

        if cmdline_opts.case_id:
            self.case_id = cmdline_opts.case_id

        if self.case_id:
            self.case_id = self.sanitize_case_id(self.case_id)

        return


# vim: set et ts=4 sw=4 :
