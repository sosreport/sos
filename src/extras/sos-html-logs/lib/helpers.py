#!/usr/bin/env python

def ksort(d, func = None):
    keys = d.keys()
    keys.sort(func)
    return keys

class Memoize:
   """Memoize(fn) - an instance which acts like fn but memoizes its arguments
      Will only work on functions with non-mutable arguments
   """
   def __init__(self, fn):
      self.fn = fn
      self.memo = {}
   def __call__(self, *args):
      if not self.memo.has_key(args):
         self.memo[args] = self.fn(*args)
      return self.memo[args]

class SQL:
   def  __init__(self):
      self.dbcon = sqlite.connect(":memory:", check_same_thread=False)
      self.dbcur = self.dbcon.cursor()

      self.dbcon.execute("create table events(date, host, position, message, css_style)")

   def execute(self, query):
      return self.dbcon.execute(query)

def color_gradient(src, dst, percent):
   csrc = [ col for col in src ]
   cdst = [ col for col in dst ]
   toret = []

   for inc in range(0,3):
     toret.append(csrc[inc] + ((cdst[inc] - csrc[inc]) * percent / 100))

   return toret

def rgb_to_hex(rgb):
   return "%X%X%X" % (rgb[0], rgb[1], rgb[2])
