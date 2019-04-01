# Copyright (C) 2006 Steve Conklin <sconklin@redhat.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import sys
import shutil
import subprocess

_debug = False

def log(msg):
    print(msg)

def log_debug(msg):
    global _debug
    if _debug:
        print(msg)

class ReleaseError(Exception):
    pass

# Files to update: one tuple per file, first element is path, second
# is the pattern to replace.
files = {
    "sos/__init__.py": '__version__ = "%s"',
    "sos.spec": 'Version: %s'
}

def update_version_in_file(path, old, new):
    new_path = path + ".new"
    with open(new_path, "w") as outf:
        with open(path, "r") as inf:
            for line in inf.read().splitlines():
                line = line.replace(old, new)
                outf.write(line + "\n")
                outf.flush()
    shutil.move(new_path, path)
    log_debug("Updated version strings in %s" % path)

def commit_version_bump(version):
    commit_msg = "[sos] bump release (%s)" % version
    add_cmd = ["git", "add"]
    commit_cmd = ["git", "commit", "-s", "-m", commit_msg]

    log_debug("adding %s to index" % files.keys())
    ret = subprocess.call(add_cmd + files.keys())
    if ret != 0:
        raise ReleaseError("Failed to add version change to index")

    log_debug("committing release bump (%s)" % version)
    ret = subprocess.call(commit_cmd)
    if ret != 0:
        raise ReleaseError("Failed to commit version change")
    log("Committed version string updates")


def tag_head_as_version(version):
    git_cmd = ["git", "tag", "-m sos-%s" % version, "-a"]

    log_debug("Creating annotated tag for %s" % version)
    ret = subprocess.call(git_cmd + [version])
    if ret != 0:
        raise ReleaseError("Failed to create annotated tag sos-%s" % version)
    log_debug("Tagged HEAD as sos-%s" % version)


def push_tags():
    git_cmd = ["git", "push", "--tags"]
    log_debug("Pushing changes to origin")
    ret = subprocess.call(git_cmd)
    if ret != 0:
        raise ReleaseError("Failed to push changes")
    log_debug("Updated remote HEAD")

def main(args):
    version = args[1]
    old_version = args[2] if len(args) > 2 else None

    if not old_version:
        vmaj, vmin = version.split(".")
        minor = int(vmin)
        if minor == 0:
            log("Major release requires <version> <oldversion>")
            return 1
        old_version = "%s.%d" % (vmaj, minor - 1)

    try:
        log("Releasing sos-%s (old_version=%s)" % (version, old_version))
        for path in files.keys():
            print("Updating version in %s" % path)
            update_version_in_file(path, files[path] % old_version,
                                   files[path] % version)
    
        log("Committing version bump")
        commit_version_bump(version)
    
        log("Tagging HEAD as sos-%s" % version)
        tag_head_as_version(version)

        log("Pushing changes to origin")
        push_tags()

    except ReleaseError as re:
        log("Error making release: %s" % re)
        return 1
    except OSError as oe:
        log("OSError making release: %s" % oe)
        return 1

    return 0

if __name__ == "__main__":
    ret = main(sys.argv)
    sys.exit(ret)

