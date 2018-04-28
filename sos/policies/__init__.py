from __future__ import with_statement

import os
import re
import platform
import time
import json
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
from sos import SoSOptions, _arg_names
from textwrap import fill
from six import print_
from six.moves import input

PRESETS_PATH = "/var/lib/sos/presets"


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
    files = None

    def __init__(self, chroot=None, query_command=None,
                 verify_command=None, verify_filter=None,
                 files_command=None):
        self.packages = {}
        self.files = []

        self.query_command = query_command if query_command else None
        self.verify_command = verify_command if verify_command else None
        self.verify_filter = verify_filter if verify_filter else None
        self.files_command = files_command if files_command else None

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

    def all_files(self):
        """
        Returns a list of files known by the package manager
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


#: Constants for on-disk preset fields
DESC = "desc"
NOTE = "note"
OPTS = "args"


class PresetDefaults(object):
    """Preset command line defaults.
    """
    #: Preset name, used for selection
    name = None
    #: Human readable preset description
    desc = None
    #: Notes on preset behaviour
    note = None
    #: Options set for this preset
    opts = SoSOptions()

    #: ``True`` if this preset if built-in or ``False`` otherwise.
    builtin = True

    def __str__(self):
        """Return a human readable string representation of this
            ``PresetDefaults`` object.
        """
        return ("name=%s desc=%s note=%s opts=(%s)" %
                (self.name, self.desc, self.note, str(self.opts)))

    def __repr__(self):
        """Return a machine readable string representation of this
            ``PresetDefaults`` object.
        """
        return ("PresetDefaults(name='%s' desc='%s' note='%s' opts=(%s)" %
                (self.name, self.desc, self.note, repr(self.opts)))

    def __init__(self, name="", desc="", note=None, opts=SoSOptions()):
        """Initialise a new ``PresetDefaults`` object with the specified
            arguments.

            :param name: The name of the new preset
            :param desc: A description for the new preset
            :param note: Note for the new preset
            :param opts: Options set for the new preset
            :returns: The newly initialised ``PresetDefaults``
        """
        self.name = name
        self.desc = desc
        self.note = note
        self.opts = opts

    def write(self, presets_path):
        """Write this preset to disk in JSON notation.

            :param presets_path: the directory where the preset will be
                                 written.
        """
        if self.builtin:
            raise TypeError("Cannot write built-in preset")

        # Make dictionaries of PresetDefaults values
        odict = self.opts.dict()
        pdict = {self.name: {DESC: self.desc, NOTE: self.note, OPTS: odict}}

        with open(os.path.join(presets_path, self.name), "w") as pfile:
            json.dump(pdict, pfile)

    def delete(self, presets_path):
        os.unlink(os.path.join(presets_path, self.name))


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
    presets = {"": PresetDefaults()}
    presets_path = PRESETS_PATH
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

    # for some specific binaries like "xz", we need to determine package
    # providing it; that is policy specific. By default return the binary
    # name itself until particular policy overwrites it
    def _get_pkg_name_for_binary(self, binary):
        return binary

    def get_cmd_for_compress_method(self, method, threads):
        cmd = method
        # use fast compression if using xz or bz2
        if cmd != "gzip":
            cmd = "%s -2" % cmd
        # determine number of threads to use for compressing - applicable
        # only for xz and of version 5.2 or higher
        if cmd.startswith("xz"):
            try:
                xz_package = self._get_pkg_name_for_binary(method)
                xz_version = self.package_manager\
                                 .all_pkgs()[xz_package]["version"]
            except Exception as e:
                xz_version = [0]  # deal like xz version is really old
            if xz_version >= [u'5', u'2']:
                cmd = "%s -T%d" % (cmd, threads)
        return cmd

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

    def register_presets(self, presets, replace=False):
        """Add new presets to this policy object.

            Merges the presets dictionary ``presets`` into this ``Policy``
            object, or replaces the current presets if ``replace`` is
            ``True``.

            ``presets`` should be a dictionary mapping ``str`` preset names
            to ``<class PresetDefaults>`` objects specifying the command
            line defaults.

            :param presets: dictionary of presets to add or replace
            :param replace: replace presets rather than merge new presets.
        """
        if replace:
            self.presets = {}
        self.presets.update(presets)

    def find_preset(self, preset):
        """Find a preset profile matching the specified preset string.

            :param preset: a string containing a preset profile name.
            :returns: a matching PresetProfile.
        """
        # FIXME: allow fuzzy matching?
        for match in self.presets.keys():
            if match == preset:
                return self.presets[match]

        return None

    def probe_preset(self):
        """Return a ``PresetDefaults`` object matching the runing host.

            Stub method to be implemented by derived policy classes.

            :returns: a ``PresetDefaults`` object.
        """
        return self.presets[""]

    def load_presets(self, presets_path=None):
        """Load presets from disk.

            Read JSON formatted preset data from the specified path,
            or the default location at ``/var/lib/sos/presets``.

            :param presets_path: a directory containing JSON presets.
        """
        presets_path = presets_path or self.presets_path
        if not os.path.exists(presets_path):
            return
        for preset_path in os.listdir(presets_path):
            preset_path = os.path.join(presets_path, preset_path)

            try:
                preset_data = json.load(open(preset_path))
            except ValueError:
                continue

            for preset in preset_data.keys():
                pd = PresetDefaults(preset, opts=SoSOptions())
                data = preset_data[preset]
                pd.desc = data[DESC] if DESC in data else ""
                pd.note = data[NOTE] if NOTE in data else ""

                if OPTS in data:
                    for arg in _arg_names:
                        if arg in data[OPTS]:
                            setattr(pd.opts, arg, data[OPTS][arg])
                pd.builtin = False
                self.presets[preset] = pd

    def add_preset(self, name=None, desc=None, note=None, opts=SoSOptions()):
        """Add a new on-disk preset and write it to the configured
            presets path.

            :param preset: the new PresetDefaults to add
        """
        presets_path = self.presets_path

        if not name:
            raise ValueError("Preset name cannot be empty")

        if name in self.presets.keys():
            raise ValueError("A preset with name '%s' already exists" % name)

        preset = PresetDefaults(name=name, desc=desc, note=note, opts=opts)
        preset.builtin = False
        self.presets[preset.name] = preset
        preset.write(presets_path)

    def del_preset(self, name=""):
        if not name or name not in self.presets.keys():
            raise ValueError("Unknown profile: '%s'" % name)

        preset = self.presets[name]

        if preset.builtin:
            raise ValueError("Cannot delete built-in preset '%s'" %
                             preset.name)

        preset.delete(self.presets_path)
        self.presets.pop(name)


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
        except IOError:
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
        except (IndexError, IOError):
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
