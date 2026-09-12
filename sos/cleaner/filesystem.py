# This file is part of the sos project: https://github.com/sosreport/sos

"""Small helpers for removing private sanitizer temporary trees."""

import os
import shutil


def remove_private_tree(path):
    """Remove a private tree even when archive modes are not writable."""
    if os.path.islink(path) or not os.path.isdir(path):
        os.unlink(path)
        return

    # These paths are sanitizer-owned temporary data.  Make directories
    # traversable/writable only immediately before removal; this does not
    # alter any published report or extracted tree returned to callers.
    os.chmod(path, 0o700)
    for root, directories, files in os.walk(path, followlinks=False):
        for name in directories:
            child = os.path.join(root, name)
            if not os.path.islink(child):
                os.chmod(child, 0o700)
        for name in files:
            child = os.path.join(root, name)
            if not os.path.islink(child):
                os.chmod(child, 0o600)
    shutil.rmtree(path)
