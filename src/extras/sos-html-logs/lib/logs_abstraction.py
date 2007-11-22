#!/usr/bin/env python

import os, sys, time, re, pdb
from threading import Thread, Lock
from helpers import *
from operator import itemgetter
import traceback

class cluster_class:

   def __init__(self):
      self.hosts = {}
      self.index = {}
      self.daemon_log_counter = []
      self.parsers = []

   def host_names(self):
      return ksort(self.hosts)

   def register_parser(self, parser_class):
      self.parsers.append(parser_class)

   def get_parser(self, parser_name):
      for parser in self.parsers:
         if parser.__class__.__name__ == parser_name:
            return parser

   def get_host(self, host):
      return self.hosts[host]

   def tell(self):
      toret = {}
      for host in self.hosts:
         toret[host] = self.hosts[host].tell()
      return toret

   def tell_sum(self):
      toret = 0
      for host in self.hosts:
         toret += self.hosts[host].tell()
      return toret

   def size(self):
      toret = 0
      for host in self.hosts:
         toret += self.hosts[host].size()
      return toret

   def seek(self, positions):
      # make sure positions in argument are valid
      for host in self.hosts:
         if host not in positions.keys():
            print "cannot find", positions
            raise "Invalid_Positions"

      # seek each host to saved position
      for host in positions:
         self.hosts[host].seek(positions[host])

      return True

   def seek_beginning(self):
      for host in self.hosts:
         self.hosts[host].seek(0)

      return True

   def add_log(self, logname):
      log = logfile_class(logname)
      hostname = log.hostname()
      sys.stderr.write("""adding log "%s" for host %s\n""" % (logname, hostname))
      if not self.hosts.has_key(hostname):
         self.hosts[hostname] = host_class()
      self.hosts[hostname].add_log(log)

   def get_position_by_date(self, goto_date):
      try:
         return self.index[goto_date]["position"]
      except KeyError:
         # can't find position in cache, calculate on the fly
         #
         for cmp_date in ksort(self.index):
            if goto_date <= cmp_date:
               return self.index[cmp_date]["position"]
      return None

   def parse(self, threaded = False):

      if threaded and (not hasattr(self,"parse_t") or self.parse_t == None):
         self.parse_t = Thread(target=self.parse, name='parse-thread', args = [True] )
         self.parse_t.start()
         return self.parse_t

      print "parsing begins"

      daemon_log_counter = {}

      self.seek_beginning()

      for date in self:

         self.index[date.date] = { "position":date.position, "log_counter":{} }

         for host in self.hosts:
            self.index[date.date]["log_counter"][host]=0

            try:
               for log in date[host]:
                  self.index[date.date]["log_counter"][host]+=1

                  for parser_class in self.parsers:
                     parser_class.parse_line(date, log)

                  # count how many logs per daemon
                  try:
                     daemon_log_counter[log.daemon()]+=1
                  except KeyError:
                     daemon_log_counter[log.daemon()]=1

            except "Eof":
               # no more logs for this host
               pass

      self.daemon_log_counter = sorted(daemon_log_counter.items(), key=itemgetter(1), reverse=True)

      print "parsing ends."

   def eof(self):
      for host in self.hosts:
         if not self.hosts[host].eof():
#            print "All logs are not EOF yet", host
            return False
      print "All logs are EOF!"
      return True

   def __iter__(self):
      return self

   def next(self):
      if self.eof():
         raise StopIteration

      return log_date_class(cluster = self)

   def instance(self):
      toret = cluster_class()

      for host in self.hosts:
         toret.hosts[host] = host_class()

         for log in self.hosts[host].logs:
            toret.hosts[host].logs.append(logfile_class(log.fname))

      toret.index = self.index
      toret.daemon_log_counter = self.daemon_log_counter
      toret.parsers = self.parsers

      return toret

class log_date_class:
   def __init__(self, cluster):
      self.cluster = cluster
      self.date = None
      self.hosts = cluster.hosts.keys()

      self.position = cluster.tell()

      newtime = None

      # 1st run, must find out what is the oldest date for each host
      for host in self.hosts:
         while True:
            try:
               newtime = time.strptime("2007 " + cluster.hosts[host].readline()[0:15], "%Y %b %d %H:%M:%S")
            except "Eof":
               break
            except ValueError:
               print "parsing error in line", cluster.hosts[host].tell()
            else:
               break

         if newtime:
            if not self.date or newtime < self.date:
               self.date = newtime

         if not cluster.hosts[host].eof():
            cluster.hosts[host].backline()

      # this should almost never happen, but just in case.
      if not self.date:
         raise "Strange_Eof"

   def __str__(self):
      return time.strftime("%b %d %H:%M:%S", self.date)

   def __getitem__(self, host):
      return log_date_host(self.cluster, self.cluster.hosts[host], self.date)

   def __iter__(self):
      return self

class log_date_host:
   def __init__(self, cluster, host, date):
      self.cluster = cluster
      self.host = host
      self.date = date

      self.parent_date = date

   def __iter__(self):
      return self

   def next(self):
      position = self.host.tell()

      self.host.readline()

      try:
         if time.strptime("2007 " + self.host.cur_line[0:15], "%Y %b %d %H:%M:%S") <= self.date:
            return log_line_class(self.parent_date, self.host, position, self.host.cur_line)
      except:
         return log_line_class(self.parent_date, self.host, position, self.host.cur_line)

      self.host.backline()

      raise StopIteration

class log_line_class:
   def __init__(self, date, host, position, line):
      self.host = host
      self.position = position
      self.line = line
      self.parse = Memoize(self.parse_uncached)

      self.parent_date = date
      self.parent_host = host

   def parse_uncached(self):
      try:
         return re.findall(r"""^(... .. ..:..:..) %s ([-_0-9a-zA-Z \.\/\(\)]+)(\[[0-9]+\])?(:)? (.*)$""" % self.hostname(), self.line)[0]
      except:
         return [ None, None, None, None, None ]

   def __str__(self):
      return self.line

   def date(self):
      try:
         return time.strptime("2007 " + self.line[0:15], "%Y %b %d %H:%M:%S")
      except:
         return False

   def hostname(self):
      return self.line[16:].split(" ", 1)[0]

   def daemon(self):
      return self.parse()[1]

   def message(self):
      return self.parse()[4]

class host_class:

   def __init__(self):
      self.logs = []

      self.log_idx = 0 # first log
      self.log_ptr = 0 # first char

      self.cur_line = None

   def __str__(self):
      return self.hostname()

   def add_log(self, logfile):

      for inc in range(0,len(self.logs)):
         if logfile.time_end() < self.logs[inc].time_begin():
            self.logs.insert(inc, logfile)
            break
      else:
         self.logs.append(logfile)

   def hostname(self):
      return self.logs[0].hostname()
#      try:    return self.logs[0].hostname()
#      except: return None

   def tell(self):
      sumsize = 0
      if self.log_idx > 0:
         for inc in range(0, self.log_idx):
            sumsize += self.logs[inc].size()
      try:
         sumsize += self.fp().tell()
      except TypeError:
         pass
      return sumsize

   def size(self):
      sumsize = 0
      for inc in range(0, len(self.logs)):
         sumsize += self.logs[inc].size()
      return sumsize 

   def eof(self):
      if self.tell() >= self.size():
         return True
      return False

   def seek(self, offset, whence = 0):
      if whence == 1:   offset = self.tell() + offset
      elif whence == 2: offset = self.size() + offset

      sumsize = 0
      for inc in range(0, len(self.logs)):
         if offset <= sumsize + self.logs[inc].size():
            offset -= sumsize
            self.log_idx = inc
            self.log_ptr = offset
            self.logs[inc].seek(offset)
            return True
         sumsize += self.logs[inc].size()
      raise "Off_Boundaries"   

   def seek_and_read(self, offset, whence = 0):
      self.seek(offset, whence)
      return self.readline()

   def time(self):
      return time.strptime("2007 " + self.cur_line[0:15], "%Y %b %d %H:%M:%S")

   def fp(self):
      return self.logs[self.log_idx]

   def backline(self):
      self.seek(-len(self.cur_line), 1)

   def readline(self):
      if self.eof():
         raise "Eof"

      while True:
         position = self.fp().tell()
         fromfile = self.fp().fname
         toret = self.fp().readline()
         if len(toret) == 0:
            if self.log_idx < len(self.logs):
               self.log_idx += 1
               self.fp().seek(0)
               continue
            else:
               return ""

         if len(toret) > 0 or toret == "":
            self.cur_line = toret
            self.cur_file = fromfile
            self.cur_pos = position
            return toret
         else:
            print "invalid line", toret

class logfile_class:

   def __init__(self,fname):
      self.fname = fname
      self.fp = open(fname)

   def hostname(self):
      pos = self.fp.tell()
      self.seek(0)
      toret = self.fp.readline()[16:].split(" ")[0]
      self.fp.seek(pos)
      return toret

   def time_begin(self):
      pos = self.fp.tell()
      self.fp.seek(0)
      toret = time.strptime(self.fp.readline()[0:15], "%b %d %H:%M:%S")
      self.fp.seek(pos)
      return toret

   def time_end(self):
      pos = self.fp.tell()
      bs = 1024
      if self.size() < bs: bs = self.size()
      self.fp.seek(-bs, 2)
      buf = self.fp.read(bs)
      bufsplit = buf.split("\n")
      bufsplit.reverse()
      for line in bufsplit:
         if len(line) == 0: continue
         try:  toret = time.strptime(line[0:15], "%b %d %H:%M:%S")
         except ValueError: print "Error in conversion"; continue
         else: break
      self.fp.seek(pos)
      return toret

   def size(self):
      return os.path.getsize(self.fname)

   def eof(self):
      return self.fp.tell() > self.size()

   def readline(self):
      return self.fp.readline()

   def seek(self,pos):
#      if cmdline["verbose"]:
#         print "seeking to position %d for file %s" % (pos, self.fname)
#      traceback.print_stack()
      self.fp.seek(pos)

   def tell(self):
      return self.fp.tell()
