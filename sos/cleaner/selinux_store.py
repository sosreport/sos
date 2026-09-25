# This file is part of the sos project: https://github.com/sosreport/sos

"""Small, path-only classifiers for the SELinux active policy store."""

import re


_PREFIX = ('var', 'lib', 'selinux', 'targeted', 'active', 'modules')
_LEAVES = frozenset(('hll', 'cil', 'lang_ext'))
_PRIORITY = re.compile(r'[1-9][0-9]{0,2}\Z')


def module_artifact(relative):
    """Return the module leaf, or None for a non-module-store path.

    The caller must perform the sibling and object checks.  This function is
    deliberately path-only so it cannot accidentally authorize arbitrary
    files beneath the SELinux store.
    """
    parts = tuple(relative)
    if len(parts) == len(_PREFIX) + 3 and parts[:len(_PREFIX)] == _PREFIX:
        candidate = parts
    elif (len(parts) == len(_PREFIX) + 4 and
          parts[1:1 + len(_PREFIX)] == _PREFIX):
        candidate = parts[1:]
    else:
        return None
    priority, module, leaf = candidate[-3:]
    if (not _PRIORITY.fullmatch(priority) or not module or
            module in ('.', '..') or len(module) > 255 or
            any(ord(char) < 0x20 or char in '/\\' for char in module) or
            leaf not in _LEAVES):
        return False
    return leaf


def active_store_path(relative, filename):
    """Match one exact active-store control file, with one optional root."""
    parts = tuple(relative)
    target = ('var', 'lib', 'selinux', 'targeted', 'active', filename)
    return parts == target or (len(parts) == len(target) + 1 and
                               parts[1:] == target)


def active_store_module_path(relative, leaf=None):
    result = module_artifact(relative)
    return result if leaf is None or result == leaf else None
