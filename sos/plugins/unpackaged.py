# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin

import os
import stat


class Unpackaged(Plugin, RedHatPlugin):
    '''
    Collects a list of files that are not handled by the package
    manager
    '''

    def setup(self):

        def get_env_path_list():
            """Return a list of directories in $PATH.
            """
            return os.environ['PATH'].split(':')

        def all_files_system(path, exclude=None):
            """Retrun a list of all files present on the system, excluding
                any directories listed in `exclude`.

            :param path: the starting path
            :param exclude: list of paths to exclude
            """
            file_list = []

            for root, dirs, files in os.walk(path, topdown=True):
                if exclude:
                    for e in exclude:
                        dirs[:] = [d for d in dirs if d not in e]
                for name in files:
                    path = os.path.join(root, name)
                    try:
                        while stat.S_ISLNK(os.lstat(path).st_mode):
                            path = os.path.abspath(os.readlink(path))
                    except Exception:
                        continue
                    file_list.append(os.path.realpath(path))
                for name in dirs:
                    file_list.append(os.path.realpath(
                                     os.path.join(root, name)))

            return file_list

        def format_output(files):
            """Format the unpackaged list as a string.
            """
            expanded = []
            for f in files:
                if os.path.islink(f):
                    expanded.append("{} -> {}".format(f, os.readlink(f)))
                else:
                    expanded.append(f)
            return expanded

        # Check command predicate to avoid costly processing
        if not self.test_predicate(cmd=True):
            return

        all_fsystem = []
        all_frpm = set(os.path.realpath(x)
                       for x in self.policy.mangle_package_path(
                       self.policy.package_manager.files))

        for d in get_env_path_list():
            all_fsystem += all_files_system(d)
        not_packaged = [x for x in all_fsystem if x not in all_frpm]
        not_packaged_expanded = format_output(not_packaged)
        self.add_string_as_file('\n'.join(not_packaged_expanded), 'unpackaged')

# vim: set et ts=4 sw=4 :
