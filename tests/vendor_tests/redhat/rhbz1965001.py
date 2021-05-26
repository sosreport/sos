# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


import tempfile
import shutil
from sos_tests import StageOneReportTest


class rhbz1965001(StageOneReportTest):
    """
    Copying /proc/sys/vm/{compact_memory,drop_caches} must ignore SELinux
    context, otherwise an attempt to set the context to files under some
    directories like /tmp raises an AVC denial, and an ERROR
    "Unable to add '...' to archive: [Errno 13] Permission denied: '...'
    is raise.

    https://bugzilla.redhat.com/show_bug.cgi?id=1965001

    :avocado: enable
    :avocado: tags=stageone
    """

    sos_cmd = '-o system'
    # it is crucial to run the test case with --tmp-dir=/tmp/... as that is
    # (an example of) directory exhibiting the relabel permission deny.
    # /var/tmp directory allows those relabels.
    #
    # the directory shouldn't exist at this moment, otherwise
    # "check to prevent multiple setUp() runs" in sos_tests.py would fail
    _tmpdir = '/tmp/rhbz1965001_avocado_test'

    def test_no_permission_denied(self):
        self.assertSosLogNotContains("Permission denied")
