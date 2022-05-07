# Copyright (C) 2006 Steve Conklin <sconklin@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

""" This exports methods available for use by plugins for sos """

from sos.utilities import (sos_get_command_output, import_module, grep,
                           fileobj, tail, is_executable, TIMEOUT_DEFAULT,
                           path_exists, path_isdir, path_isfile, path_islink,
                           listdir, path_join, bold, file_is_binary)

from sos.archive import P_FILE
import os
import glob
import re
import stat
from time import time
import logging
import fnmatch
import errno
import textwrap

from datetime import datetime


def regex_findall(regex, fname):
    """Return a list of all non overlapping matches in the string(s)"""
    try:
        with fileobj(fname) as f:
            return re.findall(regex, f.read(), re.MULTILINE)
    except AttributeError:
        return []


def _mangle_command(command, name_max):
    mangledname = re.sub(r"^/(usr/|)(bin|sbin)/", "", command)
    mangledname = re.sub(r"[^\w\-\.\/]+", "_", mangledname)
    mangledname = re.sub(r"/", ".", mangledname).strip(" ._-")
    mangledname = mangledname[0:name_max]
    return mangledname


def _path_in_path_list(path, path_list):
    return any((p == path or path.startswith(os.path.abspath(p)+os.sep)
                for p in path_list))


def _node_type(st):
    """ return a string indicating the type of special node represented by
    the stat buffer st (block, character, fifo, socket).
    """
    _types = [
        (stat.S_ISBLK, "block device"),
        (stat.S_ISCHR, "character device"),
        (stat.S_ISFIFO, "named pipe"),
        (stat.S_ISSOCK, "socket")
    ]
    for t in _types:
        if t[0](st.st_mode):
            return t[1]


_certmatch = re.compile("-*BEGIN.*?-*END", re.DOTALL)
_cert_replace = "-----SCRUBBED"


class SoSPredicate(object):
    """A class to implement collection predicates.

    A predicate gates the collection of data by an sos plugin. For any
    `add_cmd_output()`, `add_copy_spec()` or `add_journal()` call, the
    passed predicate will be evaulated and collection will proceed if
    the result is `True`, and not otherwise.

    Predicates may be used to control conditional data collection
    without the need for explicit conditional blocks in plugins.

    :param owner:       The ``Plugin`` object creating the predicate
    :type owner:        ``Plugin``

    :param dry_run:     Is sos running in dry_run mode?
    :type dry_run:      ``bool``

    :param kmods:       Kernel module name(s) to check presence of
    :type kmods:        ``list``, or ``str`` of single name

    :param services:    Service name(s) to check if running
    :type services:     ``list``, or ``str`` of single name

    :param packages:    Package name(s) to check presence of
    :type packages:     ``list``, or ``str`` of single name

    :param cmd_outputs: Command to run, with output string to check
    :type cmd_outputs:  ``list`` of ``dict``s, or single ``dict`` taking form
                        {'cmd': <command to run>,
                        'output': <string that output should contain>}
    :param arch:        Architecture(s) that the local system is matched
                        against
    :type arch:         ``list``, or ``str`` of single architecture

    :param required:    For each parameter provided, should the checks
                        require all items, no items, or any items provided
    :type required:     ``dict``, with keys matching parameter names and values
                        being either 'any', 'all', or 'none. Default 'any'.

    """
    #: The plugin that owns this predicate
    _owner = None

    #: Skip all collection?
    dry_run = False

    #: Kernel module enablement list
    kmods = []

    #: Services enablement list
    services = []

    #: Package presence list
    packages = []

    # Command output inclusion pairs {'cmd': 'foo --help', 'output': 'bar'}
    cmd_outputs = []

    #: Allowed architecture(s) of the system
    arch = []

    def __str(self, quote=False, prefix="", suffix=""):
        """Return a string representation of this SoSPredicate with
            optional prefix, suffix and value quoting.
        """
        quotes = '"%s"'
        pstr = "dry_run=%s, " % self.dry_run

        kmods = self.kmods
        kmods = [quotes % k for k in kmods] if quote else kmods
        pstr += "kmods=[%s], " % (",".join(kmods))

        services = self.services
        services = [quotes % s for s in services] if quote else services
        pstr += "services=[%s], " % (",".join(services))

        pkgs = self.packages
        pkgs = [quotes % p for p in pkgs] if quote else pkgs
        pstr += "packages=[%s], " % (",".join(pkgs))

        cmdoutputs = [
            "{ %s: %s, %s: %s }" % (quotes % "cmd",
                                    quotes % cmdoutput['cmd'],
                                    quotes % "output",
                                    quotes % cmdoutput['output'])
            for cmdoutput in self.cmd_outputs
        ]
        pstr += "cmdoutputs=[%s], " % (",".join(cmdoutputs))

        arches = self.arch
        arches = [quotes % a for a in arches] if quote else arches
        pstr += "arches=[%s]" % (",".join(arches))

        return prefix + pstr + suffix

    def __str__(self):
        """Return a string representation of this SoSPredicate.

            "dry_run=False, kmods=[], services=[], cmdoutputs=[]"
        """
        return self.__str()

    def __repr__(self):
        """Return a machine readable string representation of this
            SoSPredicate.

            "SoSPredicate(dry_run=False, kmods=[], services=[], cmdoutputs=[])"
        """
        return self.__str(quote=True, prefix="SoSPredicate(", suffix=")")

    def _check_required_state(self, items, required):
        """Helper to simplify checking the state of the predicate's evaluations
        against the setting of the required state of that evaluation
        """
        if required == 'any':
            return any(items)
        elif required == 'all':
            return all(items)
        elif required == 'none':
            return not any(items)

    def _failed_or_forbidden(self, test, item):
        """Helper to direct failed predicates to provide the proper messaging
        based on the required check type

            :param test:      The type of check we're doing, e.g. kmods, arch
            :param item:      The string of what failed
        """
        _req = self.required[test]
        if _req != 'none':
            self._failed[test].append(item)
        else:
            self._forbidden[test].append(item)

    def _eval_kmods(self):
        if not self.kmods or self._owner.get_option('allow_system_changes'):
            return True

        _kmods = []
        # Are kernel modules loaded?
        for kmod in self.kmods:
            res = self._owner.is_module_loaded(kmod)
            _kmods.append(res)
            if not res:
                self._failed_or_forbidden('kmods', kmod)

        return self._check_required_state(_kmods, self.required['kmods'])

    def _eval_services(self):
        if not self.services:
            return True

        _svcs = []
        for svc in self.services:
            res = self._owner.is_service_running(svc)
            _svcs.append(res)
            if not res:
                self._failed_or_forbidden('services', svc)

        return self._check_required_state(_svcs, self.required['services'])

    def _eval_packages(self):
        if not self.packages:
            return True

        _pkgs = []
        for pkg in self.packages:
            res = self._owner.is_installed(pkg)
            _pkgs.append(res)
            if not res:
                self._failed_or_forbidden('packages', pkg)

        return self._check_required_state(_pkgs, self.required['packages'])

    def _eval_cmd_output(self, cmd_output):
        """Does 'cmd' output contain string 'output'?"""
        if 'cmd' not in cmd_output or 'output' not in cmd_output:
            return False
        result = sos_get_command_output(cmd_output['cmd'])
        if result['status'] != 0:
            return False
        for line in result['output'].splitlines():
            if cmd_output['output'] in line:
                return True
        return False

    def _eval_cmd_outputs(self):
        if not self.cmd_outputs:
            return True

        _cmds = []
        for cmd in self.cmd_outputs:
            res = self._eval_cmd_output(cmd)
            _cmds.append(res)
            if not res:
                self._failed_or_forbidden(
                    'cmd_outputs',
                    "%s: %s" % (cmd['cmd'], cmd['output'])
                )
        return self._check_required_state(_cmds, self.required['cmd_outputs'])

    def _eval_arch(self):
        if not self.arch:
            return True

        # a test for 'all' against arch does not make sense, so only test to
        # see if the system's reported architecture is in the last of 'allowed'
        # arches requested by the predicate
        _arch = self._owner.policy.get_arch()
        regex = '(?:%s)' % '|'.join(self.arch)
        if self.required['arch'] == 'none':
            if re.match(regex, _arch):
                self._forbidden['architecture'].append(_arch)
                return False
            return True
        if re.match(regex, _arch):
            return True
        self._failed['architecture'].append(_arch)
        return False

    def _report_failed(self):
        """Return a string informing user what caused the predicate to fail
        evaluation
        """
        msg = ''
        _substr = "required %s missing: %s."
        for key, val in self._failed.items():
            if not val:
                continue
            val = set(val)
            msg += _substr % (key, ', '.join(v for v in val))
        return msg

    def _report_forbidden(self):
        """Return a string informing the user that a forbidden condition exists
        which caused the predicate to fail
        """
        msg = ''
        _substr = "forbidden %s '%s' found."
        for key, val in self._forbidden.items():
            if not val:
                continue
            val = set(val)
            msg += _substr % (key, ', '.join(v for v in val))
        return msg

    def report_failure(self):
        """Used by `Plugin()` to obtain the error string based on if the reason
        was a failed check or a forbidden check
        """
        msg = [
            self._report_failed(),
            self._report_forbidden(),
            '(dry run)' if self.dry_run else ''
        ]
        return " ".join(msg).lstrip()

    def __bool__(self):
        """Predicate evaluation hook.
        """

        # Null predicate?
        if not any([self.kmods, self.services, self.packages, self.cmd_outputs,
                    self.arch, self.dry_run]):
            return True

        return ((self._eval_kmods() and self._eval_services() and
                 self._eval_packages() and self._eval_cmd_outputs() and
                 self._eval_arch())
                and not self.dry_run)

    def __init__(self, owner, dry_run=False, kmods=[], services=[],
                 packages=[], cmd_outputs=[], arch=[], required={}):
        """Initialise a new SoSPredicate object
        """
        self._owner = owner
        self.kmods = list(kmods)
        self.services = list(services)
        self.packages = list(packages)
        self.arch = list(arch)
        if not isinstance(cmd_outputs, list):
            cmd_outputs = [cmd_outputs]
        self.cmd_outputs = cmd_outputs
        self.dry_run = dry_run | self._owner.commons['cmdlineopts'].dry_run
        self.required = {'kmods': 'any', 'services': 'any', 'packages': 'any',
                         'cmd_outputs': 'any', 'arch': 'any'}
        self.required.update({
            k: v for k, v in required.items() if
            required[k] != self.required[k]
        })
        #: Dict holding failed evaluations
        self._failed = {
            'kmods': [], 'services': [], 'packages': [], 'cmd_outputs': [],
            'architecture': []
        }
        self._forbidden = {
            'kmods': [], 'services': [], 'packages': [], 'cmd_outputs': [],
            'architecture': []
        }


class SoSCommand(object):
    """A class to represent a command to be collected.

    A SoSCommand() object is instantiated for each command handed to an
    _add_cmd_output() call, so that we no longer need to pass around a very
    long tuple to handle the parameters.

    Any option supported by _add_cmd_output() is passed to the SoSCommand
    object and converted to an attribute. SoSCommand.__dict__ is then passed to
    _get_command_output_now() for each command to be collected.
    """

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __str__(self):
        """Return a human readable string representation of this SoSCommand
        """
        return ', '.join("%s=%r" % (param, val) for (param, val) in
                         sorted(self.__dict__.items()))


class PluginOpt():
    """This is used to define options available to plugins. Plugins will need
    to define options alongside their distro-specific classes in order to add
    support for user-controlled changes in Plugin behavior.

    :param name:        The name of the plugin option
    :type name:         ``str``

    :param default:     The default value of the option
    :type default:      Any

    :param desc:        A short description of the effect of the option
    :type desc:         ``str``

    :param long_desc:   A detailed description of the option. Will be used by
                        `sos info`
    :type long_desc:    ``str``

    :param val_type:    The type of object the option accepts for values. If
                        not provided, auto-detect from the type of ``default``
    :type val_type:     A single type or a ``list`` of types
    """

    name = ''
    default = None
    enabled = False
    desc = ''
    long_desc = ''
    value = None
    val_type = [None]
    plugin = ''

    def __init__(self, name='undefined', default=None, desc='', long_desc='',
                 val_type=None):
        self.name = name
        self.default = default
        self.desc = desc
        self.long_desc = long_desc
        self.value = self.default
        if val_type is not None:
            if not isinstance(val_type, list):
                val_type = [val_type]
        else:
            val_type = [default.__class__]
        self.val_type = val_type

    def __str__(self):
        items = [
            'name=%s' % self.name,
            'desc=\'%s\'' % self.desc,
            'value=%s' % self.value,
            'default=%s' % self.default
        ]
        return '(' + ', '.join(items) + ')'

    def __repr__(self):
        return self.__str__()

    def set_value(self, val):
        # 'str' type accepts any value, incl. numbers
        if type('') in self.val_type:
            self.value = str(val)
            return
        if not any([type(val) == _t for _t in self.val_type]):
            valid = []
            for t in self.val_type:
                if t is None:
                    continue
                if t.__name__ == 'bool':
                    valid.append("boolean true/false (on/off, etc)")
                elif t.__name__ == 'str':
                    valid.append("string (no spaces)")
                elif t.__name__ == 'int':
                    valid.append("integer values")
            raise Exception(
                "Plugin option '%s.%s' takes %s, not %s" % (
                    self.plugin, self.name, ', '.join(valid),
                    type(val).__name__
                )
            )
        self.value = val


class Plugin():
    """This is the base class for sosreport plugins. Plugins should subclass
    this and set the class variables where applicable.

    :param commons:     A set of information that is shared internally so that
                        plugins may access the same dataset. This is provided
                        automatically by sos
    :type commons:      ``dict``

    Each `Plugin()` subclass should also subclass at least one tagging class,
    e.g. ``RedHatPlugin``, to support that distribution. If different
    distributions require different collections, each distribution should have
    its own subclass of the Plugin that also subclasses the tagging class for
    their respective distributions.

    :cvar plugin_name:  The name of the plugin, will be returned by `name()`
    :vartype plugin_name: ``str``

    :cvar packages:     Package name(s) that, if installed, enable this plugin
    :vartype packages:  ``tuple``

    :cvar files:        File path(s) that, if present, enable this plugin
    :vartype files:     ``tuple``

    :cvar commands:     Executables that, if present, enable this plugin
    :vartype commands:  ``tuple``

    :cvar kernel_mods:  Kernel module(s) that, if loaded, enable this plugin
    :vartype kernel_mods: ``tuple``

    :cvar services:     Service name(s) that, if running, enable this plugin
    :vartype services:  ``tuple``

    :cvar architectures: Architecture(s) this plugin is enabled for. Defaults
                         to 'none' to enable on all arches.
    :vartype architectures: ``tuple``, or ``None``

    :cvar profiles:     Name(s) of profile(s) this plugin belongs to
    :vartype profiles:  ``tuple``

    :cvar plugin_timeout: Timeout in seconds for this plugin as a whole
    :vartype plugin_timeout: ``int``

    :cvar cmd_timeout:  Timeout in seconds for individual commands
    :vartype cmd_timeout:   ``int``
    """

    plugin_name = None
    packages = ()
    files = ()
    commands = ()
    kernel_mods = ()
    services = ()
    containers = ()
    architectures = None
    archive = None
    profiles = ()
    sysroot = '/'
    plugin_timeout = TIMEOUT_DEFAULT
    cmd_timeout = TIMEOUT_DEFAULT
    _timeout_hit = False
    cmdtags = {}
    filetags = {}
    option_list = []

    # Default predicates
    predicate = None
    cmd_predicate = None

    def __init__(self, commons):

        self.copied_files = []
        self.executed_commands = []
        self._env_vars = set()
        self.alerts = []
        self.custom_text = ""
        self.commons = commons
        self.forbidden_paths = []
        self.copy_paths = set()
        self.container_copy_paths = []
        self.copy_strings = []
        self.collect_cmds = []
        self.options = {}
        self.sysroot = commons['sysroot']
        self.policy = commons['policy']
        self.devices = commons['devices']
        self.manifest = None
        self.skip_files = commons['cmdlineopts'].skip_files
        self.skip_commands = commons['cmdlineopts'].skip_commands
        self.default_environment = {}

        self.soslog = self.commons['soslog'] if 'soslog' in self.commons \
            else logging.getLogger('sos')

        # add the default plugin opts
        self.options.update(self.get_default_plugin_opts())
        for popt in self.options:
            self.options[popt].plugin = self.name()
        for opt in self.option_list:
            opt.plugin = self.name()
            self.options[opt.name] = opt

        # Initialise the default --dry-run predicate
        self.set_predicate(SoSPredicate(self))

    def get_default_plugin_opts(self):
        return {
            'timeout': PluginOpt(
                'timeout', default=-1, val_type=int,
                desc='Timeout in seconds for plugin to finish all collections'
            ),
            'cmd-timeout': PluginOpt(
                'cmd-timeout', default=-1, val_type=int,
                desc='Timeout in seconds for individual commands to finish'
            ),
            'postproc': PluginOpt(
                'postproc', default=True, val_type=bool,
                desc='Enable post-processing of collected data'
            )
        }

    def set_plugin_manifest(self, manifest):
        """Pass in a manifest object to the plugin to write to

        :param manifest: The manifest that the plugin will add metadata to
        :type manifest: ``SoSManifest``
        """
        self.manifest = manifest
        # add these here for organization when they actually get set later
        self.manifest.add_field('start_time', '')
        self.manifest.add_field('end_time', '')
        self.manifest.add_field('run_time', '')
        self.manifest.add_field('setup_start', '')
        self.manifest.add_field('setup_end', '')
        self.manifest.add_field('setup_time', '')
        self.manifest.add_field('timeout', self.timeout)
        self.manifest.add_field('timeout_hit', False)
        self.manifest.add_field('command_timeout', self.cmdtimeout)
        self.manifest.add_list('commands', [])
        self.manifest.add_list('files', [])
        self.manifest.add_field('strings', {})
        self.manifest.add_field('containers', {})

    def set_default_cmd_environment(self, env_vars):
        """
        Specify a collection of environment variables that should always be
        passed to commands being executed by this plugin.

        :param env_vars:    The environment variables and their values to set
        :type env_vars:     ``dict{ENV_VAR_NAME: ENV_VAR_VALUE}``
        """
        if not isinstance(env_vars, dict):
            raise TypeError(
                "Environment variables for Plugin must be specified by dict"
            )
        self.default_environment = env_vars
        self._log_debug("Default environment for all commands now set to %s"
                        % self.default_environment)

    def add_default_cmd_environment(self, env_vars):
        """
        Add or modify a specific environment variable in the set of default
        environment variables used by this Plugin.

        :param env_vars:    The environment variables to add to the current
                            set of env vars in use
        :type env_vars:     ``dict``
        """
        if not isinstance(env_vars, dict):
            raise TypeError("Environment variables must be added via dict")
        self._log_debug("Adding %s to default environment" % env_vars)
        self.default_environment.update(env_vars)

    def _get_cmd_environment(self, env=None):
        """
        Get the merged set of environment variables for a command about to be
        executed by this plugin.

        :returns: The set of env vars to use for a command
        :rtype: ``dict``
        """
        if env is None:
            return self.default_environment
        if not isinstance(env, dict):
            raise TypeError("Command env vars must be passed as dict")
        _env = self.default_environment.copy()
        _env.update(env)
        return _env

    def timeout_from_options(self, optname, plugoptname, default_timeout):
        """
        Get the timeout value for either the plugin or a command, as
        determined by either the value provided via the
        plugin.timeout or plugin.cmd-timeout option, the global timeout or
        cmd-timeout options, or the default value set by the plugin or the
        collection, in that order of precendence.

        :param optname: The name of the cmdline option being checked, either
                        'plugin_timeout' or 'timeout'
        :type optname:  ``str``

        :param plugoptname: The name of the plugin option name being checked,
                            either 'timeout' or 'cmd-timeout'
        :type plugoptname: ``str``

        :param default_timeout: The timeout to default to if determination is
                                inconclusive or hits an error
        :type default_timeout:  ``int``

        :returns: The timeout value in seconds
        :rtype:   ``int``
        """
        _timeout = None
        try:
            opt_timeout = self.get_option(optname)
            own_timeout = int(self.get_option(plugoptname))
            if opt_timeout is None:
                _timeout = own_timeout
            elif opt_timeout is not None and own_timeout == -1:
                if opt_timeout == TIMEOUT_DEFAULT:
                    _timeout = default_timeout
                else:
                    _timeout = int(opt_timeout)
            elif opt_timeout is not None and own_timeout > -1:
                _timeout = own_timeout
            else:
                return None
        except ValueError:
            return default_timeout  # Default to known safe value
        if _timeout is not None and _timeout > -1:
            return _timeout
        return default_timeout

    @property
    def timeout(self):
        """Returns either the default plugin timeout value, the value as
        provided on the commandline via -k plugin.timeout=value, or the value
        of the global --plugin-timeout option.
        """
        _timeout = self.timeout_from_options('plugin_timeout', 'timeout',
                                             self.plugin_timeout)
        return _timeout

    @property
    def cmdtimeout(self):
        """Returns either the default command timeout value, the value as
        provided on the commandline via -k plugin.cmd-timeout=value, or the
        value of the global --cmd-timeout option.
        """
        _cmdtimeout = self.timeout_from_options('cmd_timeout', 'cmd-timeout',
                                                self.cmd_timeout)
        return _cmdtimeout

    def set_timeout_hit(self):
        self._timeout_hit = True
        self.manifest.add_field('end_time', datetime.now())
        self.manifest.add_field('timeout_hit', True)

    def check_timeout(self):
        """
        Checks to see if the plugin has hit its timeout.

        This is set when the sos.collect_plugin() method hits a timeout and
        terminates the thread. From there, a Popen() call can still continue to
        run, and we need to manually terminate it. Thus, check_timeout() should
        only be called in sos_get_command_output().

        Since sos_get_command_output() is not plugin aware, this method is
        handed to that call to use as a polling method, to avoid passing the
        entire plugin object.

        :returns: ``True`` if timeout has been hit, else ``False``
        :rtype: ``bool``

        """
        return self._timeout_hit

    @classmethod
    def name(cls):
        """Get the name of the plugin

        :returns: The name of the plugin, in lowercase
        :rtype: ``str``
        """
        if cls.plugin_name:
            return cls.plugin_name
        return cls.__name__.lower()

    @classmethod
    def display_help(cls, section):
        if cls.plugin_name is None:
            cls.display_self_help(section)
        else:
            cls.display_plugin_help(section)

    @classmethod
    def display_plugin_help(cls, section):
        from sos.help import TERMSIZE
        section.set_title("%s Plugin Information - %s"
                          % (cls.plugin_name.title(), cls.short_desc))
        missing = '\nDetailed information is not available for this plugin.\n'

        # Concatenate the docstrings of distro-specific plugins with their
        # base classes, if available.
        try:
            _doc = ''
            _sc = cls.__mro__[1]
            if _sc != Plugin and _sc.__doc__:
                _doc = _sc.__doc__
            if cls.__doc__:
                _doc += cls.__doc__
        except Exception:
            _doc = None

        section.add_text('\n    %s' % _doc if _doc else missing)

        if not any([cls.packages, cls.commands, cls.files, cls.kernel_mods,
                    cls.services, cls.containers]):
            section.add_text("This plugin is always enabled by default.")
        else:
            for trig in ['packages', 'commands', 'files', 'kernel_mods',
                         'services']:
                if getattr(cls, trig, None):
                    section.add_text(
                        "Enabled by %s: %s"
                        % (trig, ', '.join(getattr(cls, trig))),
                        newline=False
                    )
            if getattr(cls, 'containers'):
                section.add_text(
                    "Enabled by containers with names matching: %s"
                    % ', '.join(c for c in cls.containers),
                    newline=False
                )

        if cls.profiles:
            section.add_text(
                "Enabled with the following profiles: %s"
                % ', '.join(p for p in cls.profiles),
                newline=False
            )

        if hasattr(cls, 'verify_packages'):
            section.add_text(
                "\nVerfies packages (when using --verify): %s"
                % ', '.join(pkg for pkg in cls.verify_packages),
                newline=False,
            )

        if cls.postproc is not Plugin.postproc:
            section.add_text(
                'This plugin performs post-processing on potentially '
                'sensitive collections. Disabling post-processing may'
                ' leave sensitive data in plaintext.'
            )

        if not cls.option_list:
            return

        optsec = section.add_section('Plugin Options')
        optsec.add_text(
            "These options may be toggled or changed using '%s'"
            % bold("-k %s.option_name=$value" % cls.plugin_name)
        )
        optsec.add_text(bold(
            "\n{:<4}{:<20}{:<30}{:<20}\n".format(
                ' ', "Option Name", "Default", "Description")
            ), newline=False
        )

        opt_indent = ' ' * 54
        for opt in cls.option_list:
            _def = opt.default
            # convert certain values to text meanings
            if _def is None or _def == '':
                _def = "None/Unset"
            if isinstance(opt.default, bool):
                if opt.default:
                    _def = "True/On"
                else:
                    _def = "False/Off"
            _ln = "{:<4}{:<20}{:<30}{:<20}".format(' ', opt.name, _def,
                                                   opt.desc)
            optsec.add_text(
                textwrap.fill(_ln, width=TERMSIZE,
                              subsequent_indent=opt_indent),
                newline=False
            )
            if opt.long_desc:
                _size = TERMSIZE - 10
                space = ' ' * 8
                optsec.add_text(
                    textwrap.fill(opt.long_desc, width=_size,
                                  initial_indent=space,
                                  subsequent_indent=space),
                    newline=False
                )

    @classmethod
    def display_self_help(cls, section):
        section.set_title("SoS Plugin Detailed Help")
        section.add_text(
            "Plugins are what define what collections occur for a given %s "
            "execution. Plugins are generally representative of a single "
            "system component (e.g. kernel), package (e.g. podman), or similar"
            " construct. Plugins will typically specify multiple files or "
            "directories to copy, as well as commands to execute and collect "
            "the output of for further analysis."
            % bold('sos report')
        )

        subsec = section.add_section('Plugin Enablement')
        subsec.add_text(
            'Plugins will be automatically enabled based on one of several '
            'triggers - a certain package being installed, a command or file '
            'existing, a kernel module being loaded, etc...'
        )
        subsec.add_text(
            "Plugins may also be enabled or disabled by name using the %s or "
            "%s options respectively."
            % (bold('-e $name'), bold('-n $name'))
        )

        subsec.add_text(
            "Certain plugins may only be available for specific distributions "
            "or may behave differently on different distributions based on how"
            " the component for that plugin is installed or how it operates."
            " When using %s, help will be displayed for the version of the "
            "plugin appropriate for your distribution."
            % bold('sos help report.plugins.$plugin')
        )

        optsec = section.add_section('Using Plugin Options')
        optsec.add_text(
            "Many plugins support additional options to enable/disable or in "
            "some other way modify the collections it makes. Plugin options "
            "are set using the %s syntax. Options that are on/off toggles "
            "may exclude setting a value, which will be interpreted as "
            "enabling that option.\n\nSee specific plugin help sections "
            "or %s for more information on these options"
            % (bold('-k $plugin_name.$option_name=$value'),
               bold('sos report -l'))
        )

        seealso = section.add_section('See Also')
        _also = {
            'report.plugins.$plugin': 'Help for a specific $plugin',
            'policies': 'Information on distribution policies'
        }
        seealso.add_text(
            "Additional relevant information may be available in these "
            "help sections:\n\n%s" % "\n".join(
                "{:>8}{:<30}{:<30}".format(' ', sec, desc)
                for sec, desc in _also.items()
            ), newline=False
        )

    def _format_msg(self, msg):
        return "[plugin:%s] %s" % (self.name(), msg)

    def _log_error(self, msg):
        self.soslog.error(self._format_msg(msg))

    def _log_warn(self, msg):
        self.soslog.warning(self._format_msg(msg))

    def _log_info(self, msg):
        self.soslog.info(self._format_msg(msg))

    def _log_debug(self, msg):
        self.soslog.debug(self._format_msg(msg))

    def strip_sysroot(self, path):
        """Remove the configured sysroot from a filesystem path

        :param path:    The filesystem path to strip sysroot from
        :type path: ``str``

        :returns: The stripped filesystem path
        :rtype: ``str``
        """
        if not self.use_sysroot():
            return path
        if self.sysroot and path.startswith(self.sysroot):
            return path[len(self.sysroot):]
        return path

    def use_sysroot(self):
        """Determine if the configured sysroot needs to be used

        :returns: ``True`` if sysroot is not `/`, else ``False``
        :rtype: ``bool``
        """
        return self.sysroot != os.path.abspath(os.sep)

    def tmp_in_sysroot(self):
        """Check if sysroot is within the archive's temp directory

        :returns: ``True`` if sysroot is in the archive's temp directory, else
                  ``False``
        :rtype: ``bool``
        """
        # if sysroot is still None, that implies '/'
        _sysroot = self.sysroot or '/'
        paths = [_sysroot, self.archive.get_tmp_dir()]
        return os.path.commonprefix(paths) == _sysroot

    def is_installed(self, package_name):
        """Is the package $package_name installed?

        :param package_name:    The name of the package to check
        :type package_name:     ``str``

        :returns: ``True`` id the package is installed, else ``False``
        :rtype: ``bool``
        """
        return self.policy.pkg_by_name(package_name) is not None

    def is_service(self, name):
        """Does the service $name exist on the system?

        :param name:    The name of the service to check
        :type name:     ``str``

        :returns: ``True`` if service is present on the system, else ``False``
        :rtype: ``bool``
        """
        return self.policy.init_system.is_service(name)

    def is_service_enabled(self, name):
        """Is the service $name enabled?

        :param name:    The name of the service to check
        :type name:     ``str``

        :returns: ``True if service is enabled on the system, else ``False``
        :rtype: ``bool``
        """
        return self.policy.init_system.is_enabled(name)

    def is_service_disabled(self, name):
        """Is the service $name disabled?

        :param name:    The name of the service to check
        :type name:     ``str``

        :returns: ``True`` if service is disabled on the system, else ``False``
        :rtype: ``bool``
        """
        return self.policy.init_system.is_disabled(name)

    def is_service_running(self, name):
        """Is the service $name currently running?

        :param name:    The name of the service to check
        :type name:     ``str``

        :returns: ``True`` if the service is running on the system, else
                  ``False``
        :rtype: ``bool``
        """
        return self.policy.init_system.is_running(name)

    def get_service_status(self, name):
        """Return the reported status for service $name

        :param name:    The name of the service to check
        :type name:     ``str``

        :returns: The state of the service according to the init system
        :rtype: ``str``
        """
        return self.policy.init_system.get_service_status(name)['status']

    def get_service_names(self, regex):
        """Get all service names matching regex

        :param regex:    A regex to match service names against
        :type regex:    ``str``

        :returns: All service name(s) matching the given `regex`
        :rtype: ``list``
        """
        return self.policy.init_system.get_service_names(regex)

    def set_predicate(self, pred):
        """Set or clear the default predicate for this plugin.

        :param pred:    The predicate to use as the default for this plugin
        :type pred:     ``SoSPredicate``
        """
        self.predicate = pred

    def set_cmd_predicate(self, pred):
        """Set or clear the default predicate for command collection for this
        plugin. If set, this predecate takes precedence over the `Plugin`
        default predicate for command and journal data collection.

        :param pred:    The predicate to use as the default command predicate
        :type pred:     ``SoSPredicate``
        """
        self.cmd_predicate = pred

    def get_predicate(self, cmd=False, pred=None):
        """Get the current default `Plugin` or command predicate.

        :param cmd:     If a command predicate is set, should it be used.
        :type cmd:      ``bool``

        :param pred:    An optional predicate to pass if no command or plugin
                        predicate is set
        :type pred:     ``SoSPredicate``

        :returns:   `pred` if neither a command predicate or plugin predicate
                    is set. The command predicate if one is set and `cmd` is
                    ``True``, else the plugin default predicate (which may be
                    ``None``).
        :rtype:     ``SoSPredicate`` or ``None``
        """
        if pred is not None:
            return pred
        if cmd and self.cmd_predicate is not None:
            return self.cmd_predicate
        return self.predicate

    def test_predicate(self, cmd=False, pred=None):
        """Test the current predicate and return its value.

        :param cmd: ``True`` if the predicate is gating a command or
                    ``False`` otherwise.
        :param pred: An optional predicate to override the current
                     ``Plugin`` or command predicate.

        :returns: ``True`` or ``False`` based on predicate evaluation, or
                  ``False`` if no predicate
        :rtype: ``bool``
        """
        pred = self.get_predicate(cmd=cmd, pred=pred)
        if pred is not None:
            return bool(pred)
        return False

    def log_skipped_cmd(self, cmd, pred, changes=False):
        """Log that a command was skipped due to predicate evaluation.

        Emit a warning message indicating that a command was skipped due
        to predicate evaluation. If ``kmods`` or ``services`` are ``True``
        then the list of expected kernel modules or services will be
        included in the log message. If ``allow_changes`` is ``True`` a
        message indicating that the missing data can be collected by using
        the "--allow-system-changes" command line option will be included.

        :param cmd:     The command that was skipped
        :type cmd:      ``str``

        :param pred:    The predicate that caused the command to be skipped
        :type pred:     ``SoSPredicate``

        :param changes: Is the `--allow-system-changes` enabled
        :type changes:  ``bool``
        """
        if pred is None:
            pred = SoSPredicate(self)
        msg = "skipped command '%s': %s" % (cmd, pred.report_failure())

        if changes:
            msg += " Use '--allow-system-changes' to enable collection."

        self._log_warn(msg)

    def do_cmd_private_sub(self, cmd, desc=""):
        """Remove certificate and key output archived by sos report.
        Any matching instances are replaced with: '-----SCRUBBED' and this
        function does not take a regexp or substituting string.

        :param cmd: The name of the binary to scrub certificate output from
        :type cmd:  ``str``

        :param desc: An identifier to add to the `SCRUBBED` header line
        :type desc: ``str``

        :returns: Number of replacements made
        :rtype: ``int``
        """
        if not self.executed_commands:
            return 0

        self._log_debug("Scrubbing certs and keys for commands matching %s"
                        % (cmd))

        replace = "%s %s" % (_cert_replace, desc) if desc else _cert_replace

        return self.do_cmd_output_sub(cmd, _certmatch, replace)

    def do_cmd_output_sub(self, cmd, regexp, subst):
        """Apply a regexp substitution to command output archived by sosreport.

        This is used to obfuscate sensitive information captured by command
        output collection via plugins.

        :param cmd: The command name/binary name for collected output that
                    needs to be obfuscated. Internally globbed with a leading
                    and trailing `*`
        :type cmd:  ``str``

        :param regexp: A regex to match the contents of the command output
                       against
        :type regexp: ``str`` or compile ``re`` object

        :param subst: The substitution string used to replace matches from
                      `regexp`
        :type subst: ``str``

        :returns: Number of replacements made
        :rtype: ``int``
        """
        globstr = '*' + cmd + '*'
        pattern = regexp.pattern if hasattr(regexp, "pattern") else regexp
        self._log_debug("substituting '%s' for '%s' in commands matching '%s'"
                        % (subst, pattern, globstr))

        if not self.executed_commands:
            return 0

        replacements = None
        try:
            for called in self.executed_commands:
                # was anything collected?
                if called['file'] is None:
                    continue
                if called['binary'] == 'yes':
                    self._log_warn("Cannot apply regex substitution to binary"
                                   " output: '%s'" % called['exe'])
                    continue
                if fnmatch.fnmatch(called['cmd'], globstr):
                    path = os.path.join(self.commons['cmddir'], called['file'])
                    self._log_debug("applying substitution to '%s'" % path)
                    readable = self.archive.open_file(path)
                    result, replacements = re.subn(
                        regexp, subst, readable.read())
                    if replacements:
                        self.archive.add_string(result, path)

        except Exception as e:
            msg = "regex substitution failed for '%s' with: '%s'"
            self._log_error(msg % (called['exe'], e))
            replacements = None
        return replacements

    def do_file_private_sub(self, pathregex, desc=""):
        """Scrub certificate/key/etc information from files collected by sos.

        Files matching the provided pathregex are searched for content that
        resembles certificate, ssh keys, or similar information. Any matches
        are replaced with "-----SCRUBBED $desc" where `desc` is a description
        of the specific type of content being replaced, e.g.
        "-----SCRUBBED RSA PRIVATE KEY" so that support representatives can
        at least be informed of what type of content it was originally.

        :param pathregex: A string or regex of a filename to match against
        :type pathregex: ``str``

        :param desc: A description of the replaced content
        :type desc: ``str``
        """
        self._log_debug("Scrubbing certs and keys for paths matching %s"
                        % pathregex)
        match = re.compile(pathregex).match
        replace = "%s %s" % (_cert_replace, desc) if desc else _cert_replace
        file_list = [f for f in self.copied_files if match(f['srcpath'])]
        for i in file_list:
            path = i['dstpath']
            if not path:
                continue
            self.do_file_sub(path, _certmatch, replace)

    def do_file_sub(self, srcpath, regexp, subst):
        """Apply a regexp substitution to a file archived by sosreport.

        :param srcpath: Path in the archive where the file can be found
        :type srcpath: ``str``

        :param regexp:  A regex to match the contents of the file
        :type regexp: ``str`` or compiled ``re`` object

        :param subst: The substitution string to be used to replace matches
                      within the file
        :type subst: ``str``

        :returns: Number of replacements made
        :rtype: ``int``
        """
        try:
            path = self._get_dest_for_srcpath(srcpath)
            pattern = regexp.pattern if hasattr(regexp, "pattern") else regexp
            self._log_debug("substituting scrpath '%s'" % srcpath)
            self._log_debug("substituting '%s' for '%s' in '%s'"
                            % (subst, pattern, path))
            if not path:
                return 0
            readable = self.archive.open_file(path)
            content = readable.read()
            if not isinstance(content, str):
                content = content.decode('utf8', 'ignore')
            result, replacements = re.subn(regexp, subst, content)
            if replacements:
                self.archive.add_string(result, srcpath)
            else:
                replacements = 0
        except (OSError, IOError) as e:
            # if trying to regexp a nonexisting file, dont log it as an
            # error to stdout
            if e.errno == errno.ENOENT:
                msg = "file '%s' not collected, substitution skipped"
                self._log_debug(msg % path)
            else:
                msg = "regex substitution failed for '%s' with: '%s'"
                self._log_error(msg % (path, e))
            replacements = 0
        return replacements

    def do_path_regex_sub(self, pathexp, regexp, subst):
        """Apply a regexp substituation to a set of files archived by
        sos. The set of files to be substituted is generated by matching
        collected file pathnames against `pathexp`.

        :param pathexp: A regex to match filenames within the archive
        :type pathexp: ``str`` or compiled ``re`` object

        :param regexp: A regex to match against the contents of each file
        :type regexp: ``str`` or compiled ``re`` object

        :param subst: The substituion string to be used to replace matches
        :type subst: ``str``
        """
        if not hasattr(pathexp, "match"):
            pathexp = re.compile(pathexp)
        match = pathexp.match
        file_list = [f for f in self.copied_files if match(f['srcpath'])]
        for file in file_list:
            self.do_file_sub(file['srcpath'], regexp, subst)

    def do_regex_find_all(self, regex, fname):
        return regex_findall(regex, fname)

    def _copy_symlink(self, srcpath):
        # the target stored in the original symlink
        linkdest = os.readlink(srcpath)
        dest = os.path.join(os.path.dirname(srcpath), linkdest)
        # Absolute path to the link target. If SYSROOT != '/' this path
        # is relative to the host root file system.
        absdest = os.path.normpath(dest)
        # adjust the target used inside the report to always be relative
        if os.path.isabs(linkdest):
            # Canonicalize the link target path to avoid additional levels
            # of symbolic links (that would affect the path nesting level).
            realdir = os.path.realpath(os.path.dirname(srcpath))
            reldest = os.path.relpath(linkdest, start=realdir)
            # trim leading /sysroot
            if self.use_sysroot():
                reldest = reldest[len(os.sep + os.pardir):]
            self._log_debug("made link target '%s' relative as '%s'"
                            % (linkdest, reldest))
        else:
            reldest = linkdest

        self._log_debug("copying link '%s' pointing to '%s' with isdir=%s"
                        % (srcpath, linkdest, self.path_isdir(absdest)))

        dstpath = self.strip_sysroot(srcpath)
        # use the relative target path in the tarball
        self.archive.add_link(reldest, dstpath)

        if self.path_isdir(absdest):
            self._log_debug("link '%s' is a directory, skipping..." % linkdest)
            return

        self.copied_files.append({'srcpath': srcpath,
                                  'dstpath': dstpath,
                                  'symlink': "yes",
                                  'pointsto': linkdest})

        # Check for indirect symlink loops by stat()ing the next step
        # in the link chain.
        try:
            os.stat(absdest)
        except OSError as e:
            if e.errno == 40:
                self._log_debug("link '%s' is part of a file system "
                                "loop, skipping target..." % dstpath)
                return

        # copy the symlink target translating relative targets
        # to absolute paths to pass to _do_copy_path.
        self._log_debug("normalized link target '%s' as '%s'"
                        % (linkdest, absdest))

        # skip recursive copying of symlink pointing to itself.
        if (absdest != srcpath):
            self._do_copy_path(absdest)
        else:
            self._log_debug("link '%s' points to itself, skipping target..."
                            % linkdest)

    def _copy_dir(self, srcpath):
        try:
            for name in self.listdir(srcpath):
                self._log_debug("recursively adding '%s' from '%s'"
                                % (name, srcpath))
                path = os.path.join(srcpath, name)
                self._do_copy_path(path)
        except OSError as e:
            if e.errno == errno.EPERM or errno.EACCES:
                msg = "Permission denied"
                self._log_warn("_copy_dir: '%s' %s" % (srcpath, msg))
                return
            if e.errno == errno.ELOOP:
                msg = "Too many levels of symbolic links copying"
                self._log_error("_copy_dir: %s '%s'" % (msg, srcpath))
                return
            raise

    def _get_dest_for_srcpath(self, srcpath):
        if self.use_sysroot():
            srcpath = self.path_join(srcpath)
        for copied in self.copied_files:
            if srcpath == copied["srcpath"]:
                return copied["dstpath"]
        return None

    def _is_forbidden_path(self, path):
        return _path_in_path_list(path, self.forbidden_paths)

    def _is_policy_forbidden_path(self, path):
        return any([
            fnmatch.fnmatch(path, fp) for fp in self.policy.forbidden_paths
        ])

    def _is_skipped_path(self, path):
        """Check if the given path matches a user-provided specification to
        ignore collection of via the ``--skip-files`` option

        :param path:    The filepath being collected
        :type path: ``str``

        :returns: ``True`` if file should be skipped, else ``False``
        """
        for _skip_path in self.skip_files:
            if fnmatch.fnmatch(path, _skip_path):
                return True
        return False

    def _copy_node(self, path, st):
        dev_maj = os.major(st.st_rdev)
        dev_min = os.minor(st.st_rdev)
        mode = st.st_mode
        self.archive.add_node(path, mode, os.makedev(dev_maj, dev_min))

    # Methods for copying files and shelling out
    def _do_copy_path(self, srcpath, dest=None):
        """Copy file or directory to the destination tree. If a directory, then
        everything below it is recursively copied. A list of copied files are
        saved for use later in preparing a report.
        """
        if self._timeout_hit:
            return

        if self._is_forbidden_path(srcpath):
            self._log_debug("skipping forbidden path '%s'" % srcpath)
            return ''

        if not dest:
            dest = srcpath

        if self.use_sysroot():
            dest = self.strip_sysroot(dest)

        try:
            st = os.lstat(srcpath)
        except (OSError, IOError):
            self._log_info("failed to stat '%s'" % srcpath)
            return

        if stat.S_ISLNK(st.st_mode):
            self._copy_symlink(srcpath)
            return
        else:
            if stat.S_ISDIR(st.st_mode) and os.access(srcpath, os.R_OK):
                # copy empty directory
                if not self.listdir(srcpath):
                    self.archive.add_dir(dest)
                    return
                self._copy_dir(srcpath)
                return

        # handle special nodes (block, char, fifo, socket)
        if not (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)):
            ntype = _node_type(st)
            self._log_debug("creating %s node at archive:'%s'"
                            % (ntype, dest))
            self._copy_node(dest, st)
            return

        # if we get here, it's definitely a regular file (not a symlink or dir)
        self._log_debug("copying path '%s' to archive:'%s'" % (srcpath, dest))

        # if not readable(srcpath)
        if not st.st_mode & 0o444:
            # FIXME: reflect permissions in archive
            self.archive.add_string("", dest)
        else:
            self.archive.add_file(srcpath, dest)

        self.copied_files.append({
            'srcpath': srcpath,
            'dstpath': dest,
            'symlink': "no"
        })

    def add_forbidden_path(self, forbidden, recursive=False):
        """Specify a path, or list of paths, to not copy, even if it's part of
        an ``add_copy_spec()`` call

        :param forbidden: A filepath to forbid collection from
        :type forbidden: ``str`` or a ``list`` of strings

        :param recursive: Should forbidden glob be applied recursively
        """
        if isinstance(forbidden, str):
            forbidden = [forbidden]

        if self.use_sysroot():
            forbidden = [self.path_join(f) for f in forbidden]

        for forbid in forbidden:
            self._log_info("adding forbidden path '%s'" % forbid)
            for path in glob.glob(forbid, recursive=recursive):
                self.forbidden_paths.append(path)

    def set_option(self, optionname, value):
        """Set the named option to value. Ensure the original type of the
        option value is preserved

        :param optioname: The name of the option to set
        :type optioname: ``str``

        :param value: The value to set the option to

        :returns: ``True`` if the option is successfully set, else ``False``
        :rtype: ``bool``
        """
        if optionname in self.options:
            try:
                self.options[optionname].set_value(value)
                return True
            except Exception as err:
                self._log_error(err)
                raise
        return False

    def get_option(self, optionname, default=0):
        """Retrieve the value of the requested option, searching in order:
        parameters passed from the command line, set via `set_option()`, or the
        global_plugin_options dict.

        `optionname` may be iterable, in which case this function will return
        the first match.

        :param optionname: The name of the option to retrieve the value of
        :type optionname: ``str``

        :param default: Optionally provide a default value to return if no
                        option matching `optionname` is found. Default 0

        :returns: The value of `optionname` if found, else `default`
        """

        global_options = (
            'all_logs', 'allow_system_changes', 'cmd_timeout', 'log_size',
            'plugin_timeout', 'since', 'verify'
        )

        if optionname in global_options:
            return getattr(self.commons['cmdlineopts'], optionname)

        if optionname in self.options:
            opt = self.options[optionname]
            if not default or opt.value is not None:
                return opt.value
            return default
        return default

    def _add_copy_paths(self, copy_paths):
        self.copy_paths.update(copy_paths)

    def add_file_tags(self, tagdict):
        """Apply a tag to a file matching a given regex, for use when a file
        is copied by a more generic copyspec.

        :param tagdict: A dict containing the filepatterns to match and the
                        tag(s) to apply to those files
        :type tagdict: ``dict``

        `tagdict` takes the form `{file_pattern: tag}`, E.G. to match all bond
        devices from /proc/net/bonding with the tag `bond`, use
        `{'/proc/net/bonding/bond.*': ['bond']}`
        """
        for fname in tagdict:
            if isinstance(tagdict[fname], str):
                tagdict[fname] = [tagdict[fname]]
        self.filetags.update(tagdict)

    def get_tags_for_file(self, fname):
        """Get the tags that should be associated with a file matching a given
        regex

        :param fname:   A regex for filenames to be matched against
        :type fname: ``str``

        :returns:   The tag(s) associated with `fname`
        :rtype: ``list`` of strings
        """
        for key, val in self.filetags.items():
            if re.match(key, fname):
                return val
        return []

    def generate_copyspec_tags(self):
        """After file collections have completed, retroactively generate
        manifest entries to apply tags to files copied by generic copyspecs
        """
        for file_regex in self.filetags:
            manifest_data = {
                'specification': file_regex,
                'files_copied': [],
                'tags': self.filetags[file_regex]
            }
            matched_files = []
            for cfile in self.copied_files:
                if re.match(file_regex, cfile['srcpath']):
                    matched_files.append(cfile['dstpath'])
            if matched_files:
                manifest_data['files_copied'] = matched_files
                self.manifest.files.append(manifest_data)

    def add_copy_spec(self, copyspecs, sizelimit=None, maxage=None,
                      tailit=True, pred=None, tags=[], container=None):
        """Add a file, directory, or regex matching filepaths to the archive

        :param copyspecs: A file, directory, or regex matching filepaths
        :type copyspecs: ``str`` or a ``list`` of strings

        :param sizelimit: Limit the total size of collections from `copyspecs`
                          to this size in MB
        :type sizelimit: ``int``

        :param maxage: Collect files with `mtime` not older than this many
                       hours
        :type maxage: ``int``

        :param tailit: Should a file that exceeds `sizelimit` be tail'ed to fit
                       the remaining space to meet `sizelimit`
        :type tailit: ``bool``

        :param pred: A predicate to gate if `copyspecs` should be collected
        :type pred: ``SoSPredicate``

        :param tags: A tag or set of tags to add to the metadata information
                     for this collection
        :type tags: ``str`` or a ``list`` of strings

        :param container: Container(s) from which this file should be copied
        :type container: ``str`` or a ``list`` of strings

        `copyspecs` will be expanded and/or globbed as appropriate. Specifying
        a directory here will cause the plugin to attempt to collect the entire
        directory, recursively.

        If `container` is specified, `copyspecs` may only be explicit paths,
        not globs as currently container runtimes do not support glob expansion
        as part of the copy operation.

        Note that `sizelimit` is applied to each `copyspec`, not each file
        individually. For example, a copyspec of
        ``['/etc/foo', '/etc/bar.conf']`` and a `sizelimit` of 25 means that
        sos will collect up to 25MB worth of files within `/etc/foo`, and will
        collect the last 25MB of `/etc/bar.conf`.
        """
        since = None
        if self.get_option('since'):
            since = self.get_option('since')

        logarchive_pattern = re.compile(r'.*((\.(zip|gz|bz2|xz))|[-.][\d]+)$')
        configfile_pattern = re.compile(r"^%s/*" % self.path_join("etc"))

        if not self.test_predicate(pred=pred):
            self._log_info("skipped copy spec '%s' due to predicate (%s)" %
                           (copyspecs, self.get_predicate(pred=pred)))
            return

        if sizelimit is None:
            sizelimit = self.get_option("log_size")

        if self.get_option('all_logs'):
            sizelimit = None

        if sizelimit:
            sizelimit *= 1024 * 1024  # in MB

        if not copyspecs:
            return False

        if isinstance(copyspecs, str):
            copyspecs = [copyspecs]

        if isinstance(tags, str):
            tags = [tags]

        def get_filename_tag(fname):
            """Generate a tag to add for a single file copyspec

            This tag will be set to the filename, minus any extensions
            except '.conf' which will be converted to '_conf'
            """
            fname = fname.replace('-', '_')
            if fname.endswith('.conf'):
                return fname.replace('.', '_')
            return fname.split('.')[0]

        for copyspec in copyspecs:
            if not (copyspec and len(copyspec)):
                return False

            if not container:
                if self.use_sysroot():
                    copyspec = self.path_join(copyspec)
                files = self._expand_copy_spec(copyspec)
                if len(files) == 0:
                    continue
            else:
                files = [copyspec]

            _spec_tags = []
            if len(files) == 1:
                _spec_tags = [get_filename_tag(files[0].split('/')[-1])]

            _spec_tags.extend(tags)
            _spec_tags = list(set(_spec_tags))

            if container:
                if isinstance(container, str):
                    container = [container]
                for con in container:
                    if not self.container_exists(con):
                        continue
                    _tail = False
                    if sizelimit:
                        # to get just the size, stat requires a literal '%s'
                        # which conflicts with python string formatting
                        cmd = "stat -c %s " + copyspec
                        ret = self.exec_cmd(cmd, container=con)
                        if ret['status'] == 0:
                            try:
                                consize = int(ret['output'])
                                if consize > sizelimit:
                                    _tail = True
                            except ValueError:
                                self._log_info(
                                    "unable to determine size of '%s' in "
                                    "container '%s'. Skipping collection."
                                    % (copyspec, con)
                                )
                                continue
                        else:
                            self._log_debug(
                                "stat of '%s' in container '%s' failed, "
                                "skipping collection: %s"
                                % (copyspec, con, ret['output'])
                            )
                            continue
                    self.container_copy_paths.append(
                        (con, copyspec, sizelimit, _tail, _spec_tags)
                    )
                    self._log_info(
                        "added collection of '%s' from container '%s'"
                        % (copyspec, con)
                    )
                # break out of the normal flow here as container file
                # copies are done via command execution, not raw cp/mv
                # operations
                continue

            # Files hould be sorted in most-recently-modified order, so that
            # we collect the newest data first before reaching the limit.
            def getmtime(path):
                try:
                    return os.path.getmtime(path)
                except OSError:
                    return 0

            def time_filter(path):
                """ When --since is passed, or maxage is coming from the
                plugin, we need to filter out older files """

                # skip config files or not-logarchive files from the filter
                if ((logarchive_pattern.search(path) is None) or
                   (configfile_pattern.search(path) is not None)):
                    return True
                filetime = datetime.fromtimestamp(getmtime(path))
                if ((since and filetime < since) or
                   (maxage and (time()-filetime < maxage*3600))):
                    return False
                return True

            if since or maxage:
                files = list(filter(lambda f: time_filter(f), files))

            files.sort(key=getmtime, reverse=True)
            current_size = 0
            limit_reached = False

            _manifest_files = []

            for _file in files:
                if _file in self.copy_paths:
                    self._log_debug("skipping redundant file '%s'" % _file)
                    continue
                if self._is_forbidden_path(_file):
                    self._log_debug("skipping forbidden path '%s'" % _file)
                    continue
                if self._is_policy_forbidden_path(_file):
                    self._log_debug("skipping policy forbidden path '%s'"
                                    % _file)
                    continue
                if self._is_skipped_path(_file):
                    self._log_debug("skipping excluded path '%s'" % _file)
                    continue
                if limit_reached:
                    self._log_info("skipping '%s' over size limit" % _file)
                    continue

                try:
                    file_size = os.stat(_file)[stat.ST_SIZE]
                except OSError:
                    # if _file is a broken symlink, we should collect it,
                    # otherwise skip it
                    if self.path_islink(_file):
                        file_size = 0
                    else:
                        self._log_info("failed to stat '%s', skipping" % _file)
                        continue
                current_size += file_size

                if sizelimit and current_size > sizelimit:
                    limit_reached = True

                    if tailit and not file_is_binary(_file):
                        self._log_info("collecting tail of '%s' due to size "
                                       "limit" % _file)
                        file_name = _file
                        if file_name[0] == os.sep:
                            file_name = file_name.lstrip(os.sep)
                        strfile = (
                            file_name.replace(os.path.sep, ".") + ".tailed"
                        )
                        add_size = sizelimit + file_size - current_size
                        self.add_string_as_file(tail(_file, add_size), strfile)
                        rel_path = os.path.relpath('/', os.path.dirname(_file))
                        link_path = os.path.join(rel_path, 'sos_strings',
                                                 self.name(), strfile)
                        self.archive.add_link(link_path, _file)
                        _manifest_files.append(_file.lstrip('/'))
                    else:
                        self._log_info("skipping '%s' over size limit" % _file)
                else:
                    # size limit not exceeded, copy the file
                    _manifest_files.append(_file.lstrip('/'))
                    self._add_copy_paths([_file])
                    # in the corner case we just reached the sizelimit, we
                    # should collect the whole file and stop
                    limit_reached = (sizelimit and current_size == sizelimit)

            if not container:
                # container collection manifest additions are handled later
                if self.manifest:
                    self.manifest.files.append({
                        'specification': copyspec,
                        'files_copied': _manifest_files,
                        'tags': _spec_tags
                    })

    def add_blockdev_cmd(self, cmds, devices='block', timeout=None,
                         sizelimit=None, chroot=True, runat=None, env=None,
                         binary=False, prepend_path=None, whitelist=[],
                         blacklist=[], tags=[], priority=10):
        """Run a command or list of commands against storage-related devices.

        Any commands specified by cmd will be iterated over the list of the
        specified devices. Commands passed to this should include a '%(dev)s'
        variable for substitution.

        :param cmds: The command(s) to run against the list of devices
        :type cmds: ``str`` or a ``list`` of strings

        :param devices: The device paths to run `cmd` against. If set to
                        `block` or `fibre`, the commands will be run against
                        the matching list of discovered devices
        :type devices: ``str`` or a ``list`` of device paths

        :param timeout: Timeout in seconds to allow each `cmd` to run
        :type timeout: ``int``

        :param sizelimit: Maximum amount of output to collect, in MB
        :type sizelimit: ``int``

        :param chroot: Should sos chroot the command(s) being run
        :type chroot: ``bool``

        :param runat: Set the filesystem location to execute the command from
        :type runat: ``str``

        :param env: Set environment variables for the command(s) being run
        :type env: ``dict``

        :param binary: Is the output collected going to be binary data
        :type binary: ``bool``

        :param prepend_path: The leading path for block device names
        :type prepend_path: ``str`` or ``None``

        :param whitelist: Limit the devices the `cmds` will be run against to
                          devices matching these item(s)
        :type whitelist: ``list`` of ``str``

        :param blacklist: Do not run `cmds` against devices matching these
                          item(s)
        :type blacklist: ``list`` of ``str``
        """
        _dev_tags = []
        if isinstance(tags, str):
            tags = [tags]
        if devices == 'block':
            prepend_path = prepend_path or '/dev/'
            devices = self.devices['block']
            _dev_tags.append('block')
        if devices == 'fibre':
            devices = self.devices['fibre']
            _dev_tags.append('fibre')
        _dev_tags.extend(tags)
        self._add_device_cmd(cmds, devices, timeout=timeout,
                             sizelimit=sizelimit, chroot=chroot, runat=runat,
                             env=env, binary=binary, prepend_path=prepend_path,
                             whitelist=whitelist, blacklist=blacklist,
                             tags=_dev_tags, priority=priority)

    def _add_device_cmd(self, cmds, devices, timeout=None, sizelimit=None,
                        chroot=True, runat=None, env=None, binary=False,
                        prepend_path=None, whitelist=[], blacklist=[],
                        tags=[], priority=10):
        """Run a command against all specified devices on the system.
        """
        if isinstance(cmds, str):
            cmds = [cmds]
        if isinstance(devices, str):
            devices = [devices]
        if isinstance(whitelist, str):
            whitelist = [whitelist]
        if isinstance(blacklist, str):
            blacklist = [blacklist]
        sizelimit = sizelimit or self.get_option('log_size')
        for cmd in cmds:
            for device in devices:
                _dev_ok = True
                _dev_tags = [device]
                _dev_tags.extend(tags)
                if whitelist:
                    if not any(re.match(wl, device) for wl in whitelist):
                        _dev_ok = False
                if blacklist:
                    if any(re.match(blist, device) for blist in blacklist):
                        _dev_ok = False
                if not _dev_ok:
                    continue
                if prepend_path:
                    device = self.path_join(prepend_path, device)
                _cmd = cmd % {'dev': device}
                self._add_cmd_output(cmd=_cmd, timeout=timeout,
                                     sizelimit=sizelimit, chroot=chroot,
                                     runat=runat, env=env, binary=binary,
                                     tags=_dev_tags, priority=priority)

    def _add_cmd_output(self, **kwargs):
        """Internal helper to add a single command to the collection list."""
        pred = kwargs.pop('pred') if 'pred' in kwargs else SoSPredicate(self)
        if 'priority' not in kwargs:
            kwargs['priority'] = 10
        if 'changes' not in kwargs:
            kwargs['changes'] = False
        if self.get_option('all_logs') or kwargs['sizelimit'] == 0:
            kwargs['to_file'] = True
        soscmd = SoSCommand(**kwargs)
        self._log_debug("packed command: " + soscmd.__str__())
        for _skip_cmd in self.skip_commands:
            # This probably seems weird to be doing filename matching on the
            # commands, however we want to remain consistent with our regex
            # matching with file paths, which sysadmins are almost guaranteed
            # to assume will use shell-style unix matching
            if fnmatch.fnmatch(soscmd.cmd, _skip_cmd):
                self._log_debug("skipping excluded command '%s'" % soscmd.cmd)
                return
        if self.test_predicate(cmd=True, pred=pred):
            self.collect_cmds.append(soscmd)
            self._log_info("added cmd output '%s'" % soscmd.cmd)
        else:
            self.log_skipped_cmd(soscmd.cmd, pred, changes=soscmd.changes)

    def add_cmd_output(self, cmds, suggest_filename=None,
                       root_symlink=None, timeout=None, stderr=True,
                       chroot=True, runat=None, env=None, binary=False,
                       sizelimit=None, pred=None, subdir=None,
                       changes=False, foreground=False, tags=[],
                       priority=10, cmd_as_tag=False, container=None,
                       to_file=False):
        """Run a program or a list of programs and collect the output

        Output will be limited to `sizelimit`, collecting the last X amount
        of command output matching `sizelimit`. Unless `suggest_filename` is
        set, the file that the output is saved to will match the command as
        it was executed, and will be saved under `sos_commands/$plugin`

        :param cmds: The command(s) to execute
        :type cmds: ``str`` or a ``list`` of strings

        :param suggest_filename: Override the name of the file output is saved
                                 to within the archive
        :type suggest_filename: ``str``

        :param root_symlink: If set, create a symlink with this name in the
                             archive root
        :type root_symlink: ``str``

        :param timeout: Timeout in seconds to allow each `cmd` to run for
        :type timeout: ``int``

        :param stderr: Should stderr output be collected
        :type stderr: ``bool``

        :param chroot: Should sos chroot the `cmds` being run
        :type chroot: ``bool``

        :param runat: Run the `cmds` from this location in the filesystem
        :type runat: ``str``

        :param env: Set environment variables for the `cmds` being run
        :type env: ``dict``

        :param binary: Is the command expected to produce binary output
        :type binary: ``bool``

        :param sizelimit: Maximum amount of output in MB to save
        :type sizelimit: ``int``

        :param pred: A predicate to gate if `cmds` should be collected or not
        :type pred: ``SoSPredicate``

        :param subdir: Save output to this subdirectory, within the plugin's
                       directory under sos_commands
        :type subdir: ``str``

        :param changes: Do `cmds` have the potential to change system state
        :type changes: ``int``

        :param foreground: Should the `cmds` be run in the foreground, with an
                           attached TTY
        :type foreground: ``bool``

        :param tags: A tag or set of tags to add to the metadata entries for
                     the `cmds` being run
        :type tags: ``str`` or a ``list`` of strings

        :param priority:  The priority with which this command should be run,
                          lower values will run before higher values
        :type priority: ``int``

        :param cmd_as_tag: Should the command string be automatically formatted
                           to a tag?
        :type cmd_as_tag: ``bool``

        :param container: Run the specified `cmds` inside a container with this
                          ID or name
        :type container:  ``str``

        :param to_file: Should command output be written directly to a new
                        file rather than stored in memory?
        :type to_file:  ``bool``
        """
        if isinstance(cmds, str):
            cmds = [cmds]
        if len(cmds) > 1 and (suggest_filename or root_symlink):
            self._log_warn("ambiguous filename or symlink for command list")
        if sizelimit is None:
            sizelimit = self.get_option("log_size")
        if pred is None:
            pred = self.get_predicate(cmd=True)
        for cmd in cmds:
            container_cmd = None
            if container:
                ocmd = cmd
                container_cmd = (ocmd, container)
                cmd = self.fmt_container_cmd(container, cmd)
                if not cmd:
                    self._log_debug("Skipping command '%s' as the requested "
                                    "container '%s' does not exist."
                                    % (ocmd, container))
                    continue
            self._add_cmd_output(cmd=cmd, suggest_filename=suggest_filename,
                                 root_symlink=root_symlink, timeout=timeout,
                                 stderr=stderr, chroot=chroot, runat=runat,
                                 env=env, binary=binary, sizelimit=sizelimit,
                                 pred=pred, subdir=subdir, tags=tags,
                                 changes=changes, foreground=foreground,
                                 priority=priority, cmd_as_tag=cmd_as_tag,
                                 to_file=to_file, container_cmd=container_cmd)

    def add_cmd_tags(self, tagdict):
        """Retroactively add tags to any commands that have been run by this
        plugin that match a given regex

        :param tagdict: A dict containing the command regex and associated tags
        :type tagdict: ``dict``

        `tagdict` takes the form of {cmd_regex: tags}, for example to tag all
        commands starting with `foo` with the tag `bar`, use
        {'foo.*': ['bar']}
        """
        for cmd in tagdict:
            if isinstance(tagdict[cmd], str):
                tagdict[cmd] = [tagdict[cmd]]
        self.cmdtags.update(tagdict)

    def get_tags_for_cmd(self, cmd):
        """Get the tag(s) that should be associated with the given command

        :param cmd: The command that tags should be applied to
        :type cmd: ``str``

        :returns: Any tags associated with the command
        :rtype: ``list``
        """
        for key, val in self.cmdtags.items():
            if re.match(key, cmd):
                return val
        return []

    def get_cmd_output_path(self, name=None, make=True):
        """Get the path where this plugin will save command output

        :param name: Optionally specify a filename to use as part of the
                     command output path
        :type name: ``str`` or ``None``

        :param make: Attempt to create the command output path
        :type make: ``bool``

        :returns: The path where the plugin will write command output data
                  within the archive
        :rtype: ``str``
        """
        cmd_output_path = os.path.join(self.archive.get_tmp_dir(),
                                       'sos_commands', self.name())
        if name:
            cmd_output_path = os.path.join(cmd_output_path, name)
        if make:
            os.makedirs(cmd_output_path)

        return cmd_output_path

    def file_grep(self, regexp, *fnames):
        """Grep through file(s) for a specific string or regex

        :param regexp: The string or regex to search for
        :type regexp: ``str``

        :param fnames: Paths to grep through
        :type fnames: ``str``, ``list`` of string, or open file objects

        :returns: Lines matching `regexp`
        :rtype: ``str``
        """
        return grep(regexp, *fnames)

    def _mangle_command(self, exe):
        name_max = self.archive.name_max()
        return _mangle_command(exe, name_max)

    def _make_command_filename(self, exe, subdir=None):
        """The internal function to build up a filename based on a command."""

        plugin_dir = self.name()
        if subdir:
            plugin_dir += "/%s" % subdir
        outdir = os.path.join(self.commons['cmddir'], plugin_dir)
        outfn = self._mangle_command(exe)

        # check for collisions
        if os.path.exists(os.path.join(self.archive.get_tmp_dir(),
                                       outdir, outfn)):
            inc = 1
            name_max = self.archive.name_max()
            while True:
                suffix = ".%d" % inc
                newfn = outfn
                if name_max < len(newfn)+len(suffix):
                    newfn = newfn[:(name_max-len(newfn)-len(suffix))]
                newfn = newfn + suffix
                if not os.path.exists(os.path.join(self.archive.get_tmp_dir(),
                                                   outdir, newfn)):
                    outfn = newfn
                    break
                inc += 1

        return os.path.join(outdir, outfn)

    def add_env_var(self, name):
        """Add an environment variable to the list of to-be-collected env vars.

        Collected environment variables will be saved to an `environment` file
        in the archive root, and any variable specified for collection will be
        collected in lowercase, uppercase, and the form provided

        :param name: The name of the environment variable to collect
        :type name: ``str``
        """
        if not isinstance(name, list):
            name = [name]
        for env in name:
            # get both upper and lower cased vars since a common support issue
            # is setting the env vars to the wrong case, and if the plugin
            # adds a mixed case variable name, still get that as well
            self._env_vars.update([env, env.upper(), env.lower()])

    def add_string_as_file(self, content, filename, pred=None, plug_dir=False,
                           tags=[]):
        """Add a string to the archive as a file

        :param content: The string to write to the archive
        :type content: ``str``

        :param filename: The name of the file to write `content` to
        :type filename: ``str``

        :param pred: A predicate to gate if the string should be added to the
                     archive or not
        :type pred: ``SoSPredicate``

        :param plug_dir: Should the string be saved under the plugin's dir in
                         sos_commands/? If false, save to sos_strings/
        :type plug_dir: ``bool``

        :param tags: A tag or set of tags to add to the manifest entry for this
                     collection
        :type tags: ``str`` or a ``list`` of strings
        """

        # Generate summary string for logging
        summary = content.splitlines()[0] if content else ''
        if not isinstance(summary, str):
            summary = content.decode('utf8', 'ignore')

        if not self.test_predicate(cmd=False, pred=pred):
            self._log_info("skipped string ...'%s' due to predicate (%s)" %
                           (summary, self.get_predicate(pred=pred)))
            return

        sos_dir = 'sos_commands' if plug_dir else 'sos_strings'
        filename = os.path.join(sos_dir, self.name(), filename)

        if isinstance(tags, str):
            tags = [tags]

        self.copy_strings.append((content, filename, tags))
        self._log_debug("added string ...'%s' as '%s'" % (summary, filename))

    def _collect_cmd_output(self, cmd, suggest_filename=None,
                            root_symlink=False, timeout=None,
                            stderr=True, chroot=True, runat=None, env=None,
                            binary=False, sizelimit=None, subdir=None,
                            changes=False, foreground=False, tags=[],
                            priority=10, cmd_as_tag=False, to_file=False,
                            container_cmd=False):
        """Execute a command and save the output to a file for inclusion in the
        report.

        Positional Arguments:
            :param cmd:                 The command to run

        Keyword Arguments:
            :param suggest_filename:    Filename to use when writing to the
                                        archive
            :param root_symlink:        Create a symlink in the archive root
            :param timeout:             Time in seconds to allow a cmd to run
            :param stderr:              Write stderr to stdout?
            :param chroot:              Perform chroot before running cmd?
            :param runat:               Run the command from this location,
                                        overriding chroot
            :param env:                 Dict of env vars to set for the cmd
            :param binary:              Is the output in binary?
            :param sizelimit:           Maximum size in MB of output to save
            :param subdir:              Subdir in plugin directory to save to
            :param changes:             Does this cmd potentially make a change
                                        on the system?
            :param foreground:          Run the `cmd` in the foreground with a
                                        TTY
            :param tags:                Add tags in the archive manifest
            :param cmd_as_tag:          Format command string to tag
            :param to_file:             Write output directly to file instead
                                        of saving in memory

        :returns:       dict containing status, output, and filename in the
                        archive for the executed cmd

        """
        if self._timeout_hit:
            return

        if timeout is None:
            timeout = self.cmdtimeout
        _tags = []

        if isinstance(tags, str):
            tags = [tags]

        _tags.extend(tags)
        _tags.append(cmd.split(' ')[0])
        _tags.extend(self.get_tags_for_cmd(cmd))

        if cmd_as_tag:
            _tags.append(re.sub(r"[^\w\.]+", "_", cmd))

        _tags = list(set(_tags))

        _env = self._get_cmd_environment(env)

        if chroot or self.commons['cmdlineopts'].chroot == 'always':
            root = self.sysroot
        else:
            root = None

        if suggest_filename:
            outfn = self._make_command_filename(suggest_filename, subdir)
        else:
            outfn = self._make_command_filename(cmd, subdir)

        outfn_strip = outfn[len(self.commons['cmddir'])+1:]

        if to_file:
            self._log_debug("collecting '%s' output directly to disk"
                            % cmd)
            self.archive.check_path(outfn, P_FILE)
            out_file = os.path.join(self.archive.get_archive_path(), outfn)
        else:
            out_file = False

        start = time()

        result = sos_get_command_output(
            cmd, timeout=timeout, stderr=stderr, chroot=root,
            chdir=runat, env=_env, binary=binary, sizelimit=sizelimit,
            poller=self.check_timeout, foreground=foreground,
            to_file=out_file
        )

        end = time()
        run_time = end - start

        if result['status'] == 124:
            warn = "command '%s' timed out after %ds" % (cmd, timeout)
            self._log_warn(warn)
            if to_file:
                msg = (" - output up until the timeout may be available at "
                       "%s" % outfn)
                self._log_debug("%s%s" % (warn, msg))

        manifest_cmd = {
            'command': cmd.split(' ')[0],
            'parameters': cmd.split(' ')[1:],
            'exec': cmd,
            'filepath': outfn if to_file else None,
            'truncated': result['truncated'],
            'return_code': result['status'],
            'priority': priority,
            'start_time': start,
            'end_time': end,
            'run_time': run_time,
            'tags': _tags
        }

        # command not found or not runnable
        if result['status'] == 126 or result['status'] == 127:
            # automatically retry chroot'ed commands in the host namespace
            if root and root != '/':
                if self.commons['cmdlineopts'].chroot != 'always':
                    self._log_info("command '%s' not found in %s - "
                                   "re-trying in host root"
                                   % (cmd.split()[0], root))
                    result = sos_get_command_output(
                        cmd, timeout=timeout, chroot=False, chdir=runat,
                        env=env, binary=binary, sizelimit=sizelimit,
                        poller=self.check_timeout, to_file=out_file
                    )
                    run_time = time() - start
            self._log_debug("could not run '%s': command not found" % cmd)
            # Exit here if the command was not found in the chroot check above
            # as otherwise we will create a blank file in the archive
            if result['status'] in [126, 127]:
                if self.manifest:
                    self.manifest.commands.append(manifest_cmd)
                    return result

        self._log_debug("collected output of '%s' in %s (changes=%s)"
                        % (cmd.split()[0], run_time, changes))

        if result['truncated']:
            self._log_info("collected output of '%s' was truncated"
                           % cmd.split()[0])
            linkfn = outfn
            outfn = outfn.replace('sos_commands', 'sos_strings') + '.tailed'

        if not to_file:
            if binary:
                self.archive.add_binary(result['output'], outfn)
            else:
                self.archive.add_string(result['output'], outfn)

        if result['truncated']:
            # we need to manually build the relative path from the paths that
            # exist within the build dir to properly drop these symlinks
            _outfn_path = os.path.join(self.archive.get_archive_path(), outfn)
            _link_path = os.path.join(self.archive.get_archive_path(), linkfn)
            rpath = os.path.relpath(_outfn_path, _link_path)
            rpath = rpath.replace('../', '', 1)
            self.archive.add_link(rpath, linkfn)
        if root_symlink:
            self.archive.add_link(outfn, root_symlink)

        # save info for later
        self.executed_commands.append({'cmd': cmd, 'file': outfn_strip,
                                       'binary': 'yes' if binary else 'no'})

        result['filename'] = (
            os.path.join(self.archive.get_archive_path(), outfn) if outfn else
            ''
        )

        if self.manifest:
            manifest_cmd['filepath'] = outfn
            manifest_cmd['run_time'] = run_time
            self.manifest.commands.append(manifest_cmd)
            if container_cmd:
                self._add_container_cmd_to_manifest(manifest_cmd.copy(),
                                                    container_cmd)
        return result

    def collect_cmd_output(self, cmd, suggest_filename=None,
                           root_symlink=False, timeout=None,
                           stderr=True, chroot=True, runat=None, env=None,
                           binary=False, sizelimit=None, pred=None,
                           changes=False, foreground=False, subdir=None,
                           tags=[]):
        """Execute a command and save the output to a file for inclusion in the
        report, then return the results for further use by the plugin

        :param cmd:                 The command to run
        :type cmd: ``str``

        :param suggest_filename:    Filename to use when writing to the
                                    archive
        :param suggest_filename: ``str``

        :param root_symlink:        Create a symlink in the archive root
        :type root_symlink: ``bool``

        :param timeout:             Time in seconds to allow a cmd to run
        :type timeout: ``int``

        :param stderr:              Write stderr to stdout?
        :type stderr: ``bool``

        :param chroot:              Perform chroot before running cmd?
        :type chroot: ``bool``

        :param runat:               Run the command from this location,
                                    overriding chroot
        :type runat: ``str``

        :param env:                 Environment vars to set for the cmd
        :type env: ``dict``

        :param binary:              Is the output in binary?
        :type binary: ``bool``

        :param sizelimit:           Maximum size in MB of output to save
        :type sizelimit: ``int``

        :param subdir:              Subdir in plugin directory to save to
        :type subdir: ``str``

        :param changes:             Does this cmd potentially make a change
                                    on the system?
        :type changes: ``bool``

        :param foreground:          Run the `cmd` in the foreground with a TTY
        :type foreground: ``bool``

        :param tags:                Add tags in the archive manifest
        :type tags: ``str`` or a ``list`` of strings

        :returns:       `cmd` exit status, output, and the filepath within the
                        archive output was saved to
        :rtype: ``dict``
        """
        if not self.test_predicate(cmd=True, pred=pred):
            self.log_skipped_cmd(cmd, pred, changes=changes)
            return {
                'status': None,  # don't match on if result['status'] checks
                'output': '',
                'filename': ''
            }

        return self._collect_cmd_output(
            cmd, suggest_filename=suggest_filename, root_symlink=root_symlink,
            timeout=timeout, stderr=stderr, chroot=chroot, runat=runat,
            env=env, binary=binary, sizelimit=sizelimit, foreground=foreground,
            subdir=subdir, tags=tags
        )

    def exec_cmd(self, cmd, timeout=None, stderr=True, chroot=True,
                 runat=None, env=None, binary=False, pred=None,
                 foreground=False, container=False, quotecmd=False):
        """Execute a command right now and return the output and status, but
        do not save the output within the archive.

        Use this method in a plugin's setup() if command output is needed to
        build subsequent commands added to a report via add_cmd_output().

        :param cmd:                 The command to run
        :type cmd: ``str``

        :param timeout:             Time in seconds to allow a cmd to run
        :type timeout: ``int``

        :param stderr:              Write stderr to stdout?
        :type stderr: ``bool``

        :param chroot:              Perform chroot before running cmd?
        :type chroot: ``bool``

        :param runat:               Run the command from this location,
                                    overriding chroot
        :type runat: ``str``

        :param env:                 Environment vars to set for the cmd
        :type env: ``dict``

        :param binary:              Is the output in binary?
        :type binary: ``bool``

        :param pred:                A predicate to gate execution of the `cmd`
        :type pred: ``SoSPredicate``

        :param foreground:          Run the `cmd` in the foreground with a TTY
        :type foreground: ``bool``

        :param container:           Execute this command in a container with
                                    this name
        :type container: ``str``

        :param quotecmd:            Whether the cmd should be quoted.
        :type quotecmd: ``bool``

        :returns:                   Command exit status and output
        :rtype: ``dict``
        """
        _default = {'status': None, 'output': ''}
        if not self.test_predicate(cmd=True, pred=pred):
            return _default

        if timeout is None:
            timeout = self.cmdtimeout

        if chroot or self.commons['cmdlineopts'].chroot == 'always':
            root = self.sysroot
        else:
            root = None

        _env = self._get_cmd_environment(env)

        if container:
            if self._get_container_runtime() is None:
                self._log_info("Cannot run cmd '%s' in container %s: no "
                               "runtime detected on host." % (cmd, container))
                return _default
            if self.container_exists(container):
                cmd = self.fmt_container_cmd(container, cmd, quotecmd)
            else:
                self._log_info("Cannot run cmd '%s' in container %s: no such "
                               "container is running." % (cmd, container))

        return sos_get_command_output(cmd, timeout=timeout, chroot=root,
                                      chdir=runat, binary=binary, env=_env,
                                      foreground=foreground, stderr=stderr)

    def _add_container_file_to_manifest(self, container, path, arcpath, tags):
        """Adds a file collection to the manifest for a particular container
        and file path.

        :param container:   The name of the container
        :type container:    ``str``

        :param path:        The filename from the container filesystem
        :type path:         ``str``

        :param arcpath:     Where in the archive the file is written to
        :type arcpath:      ``str``

        :param tags:        Metadata tags for this collection
        :type tags:         ``str`` or ``list`` of strings
        """
        if container not in self.manifest.containers:
            self.manifest.containers[container] = {'files': [], 'commands': []}
        self.manifest.containers[container]['files'].append({
            'specification': path,
            'files_copied': arcpath,
            'tags': tags
        })

    def _add_container_cmd_to_manifest(self, manifest, contup):
        """Adds a command collection to the manifest for a particular container
        and creates a symlink to that collection from the relevant
        sos_containers/ location

        :param manifest:    The manifest entry for the command
        :type manifest:     ``dict``

        :param contup:      A tuple of (original_cmd, container_name)
        :type contup:       ``tuple``
        """

        cmd, container = contup
        if container not in self.manifest.containers:
            self.manifest.containers[container] = {'files': [], 'commands': []}
        manifest['exec'] = cmd
        manifest['command'] = cmd.split(' ')[0]
        manifest['parameters'] = cmd.split(' ')[1:]

        _cdir = "sos_containers/%s/sos_commands/%s" % (container, self.name())
        _outloc = "../../../../%s" % manifest['filepath']
        cmdfn = self._mangle_command(cmd)
        conlnk = "%s/%s" % (_cdir, cmdfn)

        self.archive.check_path(conlnk, P_FILE)
        os.symlink(_outloc, self.archive.dest_path(conlnk))

        manifest['filepath'] = conlnk
        self.manifest.containers[container]['commands'].append(manifest)

    def _get_container_runtime(self, runtime=None):
        """Based on policy and request by the plugin, return a usable
        ContainerRuntime if one exists
        """
        if runtime is None:
            if 'default' in self.policy.runtimes.keys():
                return self.policy.runtimes['default']
        else:
            for pol_runtime in list(self.policy.runtimes.keys()):
                if runtime == pol_runtime:
                    return self.policy.runtimes[pol_runtime]
        return None

    def container_exists(self, name):
        """If a container runtime is present, check to see if a container with
        a given name is currently running

        :param name:    The name or ID of the container to check presence of
        :type name: ``str``

        :returns: ``True`` if `name` exists, else ``False``
        :rtype: ``bool``
        """
        _runtime = self._get_container_runtime()
        if _runtime is not None:
            return (_runtime.container_exists(name) or
                    _runtime.get_container_by_name(name) is not None)
        return False

    def get_all_containers_by_regex(self, regex, get_all=False):
        """Get a list of all container names and ID matching a regex

        :param regex:   The regular expression to match
        :type regex:    ``str``

        :param get_all: Return all containers found, even terminated ones
        :type get_all:  ``bool``

        :returns:   All container IDs and names matching ``regex``
        :rtype:     ``list`` of ``tuples`` as (id, name)
        """
        _runtime = self._get_container_runtime()
        if _runtime is not None:
            _containers = _runtime.get_containers(get_all=get_all)
            return [c for c in _containers if re.match(regex, c[1])]
        return []

    def get_container_by_name(self, name):
        """Get the container ID for a specific container

        :param name:    The name of the container
        :type name: ``str``

        :returns: The ID of the container if it exists
        :rtype: ``str`` or ``None``
        """
        _runtime = self._get_container_runtime()
        if _runtime is not None:
            return _runtime.get_container_by_name(name)
        return None

    def get_containers(self, runtime=None, get_all=False):
        """Return a list of all container IDs from the ``Policy``
        ``ContainerRuntime``

        If `runtime` is not provided, use the ``Policy`` default

        :param runtime:     The container runtime to use, if not the default
                            runtime detected and loaded by the ``Policy``
        :type runtime: ``str``

        :param get_all:     Return all containers known to the `runtime`, even
                            those that have terminated
        :type get_all: ``bool``

        :returns: All container IDs found by the ``ContainerRuntime``
        :rtype: ``list``
        """
        _runtime = self._get_container_runtime(runtime=runtime)
        if _runtime is not None:
            if get_all:
                return _runtime.get_containers(get_all=True)
            else:
                return _runtime.containers
        return []

    def get_container_images(self, runtime=None):
        """Return a list of all image names from the Policy's
        ContainerRuntime

        If `runtime` is not provided, use the Policy default. If the specified
        `runtime` is not loaded, return empty.

        :param runtime:     The container runtime to use, if not using the
                            default runtime detected by the ``Policy``
        :type runtime: ``str``

        :returns: A list of container images known to the `runtime`
        :rtype: ``list``
        """
        _runtime = self._get_container_runtime(runtime=runtime)
        if _runtime is not None:
            return _runtime.images
        return []

    def get_container_volumes(self, runtime=None):
        """Return a list of all volume names from the Policy's
        ContainerRuntime

        If `runtime` is not provided, use the Policy default. If the specified
        `runtime` is not loaded, return empty.

        :param runtime:     The container runtime to use, if not using the
                            default runtime detected by the ``Policy``
        :type runtime: ``str``

        :returns: A list of container volumes known to the `runtime`
        :rtype: ``list``
        """
        _runtime = self._get_container_runtime(runtime=runtime)
        if _runtime is not None:
            return _runtime.volumes
        return []

    def add_container_logs(self, containers, get_all=False, **kwargs):
        """Helper to get the ``logs`` output for a given container or list
        of container names and/or regexes.

        Supports passthru of add_cmd_output() options

        :param containers:   The name of the container to retrieve logs from,
                             may be a single name or a regex
        :type containers:    ``str`` or ``list`` of strs

        :param get_all:     Should non-running containers also be queried?
                            Default: False
        :type get_all:      ``bool``

        :param kwargs:      Any kwargs supported by ``add_cmd_output()`` are
                            supported here
        """
        _runtime = self._get_container_runtime()
        if _runtime is not None:
            if isinstance(containers, str):
                containers = [containers]
            for container in containers:
                _cons = self.get_all_containers_by_regex(container, get_all)
                for _con in _cons:
                    cmd = _runtime.get_logs_command(_con[1])
                    self.add_cmd_output(cmd, **kwargs)

    def fmt_container_cmd(self, container, cmd, quotecmd=False):
        """Format a command to be executed by the loaded ``ContainerRuntime``
        in a specified container

        :param container:   The name of the container to execute the `cmd` in
        :type container: ``str``

        :param cmd:         The command to run within the container
        :type cmd: ``str``

        :param quotecmd:    Whether the cmd should be quoted.
        :type quotecmd: ``bool``

        :returns: The command to execute so that the specified `cmd` will run
                  within the `container` and not on the host
        :rtype: ``str``
        """
        if self.container_exists(container):
            _runtime = self._get_container_runtime()
            return _runtime.fmt_container_cmd(container, cmd, quotecmd)
        return ''

    def is_module_loaded(self, module_name):
        """Determine whether specified module is loaded or not

        :param module_name: Name of kernel module to check for presence
        :type module_name: ``str``

        :returns: ``True`` if the module is loaded, else ``False``
        :rtype: ``bool``
        """
        return module_name in self.policy.kernel_mods

    # For adding output
    def add_alert(self, alertstring):
        """Add an alert to the collection of alerts for this plugin. These
        will be displayed in the report

        :param alertstring: The text to add as an alert
        :type alertstring: ``str``
        """
        self.alerts.append(alertstring)

    def add_custom_text(self, text):
        """Append text to the custom text that is included in the report. This
        is freeform and can include html.

        :param text:    The text to include in the report
        :type text:     ``str``
        """
        self.custom_text += text

    def add_service_status(self, services, **kwargs):
        """Collect service status information based on the ``InitSystem`` used

        :param services: Service name(s) to collect statuses for
        :type services: ``str`` or a ``list`` of strings

        :param kwargs:   Optional arguments to pass to add_cmd_output
                         (timeout, predicate, suggest_filename,..)

        """
        if isinstance(services, str):
            services = [services]

        query = self.policy.init_system.query_cmd
        if not query:
            # No policy defined InitSystem, cannot use add_service_status
            self._log_debug('Cannot add service output, policy does not define'
                            ' an InitSystem to use')
            return

        for service in services:
            self.add_cmd_output("%s %s" % (query, service), **kwargs)

    def add_journal(self, units=None, boot=None, since=None, until=None,
                    lines=None, allfields=False, output=None,
                    timeout=None, identifier=None, catalog=None,
                    sizelimit=None, pred=None, tags=None, priority=10):
        """Collect journald logs from one of more units.

        :param units:   Which journald units to collect
        :type units: ``str`` or a ``list`` of strings

        :param boot:    A boot index using the journalctl syntax. The special
                        values 'this' and 'last' are also accepted.
        :type boot: ``str``

        :param since:   Start time for journal messages
        :type since: ``str``

        :param until:   End time forjournal messages
        :type until: ``str``

        :param lines: The maximum number of lines to be collected
        :type lines: ``int``

        :param allfields: Include all journal fields regardless of size or
                          non-printable characters
        :type allfields: ``bool``

        :param output:  Journalctl output control string, for example "verbose"
        :type output: ``str``

        :param timeout: An optional timeout in seconds
        :type timeout: ``int``

        :param identifier: An optional message identifier
        :type identifier: ``str``

        :param catalog: Augment lines with descriptions from the system catalog
        :type catalog: ``bool``

        :param sizelimit: Limit to the size of output returned in MB.
                          Defaults to the value of --log-size.
        :type sizelimit: ``int``
        """
        journal_cmd = "journalctl --no-pager "
        unit_opt = " --unit %s"
        boot_opt = " --boot %s"
        since_opt = " --since '%s'"
        until_opt = " --until %s"
        lines_opt = " --lines %s"
        output_opt = " --output %s"
        identifier_opt = " --identifier %s"
        catalog_opt = " --catalog"

        journal_size = 100
        all_logs = self.get_option("all_logs")
        log_size = sizelimit or self.get_option("log_size")
        log_size = max(log_size, journal_size) if not all_logs else 0
        if sizelimit == 0:
            # allow for specific sizelimit overrides in plugins
            log_size = 0

        if isinstance(units, str):
            units = [units]

        if isinstance(tags, str):
            tags = [tags]
        elif not tags:
            tags = []

        if units:
            for unit in units:
                journal_cmd += unit_opt % unit
                tags.append("journal_%s" % unit)

        if identifier:
            journal_cmd += identifier_opt % identifier

        if catalog:
            journal_cmd += catalog_opt

        if allfields:
            journal_cmd += " --all"

        if boot:
            if boot == "this":
                boot = ""
            if boot == "last":
                boot = "-1"
            journal_cmd += boot_opt % boot

        if since:
            journal_cmd += since_opt % since

        if until:
            journal_cmd += until_opt % until

        if lines:
            journal_cmd += lines_opt % lines

        if output:
            journal_cmd += output_opt % output

        self._log_debug("collecting journal: %s" % journal_cmd)
        self._add_cmd_output(cmd=journal_cmd, timeout=timeout,
                             sizelimit=log_size, pred=pred, tags=tags,
                             priority=priority)

    def _expand_copy_spec(self, copyspec):
        def __expand(paths):
            found_paths = []
            paths = glob.glob(paths)
            for path in paths:
                try:
                    # avoid recursive symlink dirs
                    if self.path_isfile(path) or self.path_islink(path):
                        found_paths.append(path)
                    elif self.path_isdir(path) and self.listdir(path):
                        found_paths.extend(__expand(self.path_join(path, '*')))
                    else:
                        found_paths.append(path)
                except PermissionError:
                    # when running in LXD, we've seen os.access return True for
                    # some /sys or /proc paths yet still get a PermissionError
                    # when calling os.listdir(), so rather than rely on that,
                    # just catch and ignore permissions errors resulting from
                    # security modules like apparmor/selinux
                    # Ref: https://github.com/lxc/lxd/issues/5688
                    pass
            return list(set(found_paths))

        if (os.access(copyspec, os.R_OK) and self.path_isdir(copyspec) and
                self.listdir(copyspec)):
            # the directory exists and is non-empty, recurse through it
            copyspec = self.path_join(copyspec, '*')
        expanded = glob.glob(copyspec, recursive=True)
        recursed_files = []
        for _path in expanded:
            try:
                if self.path_isdir(_path) and self.listdir(_path):
                    # remove the top level dir to avoid duplicate attempts to
                    # copy the dir and its contents
                    expanded.remove(_path)
                    recursed_files.extend(__expand(os.path.join(_path, '*')))
            except PermissionError:
                # same as the above in __expand(), but this time remove the
                # path so we don't hit another PermissionError during the
                # actual copy
                expanded.remove(_path)
        expanded.extend(recursed_files)
        return list(set(expanded))

    def _collect_copy_specs(self):
        for path in sorted(self.copy_paths, reverse=True):
            self._log_info("collecting path '%s'" % path)
            self._do_copy_path(path)
        self.generate_copyspec_tags()

    def _collect_container_copy_specs(self):
        """Copy any requested files from containers here. This is done
        separately from normal file collection as this requires the use of
        a container runtime.

        This method will iterate over self.container_copy_paths which is a set
        of 5-tuples as (container, path, sizelimit, stdout, tags).
        """
        if not self.container_copy_paths:
            return
        rt = self._get_container_runtime()
        if not rt:
            self._log_info("Cannot collect container based files - no runtime "
                           "is present/active.")
            return
        if not rt.check_can_copy():
            self._log_info("Loaded runtime '%s' does not support copying "
                           "files from containers. Skipping collections.")
            return
        for contup in self.container_copy_paths:
            con, path, sizelimit, tailit, tags = contup
            self._log_info("collecting '%s' from container '%s'" % (path, con))

            arcdest = "sos_containers/%s/%s" % (con, path.lstrip('/'))
            self.archive.check_path(arcdest, P_FILE)
            dest = self.archive.dest_path(arcdest)

            cpcmd = rt.get_copy_command(
                con, path, dest, sizelimit=sizelimit if tailit else None
            )
            cpret = self.exec_cmd(cpcmd, timeout=10)

            if cpret['status'] == 0:
                if tailit:
                    # current runtimes convert files sent to stdout to tar
                    # archives, with no way to control that
                    self.archive.add_string(cpret['output'], arcdest)
                self._add_container_file_to_manifest(con, path, arcdest, tags)
            else:
                self._log_info("error copying '%s' from container '%s': %s"
                               % (path, con, cpret['output']))

    def _collect_cmds(self):
        self.collect_cmds.sort(key=lambda x: x.priority)
        for soscmd in self.collect_cmds:
            self._log_debug("unpacked command: " + soscmd.__str__())
            self._log_info("collecting output of '%s'" % soscmd.cmd)
            self._collect_cmd_output(**soscmd.__dict__)

    def _collect_strings(self):
        for string, file_name, tags in self.copy_strings:
            if self._timeout_hit:
                return
            content = ''
            if string:
                content = string.splitlines()[0]
                if not isinstance(content, str):
                    content = content.decode('utf8', 'ignore')
            self._log_info("collecting string ...'%s' as '%s'"
                           % (content, file_name))
            try:
                self.archive.add_string(string, file_name)
                _name = file_name.split('/')[-1].replace('.', '_')
                self.manifest.strings[_name] = {
                    'path': file_name,
                    'tags': tags
                }
            except Exception as e:
                self._log_debug("could not add string '%s': %s"
                                % (file_name, e))

    def collect(self):
        """Collect the data for a plugin."""
        start = time()
        self._collect_copy_specs()
        self._collect_container_copy_specs()
        self._collect_cmds()
        self._collect_strings()
        fields = (self.name(), time() - start)
        self._log_debug("collected plugin '%s' in %s" % fields)

    def get_description(self):
        """This function will return the description for the plugin"""
        try:
            return self.short_desc
        except Exception:
            return "<no description available>"

    def check_enabled(self):
        """This method will be used to verify that a plugin should execute
        given the condition of the underlying environment.

        The default implementation will return True if none of class.files,
        class.packages, nor class.commands is specified. If any of these is
        specified the plugin will check for the existence of any of the
        corresponding paths, packages or commands and return True if any
        are present.

        For SCLPlugin subclasses, it will check whether the plugin can be run
        for any of installed SCLs. If so, it will store names of these SCLs
        on the plugin class in addition to returning True.

        For plugins with more complex enablement checks this method may be
        overridden.

        :returns:   ``True`` if the plugin should be run for this system, else
                    ``False``
        :rtype: ``bool``
        """
        # some files or packages have been specified for this package
        if any([self.files, self.packages, self.commands, self.kernel_mods,
                self.services, self.containers, self.architectures]):
            if isinstance(self.files, str):
                self.files = [self.files]

            if isinstance(self.packages, str):
                self.packages = [self.packages]

            if isinstance(self.commands, str):
                self.commands = [self.commands]

            if isinstance(self.kernel_mods, str):
                self.kernel_mods = [self.kernel_mods]

            if isinstance(self.services, str):
                self.services = [self.services]

            if isinstance(self, SCLPlugin):
                # save SCLs that match files or packages
                type(self)._scls_matched = []
                for scl in self._get_scls():
                    files = [f % {"scl_name": scl} for f in self.files]
                    packages = [p % {"scl_name": scl} for p in self.packages]
                    commands = [c % {"scl_name": scl} for c in self.commands]
                    services = [s % {"scl_name": scl} for s in self.services]
                    if self._check_plugin_triggers(files,
                                                   packages,
                                                   commands,
                                                   services,
                                                   # SCL containers don't exist
                                                   ()):
                        type(self)._scls_matched.append(scl)
                if type(self)._scls_matched:
                    return True

            return self._check_plugin_triggers(self.files,
                                               self.packages,
                                               self.commands,
                                               self.services,
                                               self.containers)

        if isinstance(self, SCLPlugin):
            # if files and packages weren't specified, we take all SCLs
            type(self)._scls_matched = self._get_scls()

        return True

    def _check_plugin_triggers(self, files, packages, commands, services,
                               containers):

        if not any([files, packages, commands, services, containers]):
            # no checks beyond architecture restrictions
            return self.check_is_architecture()

        return ((any(self.path_exists(fname) for fname in files) or
                any(self.is_installed(pkg) for pkg in packages) or
                any(is_executable(cmd, self.sysroot) for cmd in commands) or
                any(self.is_module_loaded(mod) for mod in self.kernel_mods) or
                any(self.is_service(svc) for svc in services) or
                any(self.container_exists(cntr) for cntr in containers)) and
                self.check_is_architecture())

    def check_is_architecture(self):
        """Checks whether or not the system is running on an architecture that
        the plugin allows. If not architecture is set, assume plugin can run
        on all arches.

        :returns:   ``True`` if the host's architecture allows the plugin to
                    run, else ``False``
        :rtype: ``bool``
        """
        if self.architectures is None:
            return True
        regex = '(?:%s)' % '|'.join(self.architectures)
        return re.match(regex, self.policy.get_arch())

    def default_enabled(self):
        """This decides whether a plugin should be automatically loaded or
        only if manually specified in the command line."""
        return True

    def add_default_collections(self):
        """Based on the class attrs defined for plugin enablement, add a
        standardized set of collections before we call the plugin's own setup()
        method.
        """
        # For any service used for enablement checks, collect its current
        # status if it exists
        for service in self.services:
            if self.is_service(service):
                self.add_service_status(service)
                self.add_journal(service)

    def setup(self):
        """Collect the list of files declared by the plugin. This method
        may be overridden to add further copy_specs, forbidden_paths, and
        external programs if required.
        """
        self.add_copy_spec(list(self.files))

    def setup_verify(self):
        if not hasattr(self, "verify_packages") or not self.verify_packages:
            if hasattr(self, "packages") and self.packages:
                # Limit automatic verification to only the named packages
                self.verify_packages = [p + "$" for p in self.packages]
            else:
                return

        pm = self.policy.package_manager
        verify_cmd = pm.build_verify_command(self.verify_packages)
        if verify_cmd:
            self.add_cmd_output(verify_cmd)

    def path_exists(self, path):
        """Helper to call the sos.utilities wrapper that allows the
        corresponding `os` call to account for sysroot

        :param path:        The canonical path for a specific file/directory
        :type path:         ``str``


        :returns:           True if the path exists in sysroot, else False
        :rtype:             ``bool``
        """
        return path_exists(path, self.sysroot)

    def path_isdir(self, path):
        """Helper to call the sos.utilities wrapper that allows the
        corresponding `os` call to account for sysroot

        :param path:        The canonical path for a specific file/directory
        :type path:         ``str``


        :returns:           True if the path is a dir, else False
        :rtype:             ``bool``
        """
        return path_isdir(path, self.sysroot)

    def path_isfile(self, path):
        """Helper to call the sos.utilities wrapper that allows the
        corresponding `os` call to account for sysroot

        :param path:        The canonical path for a specific file/directory
        :type path:         ``str``


        :returns:           True if the path is a file, else False
        :rtype:             ``bool``
        """
        return path_isfile(path, self.sysroot)

    def path_islink(self, path):
        """Helper to call the sos.utilities wrapper that allows the
        corresponding `os` call to account for sysroot

        :param path:        The canonical path for a specific file/directory
        :type path:         ``str``


        :returns:           True if the path is a link, else False
        :rtype:             ``bool``
        """
        return path_islink(path, self.sysroot)

    def listdir(self, path):
        """Helper to call the sos.utilities wrapper that allows the
        corresponding `os` call to account for sysroot

        :param path:        The canonical path for a specific file/directory
        :type path:         ``str``


        :returns:           Contents of path, if it is a directory
        :rtype:             ``list``
        """
        return listdir(path, self.sysroot)

    def path_join(self, path, *p):
        """Helper to call the sos.utilities wrapper that allows the
        corresponding `os` call to account for sysroot

        :param path:    The leading path passed to os.path.join()
        :type path:     ``str``

        :param p:       Following path section(s) to be joined with ``path``,
                        an empty parameter will result in a path that ends with
                        a separator
        :type p:        ``str``
        """
        return path_join(path, *p, sysroot=self.sysroot)

    def postproc(self):
        """Perform any postprocessing. To be replaced by a plugin if required.
        """
        pass

    def check_process_by_name(self, process):
        """Checks if a named process is found in /proc/[0-9]*/cmdline.

        :param process:     The name of the process
        :type process:      ``str``

        :returns: ``True`` if the process exists, else ``False``
        :rtype: ``bool``
        """
        status = False
        cmd_line_glob = "/proc/[0-9]*/cmdline"
        try:
            cmd_line_paths = glob.glob(cmd_line_glob)
            for path in cmd_line_paths:
                f = open(self.path_join(path), 'r')
                cmd_line = f.read().strip()
                if process in cmd_line:
                    status = True
        except IOError:
            return False
        return status

    def get_process_pids(self, process):
        """Get a list of all PIDs that match a specified name

        :param process:     The name of the process the get PIDs for
        :type process:  ``str``

        :returns: A list of PIDs
        :rtype: ``list``
        """
        pids = []
        cmd_line_glob = "/proc/[0-9]*/cmdline"
        cmd_line_paths = glob.glob(cmd_line_glob)
        for path in cmd_line_paths:
            try:
                with open(path, 'r') as f:
                    cmd_line = f.read().strip()
                    if process in cmd_line:
                        pids.append(path.split("/")[2])
            except IOError:
                continue
        return pids

    def get_network_namespaces(self, ns_pattern=None, ns_max=None):
        if ns_max is None and self.commons['cmdlineopts'].namespaces:
            ns_max = self.commons['cmdlineopts'].namespaces
        return self.filter_namespaces(self.commons['namespaces']['network'],
                                      ns_pattern, ns_max)

    def filter_namespaces(self, ns_list, ns_pattern=None, ns_max=None):
        """Filter a list of namespaces by regex pattern or max number of
        namespaces (options originally present in the networking plugin.)
        """
        out_ns = []

        # Regex initialization outside of for loop
        if ns_pattern:
            pattern = (
                '(?:%s$)' % '$|'.join(ns_pattern.split()).replace('*', '.*')
                )
        for ns in ns_list:
            # if ns_pattern defined, skip namespaces not matching the pattern
            if ns_pattern and not bool(re.match(pattern, ns)):
                continue
            out_ns.append(ns)

            # if ns_max is defined at all, break the loop when the limit is
            # reached
            # this allows the use of both '0' and `None` to mean unlimited
            if ns_max:
                if len(out_ns) == ns_max:
                    self._log_warn("Limiting namespace iteration "
                                   "to first %s namespaces found"
                                   % ns_max)
                    break

        return out_ns


class PluginDistroTag():
    """The base tagging class for distro-specific classes used to signify that
    a Plugin is written for that distro.

    Use IndependentPlugin for plugins that are distribution agnostic
    """
    pass


class RedHatPlugin(PluginDistroTag):
    """Tagging class for Red Hat's Linux distributions"""
    pass


class UbuntuPlugin(PluginDistroTag):
    """Tagging class for Ubuntu Linux"""
    pass


class DebianPlugin(PluginDistroTag):
    """Tagging class for Debian Linux"""
    pass


class SuSEPlugin(PluginDistroTag):
    """Tagging class for SuSE Linux distributions"""
    pass


class OpenEulerPlugin(PluginDistroTag):
    """Tagging class for openEuler linux distributions"""
    pass


class CosPlugin(PluginDistroTag):
    """Tagging class for Container-Optimized OS"""
    pass


class IndependentPlugin(PluginDistroTag):
    """Tagging class for plugins that can run on any platform"""
    pass


class ExperimentalPlugin(PluginDistroTag):
    """Tagging class that indicates that this plugin is experimental"""
    pass


class SCLPlugin(RedHatPlugin):
    """Superclass for plugins operating on Software Collections (SCLs).

    Subclasses of this plugin class can specify class.files and class.packages
    using "%(scl_name)s" interpolation. The plugin invoking mechanism will try
    to match these against all found SCLs on the system. SCLs that do match
    class.files or class.packages are then accessible via self.scls_matched
    when the plugin is invoked.

    Additionally, this plugin class provides "add_cmd_output_scl" (run
    a command in context of given SCL), and "add_copy_spec_scl" and
    "add_copy_spec_limit_scl" (copy package from file system of given SCL).

    For example, you can implement a plugin that will list all global npm
    packages in every SCL that contains "npm" package:

    class SCLNpmPlugin(Plugin, SCLPlugin):
        packages = ("%(scl_name)s-npm",)

        def setup(self):
            for scl in self.scls_matched:
                self.add_cmd_output_scl(scl, "npm ls -g --json")
    """

    @property
    def scls_matched(self):
        if not hasattr(type(self), '_scls_matched'):
            type(self)._scls_matched = []
        return type(self)._scls_matched

    def _get_scls(self):
        output = sos_get_command_output("scl -l")["output"]
        return [scl.strip() for scl in output.splitlines()]

    def convert_cmd_scl(self, scl, cmd):
        """wrapping command in "scl enable" call
        """
        scl_cmd = "scl enable %s \"%s\"" % (scl, cmd)
        return scl_cmd

    def add_cmd_output_scl(self, scl, cmds, **kwargs):
        """Same as add_cmd_output, except that it wraps command in
        "scl enable" call and sets proper PATH.
        """
        if scl not in self.scls_matched:
            return
        if isinstance(cmds, str):
            cmds = [cmds]
        scl_cmds = []
        for cmd in cmds:
            scl_cmds.append(self.convert_cmd_scl(scl, cmd))
        self.add_cmd_output(scl_cmds, **kwargs)

    # config files for Software Collections are under /etc/${prefix}/${scl} and
    # var files are under /var/${prefix}/${scl} where the ${prefix} is distro
    # specific path. So we need to insert the paths after the appropriate root
    # dir.
    def convert_copyspec_scl(self, scl, copyspec):
        scl_prefix = self.policy.get_default_scl_prefix()
        for rootdir in ['etc', 'var']:
            p = re.compile('^/%s/' % rootdir)
            copyspec = os.path.abspath(p.sub('/%s/%s/%s/' %
                                       (rootdir, scl_prefix, scl),
                                       copyspec))
        return copyspec

    def add_copy_spec_scl(self, scl, copyspecs):
        """Same as add_copy_spec, except that it prepends path to SCL root
        to "copyspecs".
        """
        if scl not in self.scls_matched:
            return
        if isinstance(copyspecs, str):
            copyspecs = [copyspecs]
        scl_copyspecs = []
        for copyspec in copyspecs:
            scl_copyspecs.append(self.convert_copyspec_scl(scl, copyspec))
        self.add_copy_spec(scl_copyspecs)


def import_plugin(name, superclasses=None):
    """Import name as a module and return a list of all classes defined in that
    module. superclasses should be a tuple of valid superclasses to import,
    this defaults to (Plugin,).
    """
    plugin_fqname = "sos.report.plugins.%s" % name
    if not superclasses:
        superclasses = (Plugin,)
    return import_module(plugin_fqname, superclasses)

# vim: set et ts=4 sw=4 :
