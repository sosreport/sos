# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


from sos.cleaner.archives import SoSObfuscationArchive

import os
import tarfile


class DataDirArchive(SoSObfuscationArchive):
    """A plain directory on the filesystem that is not directly associated with
    any known or supported collection utility
    """

    type_name = 'data_dir'
    description = 'unassociated directory'

    @classmethod
    def check_is_type(cls, arc_path):
        return os.path.isdir(arc_path)

    def set_archive_root(self):
        return os.path.abspath(self.archive_path)


class TarballArchive(SoSObfuscationArchive):
    """A generic tar archive that is not associated with any known or supported
    collection utility
    """

    type_name = 'tarball'
    description = 'unassociated tarball'

    @classmethod
    def check_is_type(cls, arc_path):
        try:
            return tarfile.is_tarfile(arc_path)
        except Exception:
            return False

    def set_archive_root(self):
        if self.tarobj.firstmember.isdir():
            return self.tarobj.firstmember.name
        return ''
