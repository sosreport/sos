#!/usr/bin/env python

import unittest
import pexpect

class PexpectTest(unittest.TestCase):


    def setUp(self):
        self.worker = pexpect.spawn('python ../worker/worker.py')
        # worker should always be very fast to span
        self.expect('#0#\r\n')

    def sendlines(self, lines):
        for line in lines:
            self.worker.sendline(line)
            self.worker.expect(line+'\r\n')

    def expect(self, v, timeout = 3):
        self.worker.expect(v, timeout)
        self.assertEqual(self.worker.before, "")

    def test_exit(self):
        self.sendlines(['exit'])
        self.expect(pexpect.EOF)

    def test_basic_noop(self):
        self.sendlines(['noop'])
        self.expect('#1#\r\n')
        self.test_exit()
    
    def test_basic_ping(self):
        self.sendlines(['ping'])
        self.expect('ALIVE\r\n#1#\r\n')
        self.test_exit()

    def test_basic_glob(self):
        self.sendlines(['glob', '/*bin'])
        self.expect('2\r\n(/bin\r\n/sbin|/sbin\r\n/bin)\r\n')
        self.test_exit()

if __name__ == '__main__':
    unittest.main()
