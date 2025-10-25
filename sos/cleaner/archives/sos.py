# Copyright 2021 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import tarfile

from sos.cleaner.archives import SoSObfuscationArchive


class SoSReportArchive(SoSObfuscationArchive):
    """This is the class representing an sos report, or in other words the
    type the archive the SoS project natively generates
    """

    type_name = 'report'
    description = 'sos report archive'

    @classmethod
    def check_is_type(cls, arc_path):
        try:
            return tarfile.is_tarfile(arc_path) and 'sosreport-' in arc_path
        except Exception:
            return False


class SoSReportDirectory(SoSReportArchive):
    """This is the archive class representing a build directory, or in other
    words what `sos report --clean` will end up using for in-line obfuscation
    """

    type_name = 'report_dir'
    description = 'sos report directory'

    @classmethod
    def check_is_type(cls, arc_path):
        if os.path.isdir(arc_path):
            return 'sos_logs' in os.listdir(arc_path)
        return False


class SoSCollectorArchive(SoSObfuscationArchive):
    """Archive class representing the tarball created by ``sos collect``. It
    will not provide prep files on its own, however it will provide a list
    of SoSReportArchive's which will then be used to prep the parsers
    """

    type_name = 'collect'
    description = 'sos collect tarball'
    is_nested = True

    @classmethod
    def check_is_type(cls, arc_path):
        try:
            return (tarfile.is_tarfile(arc_path) and 'sos-collect' in arc_path)
        except Exception:
            return False

    def get_nested_archives(self):
        self.extract(quiet=True)
        _path = self.extracted_path
        archives = []
        for fname in os.listdir(_path):
            arc_name = os.path.join(_path, fname)
            if 'sosreport-' in fname and tarfile.is_tarfile(arc_name):
                archives.append(SoSReportArchive(arc_name, self.tmpdir,
                                                 self.keep_binary_files,
                                                 self.treat_certificates))
        return archives


class SoSCollectorDirectory(SoSCollectorArchive):
    """The archive class representing the temp directory used by ``sos
    collect`` when ``--clean`` is used during runtime.
    """

    type_name = 'collect_dir'
    description = 'sos collect directory'

    @classmethod
    def check_is_type(cls, arc_path):
        if os.path.isdir(arc_path):
            for fname in os.listdir(arc_path):
                if 'sos-collector-' in fname:
                    return True
        return False

# vim: set et ts=4 sw=4 :
