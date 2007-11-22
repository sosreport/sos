import re
import soshtmllogs.parsers_base as parsers_base

class dmapper_Parser(parsers_base.base_Parser_class):
   default_css = "color:black; background-color:orange; font-size:larger"

   def initialize(self):
      self.db.execute("create table dmapper(disk PRIMARY KEY, host INTEGER, channel INTEGER, id INTEGER, lun INTEGER)")

   def parse_line(self, date, logline):

      # kernel: sd 1:0:0:49152: Attached scsi disk sdt
      found = re.findall(r"""^sd (.+):(.+):(.+):(.+): Attached scsi disk (.+)$""", logline.message())
      if found:
         # we can learn a little about the layout
         found = found[0]
         self.db.execute("""replace into dmapper(disk,host,channel,id,lun) values ("%s",%d,%d,%d,%d)"""
			    % (found[4], int(found[0]), int(found[1]), int(found[2]), int(found[3]))
			)

      found = re.findall(r"""^Attached scsi disk (.+) at scsi(.+), channel (.+), id (.+), lun (.+)$""", logline.message())
      if found:
         # we can learn a little about the layout
         found = found[0]
         self.db.execute("""replace into dmapper(disk,host,channel,id,lun) values ("%s",%d,%d,%d,%d)"""
			    % (found[0], int(found[1]), int(found[2]), int(found[3]), int(found[4]))
			)

      #Nov  7 12:55:38 itrac415 kernel: SCSI error : <2 0 3 0> return code = 0x20000
      found = re.findall(r"""^SCSI error : <(.+)> return code = (.+)$""", logline.message())
      if found:
         found = found[0]
         scsi_address_split = [ int(sid) for sid in found[0].split(" ") ]
         results = self.db.execute_and_fetch("select disk from dmapper where host = %d AND channel = %d AND id = %d AND lun = %d" %
            (scsi_address_split[0], scsi_address_split[1], scsi_address_split[2], scsi_address_split[3])
         )
         for row in results: found[0] = row["disk"]
         self.add_event(logline, "SCSI error on %s - %s" % (found[0], self._get_did_error(found[1])), self.default_css)
         return

      found = re.findall(r"""^end_request: I/O error, dev (.*), sector .*$""", logline.message())
      if found:
         self.add_event(logline, "I/O error on %s" % (found[0]), self.default_css)
         return

      if logline.daemon() != "multipathd":
         return

      found = re.findall(r"""(.*): mark as failed$""", logline.message())
      if found:
         disk = self._get_disk_from_majmin(found[0])
         self.add_event(logline, "Multipath path %s (%s) failed" % (found[0], disk), self.default_css)
         return

      found = re.findall(r"""(.*): reinstated$""", logline.message())
      if found:
         disk = self._get_disk_from_majmin(found[0])
         self.add_event(logline, "Multipath path %s (%s) reinstated" % (found[0], disk), self.default_css)
         return

      return

   def _get_disk_from_majmin(self, majmin):
      major, minor = majmin.split(":")
      major, minor = int(major), int(minor)

      block_majors = [8, 65, 66, 67, 68, 69, 70, 71, 128, 129, 130, 131, 132, 133, 134, 135]

      disk = (block_majors.index(major) * 16) + int(minor / 16)
      partition = minor % 16

      # 97 = ord('a')
      # 25 = ord('z') - ord('a')

      rchar = chr(97 + (disk % 25))

      if disk > 25:
         lchar = chr(97 - 1 + int(disk / 25))
         rchar = chr(ord(rchar)-1)
      else:
         lchar = ""

      return "sd" + lchar + rchar

   def _get_did_error(self, hexerr):
      # hexherr = 0x20000

      if not hexerr.startswith("0x"):
         return "Unknown error code (%s)" % hexerr

      err = hexerr[2]

      if err == "0": return "DID_OK (NO error)"
      if err == "1": return "DID_NO_CONNECT (Couldn\\'t connect before timeout period)"
      if err == "2": return "DID_BUS_BUSY (BUS stayed busy through time out period)"
      if err == "3": return "DID_TIME_OUT (TIMED OUT for other reason)"
      if err == "4": return "DID_BAD_TARGET (BAD target)"
      if err == "5": return "DID_ABORT (Told to abort for some other reason)"
      if err == "6": return "DID_PARITY (Parity error)"
      if err == "7": return "DID_ERROR (Internal error)"
      if err == "8": return "DID_RESET (Reset by somebody)"
      if err == "9": return "DID_BAD_INTR (Got an interrupt we weren't expecting)"
      if err == "a": return "DID_PASSTHROUGH (Force command past mid-layer)"
      if err == "b": return "DID_SOFT_ERROR (The low level driver just wish a retry)"
      if err == "c": return "DID_IMM_RETRY (Retry without decrementing retry count)"
      if err == "d": return "DID_REQUEUE (Requeue command (no immediate retry) also without decrementing the retry count)"
