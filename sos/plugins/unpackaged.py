# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

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
                    file_list.append(path)
                for name in dirs:
                    file_list.append(os.path.join(root, name))

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

        all_fsystem = []
        all_frpm = set(self.policy.mangle_package_path(
                       self.policy.package_manager.files))

        for d in get_env_path_list():
            all_fsystem += all_files_system(d)
        not_packaged = [x for x in all_fsystem if x not in all_frpm]
        not_packaged_expanded = format_output(not_packaged)
        self.add_string_as_file('\n'.join(not_packaged_expanded), 'unpackaged')

# vim: set et ts=4 sw=4 :
