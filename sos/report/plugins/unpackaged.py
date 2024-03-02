# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from pathlib import Path
import os
import stat
from sos.report.plugins import Plugin, RedHatPlugin


class Unpackaged(Plugin, RedHatPlugin):

    short_desc = ('Collects a list of files that are not handled by the '
                  'package manager')
    plugin_name = 'unpackaged'

    def collect(self):

        def get_env_path_list():
            """Return a list of directories in $PATH.
            """
            return os.environ['PATH'].split(':')

        def all_files_system(path, exclude=None):
            """Return a list of all files present on the system, excluding
                any directories listed in `exclude`.

            :param path: the starting path
            :param exclude: list of paths to exclude
            """
            file_list = []

            for root, dirs, files in os.walk(path, topdown=True):
                if exclude:
                    for exc in exclude:
                        dirs[:] = [d for d in dirs if d not in exc]
                for name in files:
                    path = self.path_join(root, name)
                    try:
                        if stat.S_ISLNK(os.lstat(path).st_mode):
                            path = Path(path).resolve()
                    except Exception:  # pylint: disable=broad-except
                        continue
                    file_list.append(
                        [self.path_join(root, name), os.path.realpath(path)]
                    )
                for name in dirs:
                    name = self.path_join(root, name)
                    file_list.append([name, os.path.realpath(name)])

            return file_list

        def format_output(files):
            """Format the unpackaged list as a string.
            """
            expanded = []
            for file in files:
                file = self.path_join(file)
                out = f"{file}"
                links = 0
                # expand links like
                # /usr/bin/jfr -> /etc/alternatives/jfr ->
                # /usr/lib/jvm/java-11-openjdk-11.0.17.0.8-2.el9.x86_64/bin/jfr
                # but stop at level 10 to prevent potential recursive links
                while self.path_islink(file) and links < 10:
                    file = os.readlink(file)
                    out += f" -> {file}"
                    links += 1
                expanded.append(out + '\n')
            return expanded

        # Check command predicate to avoid costly processing
        if not self.test_predicate(cmd=True):
            return

        with self.collection_file('unpackaged') as ufile:
            paths = get_env_path_list()
            all_fsystem = []
            all_frpm = set(
                os.path.realpath(x) for x in self.policy.mangle_package_path(
                    self.policy.package_manager.all_files()
                ) if any(x.startswith(p) for p in paths)
            )

            for path in paths:
                all_fsystem += all_files_system(path)
            not_packaged = [x for [x, rp] in all_fsystem if rp not in all_frpm]
            not_packaged_expanded = format_output(not_packaged)

            ufile.write(''.join(not_packaged_expanded))

# vim: set et ts=4 sw=4 :
