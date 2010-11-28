#!/usr/bin/env python

import unittest
import pexpect

from re import search, escape
from os import kill
from signal import SIGINT, SIGUSR1

class WorkerTests(unittest.TestCase):

    __exec_echo_lol_output__ = '0\r\n4\r\nlol\r\n\r\n0\r\n\r\n'

    def prompt(self, n):
        return ('#%i#\r\n' % n)

    def setUp(self):
        self.worker = pexpect.spawn('python ../worker/worker.py')
        # worker should always be very fast to span
        self.expect(self.prompt(0))

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
        self.expect(self.prompt(0))
        self.sendlines(['glob'])
        self.sig(SIGINT)
        self.expect(self.prompt(0))


    def test_basic_noop(self):
        self.sendlines(['noop'])
        self.expect(self.prompt(1))
        self.test_exit()
    
    def test_basic_ping(self):
        self.sendlines(['ping'])
        self.expect('ALIVE\r\n' + self.prompt(1))
        self.test_exit()

    def test_basic_glob(self):
        self.sendlines(['glob', '/*bin'])
        self.expect('2\r\n(/bin\r\n/sbin|/sbin\r\n/bin)\r\n'+self.prompt(1))
        self.test_exit()

    def test_empty_glob(self):
        self.sendlines(['glob', '/?kyzh?'])
        self.expect('0\r\n'+self.prompt(1))
        self.test_exit()

    def test_increasing_counter(self):
        for req_counter in range(1, 5):
            self.sendlines(['noop'])
            self.expect(self.prompt(req_counter))
        for req_counter in range(5, 10):
            self.sendlines(['ping'])
            self.expect('ALIVE\r\n'+self.prompt(req_counter))
        self.test_exit()

    def test_queuecommands(self):
        self.worker.send('ping\n'*5)
        self.worker.send('exec\necho lol\n'*5)
        for req_counter in range(1,6):
            self.lose_expect('ALIVE\r\n'+self.prompt(req_counter))
        for req_counter in range(6,11):
            self.lose_expect(self.__exec_echo_lol_output__+self.prompt(req_counter))
        self.test_exit()

if __name__ == '__main__':
    unittest.main()
