Measuring command run times
===========================

With debug logging enabled (-vv) sos logs the time taken to run each
command:

::

   2014-06-06 21:53:03,529 DEBUG: [plugin:networking] collected output of 'ip' in 0.014631986618

These can be filtered down and used to aggregate stats by plugin or
command, for e.g.:

::

   $ awk '/collected/{print $4" "$8" "$10}' sosreport-localhost.*/sos_logs/sos.log > /tmp/cmdtimes

Print the top 20 plugins and commands by runtime:

.. code:: python

   #!/usr/bin/python

   def main():
       r = open("/tmp/cmdtimes", "r")
       cmdtimes = {}
       plugtimes = {}
       for line in r.read().splitlines():
           (plugin, cmd, time) = line.split()
           if cmd not in cmdtimes:
               cmdtimes[cmd] = 0.0
           if plugin not in plugtimes:
               plugtimes[plugin] = 0.0
           cmdtimes[cmd] = cmdtimes[cmd] + float(time)
           plugtimes[plugin] = plugtimes[plugin] + float(time)

       print "Plugins:"
       for plug in sorted(plugtimes, key=lambda plug: plugtimes[plug])[-20:]:
           print "%s %fs" % (plug, plugtimes[plug])

       print "Commands:"
       for cmd in sorted(cmdtimes, key=lambda cmd: cmdtimes[cmd])[-20:]:
           print "%s %fs" % (cmd, cmdtimes[cmd])

       r.close()

   if __name__ == '__main__':
       main()

Gives output like:

::

   $ /tmp/soscmds.py 
   Plugins:
   [plugin:pcp] 0.200337s
   [plugin:usb] 0.393647s
   [plugin:sar] 0.456284s
   [plugin:lvm2] 0.487352s
   [plugin:kernel] 0.528694s
   [plugin:systemtap] 0.535331s
   [plugin:smartcard] 0.536921s
   [plugin:general] 0.580074s
   [plugin:firewalld] 0.692489s
   [plugin:networking] 0.727666s
   [plugin:samba] 0.737793s
   [plugin:process] 0.926314s
   [plugin:block] 1.009134s
   [plugin:boot] 1.269422s
   [plugin:tuned] 1.845853s
   [plugin:yum] 3.362885s
   [plugin:grub2] 3.593456s
   [plugin:selinux] 5.527698s
   [plugin:systemd] 34.034044s
   [plugin:rpm] 50.551121s
   Commands:
   'pkcs11_inspect' 0.306482s
   'nmcli' 0.354518s
   'wbinfo' 0.362981s
   'testparm' 0.374812s
   'lsusb' 0.393647s
   'sh' 0.488693s
   'stap' 0.527244s
   'parted' 0.570049s
   'ls' 0.579363s
   'firewall-cmd' 0.692489s
   'ausearch' 0.737173s
   'lsof' 0.796892s
   'lsinitrd' 1.262425s
   'tuned-adm' 1.845853s
   'semodule' 1.916661s
   'semanage' 2.580411s
   'yum' 3.362885s
   'grub2-mkconfig' 3.574695s
   'journalctl' 33.615310s
   'rpm' 50.350750s
