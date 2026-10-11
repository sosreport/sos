# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

"""
Value providers used by sos shell completion. Each provider is given the text
currently being completed and returns either a list of candidate values, or
one of the ``FILES``, ``DIRS`` or ``HOSTS`` directives that instruct the shell
to perform its own completion for that text.

Providers must be cheap enough to run on every keypress of the completion key,
and must never require root privileges or execute external commands.
"""

import json
import os

from pathlib import Path

from sos.utilities import ImporterHelper, import_module

FILES = 'files'
DIRS = 'dirs'
HOSTS = 'hosts'

BOOL_VALUES = ['true', 'false']


def _modules_in(package):
    return ImporterHelper(package).get_modules()


def _import_classes(package, superclass):
    """Yield (module name, class) for each subclass of ``superclass`` defined
    in the modules of ``package``, skipping modules that fail to import.
    """
    for mod in _modules_in(package):
        try:
            classes = import_module(f"{package.__name__}.{mod}",
                                    (superclass,))
        except Exception:
            continue
        for cls in classes:
            yield mod, cls


def _plugins():
    import sos.report.plugins
    return list(_import_classes(sos.report.plugins,
                                sos.report.plugins.Plugin))


def plugin_names(_text):
    return sorted({cls.name() for _, cls in _plugins()})


def plugin_options(text):
    """Complete ``plugin.option[=value]`` for the -k option of report"""
    import sos.report.plugins
    plugins = _plugins()
    if '.' not in text:
        return [f"{name}." for name in {cls.name() for _, cls in plugins}]
    plugname = text.split('.', 1)[0]
    # pylint: disable=no-value-for-parameter
    opts = dict(sos.report.plugins.Plugin.get_default_plugin_opts())
    for _, cls in plugins:
        if cls.name() == plugname:
            for opt in cls.option_list:
                opts[opt.name] = opt
    if '=' in text:
        optname = text.split('.', 1)[1].split('=', 1)[0]
        if optname in opts and bool in opts[optname].val_type:
            return [f"{plugname}.{optname}={v}" for v in BOOL_VALUES]
        return []
    return [f"{plugname}.{opt}" for opt in opts]


def profiles(_text):
    _profiles = set()
    for _, cls in _plugins():
        _profiles.update(cls.profiles)
    return sorted(_profiles)


def presets(_text):
    """Return the generic presets, the presets of the local policy, and any
    user-defined presets stored on disk.
    """
    from sos.policies import find_policy_class
    from sos.presets import GENERIC_PRESETS
    policy = find_policy_class()
    _presets = set(GENERIC_PRESETS) | set(policy.vendor_presets)
    try:
        fnames = os.listdir(policy.presets_path)
    except OSError:
        # no user-defined presets have been saved
        fnames = []
    for fname in fnames:
        try:
            with open(os.path.join(policy.presets_path, fname),
                      encoding='utf-8') as pfile:
                _presets.update(json.load(pfile).keys())
        except (OSError, ValueError, AttributeError):
            # skip unreadable or malformed files, as Policy.load_presets() does
            continue
    _presets.discard('')
    return sorted(_presets)


def _clusters():
    try:
        import sos.collector.clusters
    except ImportError:
        return []
    return [cls for _, cls in _import_classes(
        sos.collector.clusters, sos.collector.clusters.Cluster)]


def cluster_types(_text):
    return sorted(cls.__name__ for cls in _clusters())


def cluster_options(text):
    """Complete ``cluster.option[=value]`` for the -c option of collect"""
    clusters = {cls.__name__: cls for cls in _clusters()}
    if '.' not in text:
        return [f"{name}." for name in clusters]
    cname = text.split('.', 1)[0]
    if cname not in clusters:
        return []
    opts = {opt[0]: opt[1] for opt in clusters[cname].option_list}
    if '=' in text:
        optname = text.split('.', 1)[1].split('=', 1)[0]
        if isinstance(opts.get(optname), bool):
            return [f"{cname}.{optname}={v}" for v in ('True', 'False')]
        return []
    return [f"{cname}.{opt}" for opt in opts]


def _transports():
    try:
        from sos.collector.sosnode import TRANSPORTS
    except ImportError:
        return {}
    return TRANSPORTS


def transports(_text):
    return sorted(_transports())


def cleaner_parsers(_text):
    import sos.cleaner.parsers
    # mirror how SoSCleaner matches --disable-parsers against class names
    return sorted({cls.__name__[3:-6].lower() for _, cls in
                   _import_classes(sos.cleaner.parsers,
                                   sos.cleaner.parsers.SoSCleanerParser)})


def container_runtimes(_text):
    import sos.policies.runtimes
    runtime = sos.policies.runtimes.ContainerRuntime
    names = {cls.name for _, cls in
             _import_classes(sos.policies.runtimes, runtime)}
    names.discard(runtime.name)
    return ['auto'] + sorted(names)


def chroot_modes(_text):
    return ['auto', 'always', 'never']


def collect_groups(text):
    """Complete host group names saved by --save-group, or a path to a group
    file if the text looks like one.
    """
    if '/' in text:
        return FILES
    from sos.collector import COLLECTOR_CONFIG_DIR
    groups = set()
    for gdir in (os.path.join(Path.home(), '.config/sos/groups.d'),
                 COLLECTOR_CONFIG_DIR):
        try:
            groups.update(os.listdir(gdir))
        except OSError:
            # no groups have been saved to this location
            pass
    return sorted(groups)


def help_topics(text):
    """Complete the topics understood by `sos help`"""
    import sos.report.plugins
    import sos.policies.distros
    from sos.policies import Policy
    topics = ['report', 'report.plugins', 'clean', 'collect',
              'collect.clusters', 'collect.transports', 'policies', 'upload']
    topics.extend(f"report.plugins.{mod}" for mod in
                  _modules_in(sos.report.plugins))
    topics.extend(f"collect.clusters.{c}" for c in cluster_types(text))
    topics.extend(f"collect.transports.{t}" for t in transports(text))
    topics.extend(f"policies.{cls.__name__.lower().replace('policy', '')}"
                  for _, cls in _import_classes(sos.policies.distros, Policy))
    return sorted(set(topics))


def files(_text):
    return FILES


def dirs(_text):
    return DIRS


def hosts(_text):
    return HOSTS


# Map an option's ``dest`` to the provider for its values, and whether the
# values are dot-delimited hierarchies that should be completed one level at a
# time. Options not listed here fall back to their argparse ``choices``.
PROVIDERS = {
    'enable_plugins': (plugin_names, False),
    'skip_plugins': (plugin_names, False),
    'only_plugins': (plugin_names, False),
    'plugopts': (plugin_options, True),
    'profiles': (profiles, False),
    'preset': (presets, False),
    'del_preset': (presets, False),
    'cluster_type': (cluster_types, False),
    'cluster_options': (cluster_options, True),
    'transport': (transports, False),
    'disable_parsers': (cleaner_parsers, False),
    'container_runtime': (container_runtimes, False),
    'chroot': (chroot_modes, False),
    'group': (collect_groups, False),
    'topic': (help_topics, True),
    'config_file': (files, False),
    'keyword_file': (files, False),
    'map_file': (files, False),
    'ssh_key': (files, False),
    'registry_authfile': (files, False),
    'skip_files': (files, False),
    'skip_cleaning_files': (files, False),
    'target': (files, False),
    'upload_file': (files, False),
    'tmp_dir': (dirs, False),
    'sysroot': (dirs, False),
    'pack_dir': (dirs, False),
    'nodes': (hosts, False),
    'primary': (hosts, False),
}

# Options that accept comma-delimited values despite not using SosListOption
COMMA_DELIMITED = ('nodes',)

# vim: set et ts=4 sw=4 :
