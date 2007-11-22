import ConfigParser, re
import soshtmllogs.parsers_base as parsers_base

class simple_Parser(parsers_base.base_Parser_class):

   def initialize(self):
      self.config = ConfigParser.ConfigParser()
      self.config.readfp(open('/usr/lib/python2.4/site-packages/soshtmllogs/parsers/simple_parser.rules'))

   def parse_line(self, date, log):

      for section in self.config.sections():
         match = False

         if self.config.has_option(section, "find"):
            if log.line.find(self.config.get(section, "find")) >= 0:
               match = True
         elif self.config.has_option(section, "regex"):
            if re.match(self.config.get(section, "regex"), log.line):
               match = True

         if not match:
            continue

         self.add_event(log, section, "color:green; background-color:yellow; font-size:larger")

         return

      return None
