try:    from pysqlite2 import dbapi2 as sqlite
except: print "python-sqlite is missing. Exiting."; sys.exit(1)

from threading import Lock

class myDB_class:
   def __init__(self):
      self.dbcon = sqlite.connect(":memory:", check_same_thread=False)
      self.dbcon.row_factory = sqlite.Row
#      self.dbcur = dbcon.cursor()
      self.dblock = Lock()

      self.execute("create table events(eid INTEGER PRIMARY KEY AUTOINCREMENT, date KEY, host, position, parser, message, css_style, tooltip BLOB)")

   def execute(self, query):
      self.dblock.acquire()
      toret = self.dbcon.execute(query)
      self.dblock.release()
      return toret

   def execute_and_fetch(self, query):
      self.dblock.acquire()
      dbcur = self.dbcon.execute(query)
      toret = dbcur.fetchall()
      self.dblock.release()
      return toret
