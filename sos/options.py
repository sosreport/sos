# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from argparse import Action
from configparser import ConfigParser


def _is_seq(val):
    """Return true if val is an instance of a known sequence type.
    """
    val_type = type(val)
    return val_type is list or val_type is tuple


def str_to_bool(val):
    _val = val.lower()
    if _val in ['true', 'on', 'yes']:
        return True
    if _val in ['false', 'off', 'no']:
        return False
    return None


class SoSOptions():

    def _merge_opt(self, opt, src, is_default, prefer_new):
        def _unset(val):
            return (val == "" or val is None)

        if hasattr(src, opt):
            newvalue = getattr(src, opt)
            oldvalue = getattr(self, opt)
            # overwrite value iff:
            # - we replace unset option by a real value
            # - new default is set, or
            # - non-sequential variable keeps its default value
            # pylint: disable=too-many-boolean-expressions
            if (_unset(oldvalue) and not _unset(newvalue)) or \
               is_default or \
               ((opt not in self._nondefault) and (not _is_seq(newvalue))) or \
               prefer_new:
                # Overwrite atomic values
                setattr(self, opt, newvalue)
                if is_default:
                    self._nondefault.discard(opt)
                else:
                    self._nondefault.add(opt)
            elif _is_seq(newvalue):
                # Concatenate sequence types
                setattr(self, opt, newvalue + oldvalue)

    def _merge_opts(self, src, is_default, prefer_new):
        if not isinstance(src, dict):
            src = vars(src)
        for arg in self.arg_names:
            self._merge_opt(arg, src, is_default, prefer_new)

    def __str(self, quote=False, sep=" ", prefix="", suffix=""):
        """Format a SoSOptions object as a human or machine readable string.

            :param quote: quote option values
            :param sep: list separator string
            :param prefix: arbitrary prefix string
            :param suffix: arbitrary suffix string
            :param literal: print values as Python literals
        """
        args = prefix
        arg_fmt = "=%s"
        for arg in self.arg_names:
            args += arg + arg_fmt + sep
        args.strip(sep)

        vals = [getattr(self, arg) for arg in self.arg_names]
        if not quote:
            # Convert Python source notation for sequences into plain strings
            vals = [",".join(v) if _is_seq(v) else v for v in vals]
        else:
            # Only quote strings if quote=False
            vals = [f"'{v}'" if isinstance(v, str) else v for v in vals]

        return (args % tuple(vals)).strip(sep) + suffix

    def __str__(self):
        return self.__str()

    def __repr__(self):
        return self.__str(quote=True, sep=", ", prefix="SoSOptions(",
                          suffix=")")

    def __init__(self, arg_defaults={}, **kwargs):
        """Initialise a new ``SoSOptions`` object from keyword arguments.

            Initialises the new object with values taken from keyword
            arguments matching the names of ``SoSOptions`` attributes.

            A ``ValueError`` is raised is any of the supplied keyword
            arguments does not correspond to a known ``SoSOptions`
            attribute name.

            :param *kwargs: a list of ``SoSOptions`` keyword args.
            :returns: the new ``SoSOptions`` object.
        """
        self.arg_defaults = arg_defaults
        self.arg_names = list(arg_defaults.keys())
        self._nondefault = set()
        # first load the defaults, if supplied
        for arg in self.arg_defaults:
            setattr(self, arg, self.arg_defaults[arg])
        # next, load any kwargs
        for arg, kwarg in kwargs.items():
            self.arg_names.append(arg)
            setattr(self, arg, kwarg)

    @classmethod
    def from_args(cls, args, arg_defaults={}):
        """Initialise a new SoSOptions object from a ``Namespace``
            obtained by parsing command line arguments.

            :param args: parsed command line arguments
            :returns: an initialised SoSOptions object
            :returntype: SoSOptions
        """
        opts = SoSOptions(**vars(args), arg_defaults=arg_defaults)
        opts._merge_opts(args, True, False)
        return opts

    @classmethod
    def _opt_to_args(cls, opt, val):
        """Convert a named option and optional value to command line
            argument notation, correctly handling options that take
            no value or that have special representations (e.g. verify
            and verbose).
        """
        no_value = (
            "alloptions", "allow-system-changes", "all-logs", "batch", "build",
            "debug", "experimental", "list-plugins", "list-presets",
            "list-profiles", "no-report", "no-env-vars", "quiet", "verify"
        )
        count = ("verbose",)
        if opt in no_value:
            return [f"--{opt}"]
        if opt in count:
            return [f"--{opt}" for d in range(0, int(val))]
        return [f"--{opt}={val}"]

    def _convert_to_type(self, key, val, conf):
        """Ensure that the value read from a config file is the proper type
        for consumption by the component, as defined by arg_defaults.

        Params:
            :param key:         The key in arg_defaults we need to match the
                                type of
            :param val:         The value to be converted to a particular type
            :param conf:        File values are being loaded from
        """
        if isinstance(self.arg_defaults[key], type(val)):
            return val
        if isinstance(self.arg_defaults[key], list):
            return list(val.split(','))
        if isinstance(self.arg_defaults[key], bool):
            val = str_to_bool(val)
            if val is None:
                raise Exception(
                    f"Value of '{key}' in {conf} must be True or False or "
                    "analagous")
            return val
        if isinstance(self.arg_defaults[key], int):
            return int(val)
        return val

    def update_from_conf(self, config_file, component):
        """Read the provided config_file and update options from that.

        Positional arguments:

            :param config_file:             Filepath to the config file
            :param component:               Which component (section) to load
        """

        def _update_from_section(section, config):
            if config.has_section(section):
                odict = dict(config.items(section))
                # handle verbose explicitly
                if 'verbose' in odict.keys():
                    odict['verbosity'] = int(odict.pop('verbose'))
                # convert options names
                # unify some of them if multiple variants of the
                # cmdoption exist
                rename_opts = {
                    'name': 'label',
                    'plugin_option': 'plugopts',
                    'profile': 'profiles'
                }
                for key in list(odict):
                    if '-' in key:
                        odict[key.replace('-', '_')] = odict.pop(key)
                    if key in rename_opts:
                        odict[rename_opts[key]] = odict.pop(key)
                # set the values according to the config file
                for key, val in odict.items():
                    # most option values do not tolerate spaces, special
                    # exception however for --keywords which we do want to
                    # support phrases, and thus spaces, for
                    if isinstance(val, str) and key != 'keywords':
                        val = val.replace(' ', '')
                    if key not in self.arg_defaults:
                        # read an option that is not loaded by the current
                        # SoSComponent
                        print(f"Unknown option '{key}' in section '{section}'")
                        continue
                    val = self._convert_to_type(key, val, config_file)
                    setattr(self, key, val)

        config = ConfigParser()
        try:
            with open(config_file, encoding='utf-8') as f:
                config.read_file(f, config_file)
        except OSError as e:
            print(
                f'WARNING: Unable to read configuration file {config_file} : '
                f'{e.args[1]}'
            )

        _update_from_section("global", config)
        _update_from_section(component, config)
        if config.has_section("plugin_options") and hasattr(self, 'plugopts') \
                and hasattr(self, 'skip_plugins'):
            # pylint: disable=no-member
            for key, val in config.items("plugin_options"):
                if not key.split('.')[0] in self.skip_plugins:
                    self.plugopts.append(key + '=' + val)

    def merge(self, src, skip_default=True, prefer_new=False):
        """Merge another set of ``SoSOptions`` into this object.

            Merge two ``SoSOptions`` objects by setting unset or default
            values to their value in the ``src`` object.

            :param src: the ``SoSOptions`` object to copy from
            :param is_default: ``True`` if new default values are to be set.
            :param prefer_new: ``False`` if new default is not preferred.
        """
        for arg in self.arg_names:
            if not hasattr(src, arg):
                continue
            if getattr(src, arg) is not None or not skip_default:
                self._merge_opt(arg, src, False, prefer_new=prefer_new)

    def dict(self, preset_filter=True):
        """Return this ``SoSOptions`` option values as a dictionary of
            argument name to value mappings.

            :returns: a name:value dictionary of option values.
        """
        odict = {}
        for arg in self.arg_names:
            value = getattr(self, arg)
            # Do not attempt to store preset option values in presets
            if preset_filter:
                if arg in ('add_preset', 'del_preset', 'desc', 'note'):
                    value = None
            odict[arg] = value
        return odict

    def to_args(self):
        """Return command arguments for this object.

            Return a list of the non-default options of this ``SoSOptions``
            object in ``sos report`` command line argument notation:

                ``["--all-logs", "-vvv"]``

        """
        def has_value(name, value):
            """ Test for non-null option values.
            """
            null_values = ("False", "None", "[]", '""', "''", "0")
            if not value or value in null_values:
                return False
            if name == 'plugopts' and value:
                return True
            if name in self.arg_defaults:
                if str(value) == str(self.arg_defaults[name]):
                    return False
            return True

        def filter_opt(name, value):
            """ Filter out preset and null-valued options.
            """
            if name in ("add_preset", "del_preset", "desc", "note"):
                return False
            # Exception list for options that still need to be reported when 0
            if name in ['log_size', 'plugin_timeout', 'cmd_timeout'] \
               and value == 0:
                return True
            return has_value(name, value)

        def argify(name, value):
            """ Convert sos option notation to command line arguments.
            """
            # Handle --verbosity specially
            if name.startswith("verbosity"):
                arg = "-" + int(value) * "v"
                return arg

            name = name.replace("_", "-")

            value = ",".join(value) if _is_seq(value) else value

            if value is not True:
                opt = f"{name} {value}"
            else:
                opt = name

            arg = "--" + opt if len(opt) > 1 else "-" + opt
            return arg

        opt_items = sorted(self.dict().items(), key=lambda x: x[0])
        return [argify(n, v) for (n, v) in opt_items if filter_opt(n, v)]


class SosListOption(Action):

    """Allow to specify comma delimited list of plugins"""

    def __call__(self, parser, namespace, values, option_string=None):
        items = list(values.split(','))
        if getattr(namespace, self.dest):
            items += getattr(namespace, self.dest)
        setattr(namespace, self.dest, items)


class ClusterOption():
    """Used to store/manipulate options for cluster profiles."""

    def __init__(self, name, value, opt_type, cluster, description=None):
        self.name = name
        self.value = value
        self.opt_type = opt_type
        self.cluster = cluster
        self.description = description
