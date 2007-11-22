import time
import soshtmllogs.parsers_base as parsers_base

class crazyclock_Parser(parsers_base.base_Parser_class):

   def initialize(self):
      # in this dict, we store the last date for each host
      self.last_date = {}

   def parse_line(self, date, log):

      if date.date != log.date():
         self.add_event(log, "Time skew (%d seconds in the past)" % int(time.mktime(date.date) - time.mktime(log.date())), "color:purple; background-color:yellow")

      self.last_date[log.parent_host] = log.date()

      return

   def analyse_line(self, log):

      yield """The following line matched the rule:<BR>"""
      yield """<DIV STYLE="margin-top: 10px; padding: 10px 10px 10px 10px; margin-bottom: 10px; background-color: white; border: 1px dotted black;">%s</B></DIV>""" % log.line

      yield "The logged time for this message is before the one for the previous message appearing in the log."
