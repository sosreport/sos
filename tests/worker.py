#!/usr/bin/env python

import unittest
import pexpect

from re import search, escape
from os import kill
from signal import SIGINT, SIGUSR1

class PexpectTest(unittest.TestCase):

    def setUp(self):
        self.worker = pexpect.spawn('python ../worker/worker.py')
        # worker should always be very fast to span
        self.expect('#0#\r\n')

    def sig(self, sig):
        kill(self.worker.pid, sig)

    def lose_expect(self, v, timeout = 3):
        self.worker.expect(v, timeout)

    def expect(self, v, timeout = 3):
        self.lose_expect(v, timeout)
        self.assertEqual(self.worker.before, '')

    def send(self, text):
        self.worker.send(text)
        self.expect(escape(text))

    def sendlines(self, lines):
        for line in lines:
            self.worker.send(line+'\n')
        for line in lines:
            self.expect(escape(line)+'\r\n')

    def __finishes_ok__(self):
        self.expect(pexpect.EOF)
        self.worker.close()
        self.assertEqual(self.worker.exitstatus, 0)

    def test_exit(self):
        self.sendlines(['exit'])
        self.__finishes_ok__()

    def test_ctrlc_on_cmd_prompt_quits(self):
        self.sig(SIGINT)
        self.expect(pexpect.EOF)
        self.__finishes_ok__()

    def test_ctrlc_when_entering_command_quits(self):
        # "Mon clavier se blo" -- French reference
        self.send('glo')
        self.sig(SIGINT)
        self.expect(pexpect.EOF)

    def test_ctrlc_on_readparms_drops(self):
        self.sendlines(['exec'])
        self.sig(SIGINT)
        self.expect('#0#\r\n')
        self.sendlines(['glob'])
        self.sig(SIGINT)
        self.expect('#0#\r\n')

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
