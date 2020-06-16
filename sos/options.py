# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from argparse import Action
from configparser import ConfigParser, ParsingError, Error


def _is_seq(val):
    """Return true if val is an instance of a known sequence type.
    """
    val_type = type(val)
    return val_type is list or val_type is tuple


class SoSOptions():

    def _merge_opt(self, opt, src, is_default):
        def _unset(val):
            return (val == "" or val is None)

        if hasattr(src, opt):
            newvalue = getattr(src, opt)
            oldvalue = getattr(self, opt)
            # overwrite value iff:
            # - we replace unset option by a real value
            # - new default is set, or
            # - non-sequential variable keeps its default value
            if (_unset(oldvalue) and not _unset(newvalue)) or \
               is_default or \
               ((opt not in self._nondefault) and (not _is_seq(newvalue))):
                # Overwrite atomic values
                setattr(self, opt, newvalue)
                if is_default:
                    self._nondefault.discard(opt)
                else:
                    self._nondefault.add(opt)
            elif _is_seq(newvalue):
                # Concatenate sequence types
                setattr(self, opt, newvalue + oldvalue)

    def _merge_opts(self, src, is_default):
        if not isinstance(src, dict):
            src = vars(src)
        for arg in self.arg_names:
            self._merge_opt(arg, src, is_default)

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
            vals = ["'%s'" % v if isinstance(v, str) else v for v in vals]

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
        for arg in kwargs.keys():
            self.arg_names.append(arg)
            setattr(self, arg, kwargs[arg])

    @classmethod
    def from_args(cls, args):
        """Initialise a new SoSOptions object from a ``Namespace``
            obtained by parsing command line arguments.

            :param args: parsed command line arguments
            :returns: an initialised SoSOptions object
            :returntype: SoSOptions
        """
        opts = SoSOptions(**vars(args))
        opts._merge_opts(args, True)
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
            return ["--%s" % opt]
        if opt in count:
            return ["--%s" % opt for d in range(0, int(val))]
        return ["--" + opt + "=" + val]

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
        if isinstance(self.arg_defaults[key], bool):
            _val = val.lower()
            if _val in ['true', 'on', 'yes']:
                return True
            elif _val in ['false', 'off', 'no']:
                return False
            else:
                raise Exception(
                    "Value of '%s' in %s must be True or False or analagous"
                    % (key, conf))
        if isinstance(self.arg_defaults[key], int):
            try:
                return int(val)
            except ValueError:
                raise Exception("Value of '%s' in %s must be integer"
                                % (key, conf))
        return val

    def update_from_conf(self, config_file):
        config = ConfigParser()
        try:
            try:
                with open(config_file) as f:
                    config.readfp(f)
            except (ParsingError, Error) as e:
                raise exit('Failed to parse configuration file %s'
                           % config_file)
        except (OSError, IOError) as e:
            raise exit('Unable to read configuration file %s : %s'
                       % (config_file, e.args[1]))

        if config.has_section("general"):
            odict = dict(config.items("general"))
            # handle verbose explicitly
            if 'verbose' in odict.keys():
                odict['verbosity'] = int(odict.pop('verbose'))
            # convert options names
            for key in odict.keys():
                if '-' in key:
                    odict[key.replace('-', '_')] = odict.pop(key)
            # set the values according to the config file
            for key, val in odict.items():
                if key not in self.arg_defaults:
                    # read an option that is not loaded by the current
                    # SoSComponent
                    continue
                val = self._convert_to_type(key, val, config_file)
                setattr(self, key, val)

        # report specific checks

        if hasattr(self, 'noplugins'):
            if config.has_option("plugins", "disable"):
                self.noplugins.extend([
                    plugin.strip() for plugin in
                    config.get("plugins", "disable").split(',')
                ])

        if hasattr(self, 'enableplugins'):
            if config.has_option("plugins", "enable"):
                self.enableplugins.extend([
                    plugin.strip() for plugin in
                    config.get("plugins", "enable").split(',')
                ])

        if hasattr(self, 'plugopts'):
            if config.has_section("tunables"):
                for opt, val in config.items("tunables"):
                    if not opt.split('.')[0] in opts.noplugins:
                        self.plugopts.append(opt + "=" + val)

    def merge(self, src, skip_default=True):
        """Merge another set of ``SoSOptions`` into this object.

            Merge two ``SoSOptions`` objects by setting unset or default
            values to their value in the ``src`` object.

            :param src: the ``SoSOptions`` object to copy from
            :param is_default: ``True`` if new default values are to be set.
        """
        for arg in self.arg_names:
            if not hasattr(src, arg):
                continue
            if getattr(src, arg) is not None or not skip_default:
                self._merge_opt(arg, src, False)

    def dict(self):
        """Return this ``SoSOptions`` option values as a dictionary of
            argument name to value mappings.

            :returns: a name:value dictionary of option values.
        """
        odict = {}
        for arg in self.arg_names:
            value = getattr(self, arg)
            # Do not attempt to store preset option values in presets
            if arg in ('add_preset', 'del_preset', 'desc', 'note'):
                value = None
            odict[arg] = value
        return odict

    def to_args(self):
        """Return command arguments for this object.

            Return a list of the non-default options of this ``SoSOptions``
            object in ``sosreport`` command line argument notation:

                ``["--all-logs", "-vvv"]``

        """
        def has_value(name, value):
            """ Test for non-null option values.
            """
            null_values = ("False", "None", "[]", '""', "''", "0")
            if not value or value in null_values:
                return False
            if name in self.arg_defaults:
                if str(value) == str(self.arg_defaults[name]):
                    return False
            return True

        def filter_opt(name, value):
            """ Filter out preset and null-valued options.
            """
            if name in ("add_preset", "del_preset", "desc", "note"):
                return False
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
                opt = "%s %s" % (name, value)
            else:
                opt = name

            arg = "--" + opt if len(opt) > 1 else "-" + opt
            return arg

        opt_items = sorted(self.dict().items(), key=lambda x: x[0])
        return [argify(n, v) for (n, v) in opt_items if filter_opt(n, v)]


class SosListOption(Action):

    """Allow to specify comma delimited list of plugins"""

    def __call__(self, parser, namespace, values, option_string=None):
        items = [opt for opt in values.split(',')]
        if getattr(namespace, self.dest):
            items += getattr(namespace, self.dest)
        setattr(namespace, self.dest, items)
