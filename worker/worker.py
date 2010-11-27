#!/usr/bin/env python

class Request:
    Commands = {}

    @staticmethod
    def Register(name):
        def decorate(cls):
            Request.Commands[name] = cls
            return cls
        return decorate
    
    @staticmethod
    def ReadCommand(shell):
        cmd = shell.read_line().strip()
        request = Request.Commands[cmd](shell)
        return request

    def __init__(self, shell):
        self.shell = shell

    def read_params(self):
        pass

    def execute(self):
        raise NotImplementedError()


@Request.Register("noop")
class NoopRequest(Request):

    def execute(self):
        pass

@Request.Register("ping")
class PingRequest(Request):

    def execute(self):
        self.shell.status("ALIVE")


@Request.Register("exit")
class ExitRequest(Request):

    def execute(self):
        self.shell.exit()


@Request.Register("glob")
class GlobRequest(Request):

    def read_params(self):
        self.pattern = self.shell.read_line()

    def execute(self):
        from glob import glob
        results = glob(self.pattern)
        self.shell.write(len(results)+"\n")
        for result in results:
            self.shell.write(result+"\n")


@Request.Register("exec")
class ExecRequest(Request):

    def read_params(self):
        self.cmd = self.shell.read_line()

    def execute(self):
        from subprocess import Popen, PIPE
        proc = Popen(self.cmd, shell=True, stdout=PIPE, stderr=PIPE, bufsize=-1)
        stdout, stderr = proc.communicate()
        self.shell.write("%i\n" % proc.returncode)
        self.shell.write_blob(stdout)
        self.shell.write_blob(stderr)

class Shell:
    def __init__(self,
        input_stream  = None,
        output_stream = None,
        status_stream = None,
        bork_action   = None):
        self.__input_stream__  = input_stream
        self.__output_stream__ = output_stream
        self.__status_stream__ = status_stream
        if bork_action:
            self.__bork_action__ = bork_action
        else:
            self.__bork_action__ = self.exit
        self.__exit__ = False
        self.__cmd_number__ = 0

    def loop(self):
        while self.__exit__ == False:
            self.show_prompt()
            try: request = Request.ReadCommand(self)
            except KeyboardInterrupt:
                self.exit()
            except KeyError:
                self.status("UNKNOWN COMMAND");
                self.bork()
            else:
                try: request.read_params()
                except KeyboardInterrupt:
                    pass
                else:
                    self.__cmd_number__ += 1
                    try:
                        request.execute()
                    except KeyboardInterrupt:
                        self.status("INTERRUPTED");

    def exit(self):
        self.__exit__ = True

    def bork(self):
        self.__bork_action__()

    def show_prompt(self):
        self.write("#%i#\n" % self.__cmd_number__)

    def status(self, str):
        print >> self.__status_stream__, str

    def write(self, msg):
        self.__output_stream__.write(msg)

    def write_blob(self, blob):
        self.write("%i\n" % len(blob))
        self.write(str(blob)+"\n")

    def read_line(self):
        while True:
            try:
                return self.__input_stream__.readline().strip()
            except IOError:
                pass

    def read_blob(self, length):
        try:
            blob = self.__input_stream__.read(length)
            assert self.__input_stream__.read(1) == "\n"
        except:
            raise IOError()
        else:
            return blob

if __name__ == "__main__":
    from sys import stdin, stdout, stderr, exit
    from signal import signal, SIGUSR1
    def handler(signum, frame):
        print >> stderr, "ALIVE"
    signal(SIGUSR1, handler)
    def bork():
        exit(-1)
    Shell(input_stream = stdin,
          output_stream = stdout,
          status_stream = stderr,
          bork_action = bork).loop()
