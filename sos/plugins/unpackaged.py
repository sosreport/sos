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

import os

from sos.plugins import Plugin, RedHatPlugin


class Unpackaged(Plugin, RedHatPlugin):
    '''
    Collects a list of files that are not handled by the package
    manager
    '''

    def setup(self):

        def get_env_path_list():
            """
            It returns a list of directories contained in the $PATH var
            """
            return os.environ['PATH'].split(':')

        def all_files_system(path, exclude=None):
            """
            path: string
            exclude: list

            It returns a list of all files installed on a system.
            It excludes all the files in the directories listed in 'exclude'
            """
            file_list = []

            for root, dirs, files in os.walk(path, topdown=True):
                if exclude:
                    dirs[:] = [d for d in dirs if dirs not in exclude]
                for name in files:
                    file_list.append(os.path.join(root, name))
                for name in dirs:
                    file_list.append(os.path.join(root, name))

            return file_list

        def format_output(files):
            """
            files: list

            It returns a better formatted string in case we have symlinks
            """
            expanded = []
            for f in files:
                if os.path.islink(f):
                    expanded.append("{} -> {}".format(f, os.readlink(f)))
                else:
                    expanded.append(f)
            return expanded

        all_fsystem = []
        all_frpm = set(self.policy().mangle_package_path(
                       self.policy().package_manager.files))
        for d in get_env_path_list():
            all_fsystem += all_files_system(d)
        not_packaged = [x for x in all_fsystem if x not in all_frpm]
        not_packaged_expanded = format_output(not_packaged)
        self.add_string_as_file('\n'.join(not_packaged_expanded), 'unpackaged')
