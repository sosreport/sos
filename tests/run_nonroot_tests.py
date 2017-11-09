#!/usr/bin/python3
import unittest
import tempfile
import shutil
import gettext
from sos import sosreport
from mock import patch


class SosRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.workdir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.workdir)

    def _get_sos_version(self):
        '''
        Get the main sosreport version from sos.spec.
        This is how make updateversion sets the value
        in sos/__init__.py
        '''
        with open('sos.spec') as spec:
            lines = spec.readlines()
        for line in lines:
            if line.startswith('Version:'):
                break
        return line.strip('Version: ').strip()

    @patch('sos.sosreport.logging')
    def test_run_sosreport_nonroot(self, soserr):
        # Use --quiet so the sosreport run doesn't botch test output
        sosreport.main(['--batch', '--tmp-dir', '%s' % self.workdir,
                        '--config-file', './sos.conf', '--quiet'])
        # gettext call required to avoid error when $LANGUAGE is localised
        soserr.getLogger().error.assert_called_once_with(
                gettext.dgettext('sos', 'no valid plugins were enabled'))


if __name__ == "__main__":
    unittest.main(verbosity=0)

# vim: et ts=4 sw=4
