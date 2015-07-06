#!/usr/bin/env python

import unittest
import pexpect

from re import search, escape
from os import kill
from signal import SIGINT

class PexpectTest(unittest.TestCase):
    def test_plugins_install(self):
        sos = pexpect.spawn('/usr/sbin/sosreport -l')
        try:
            sos.expect('plugin.*does not install, skipping')
        except pexpect.EOF:
            pass
        else:
            self.fail("a plugin does not install or sosreport is too slow")
        kill(sos.pid, SIGINT)

    def test_batchmode_removes_questions(self):
        sos = pexpect.spawn('/usr/sbin/sosreport --batch')
        grp = sos.expect('send this file to your support representative.', 15)
        self.assertEquals(grp, 0)
        kill(sos.pid, SIGINT)

if __name__ == '__main__':
    unittest.main()

# vim: set et ts=4 sw=4 :
