Plugin Options
==============

Plugins can define command line options that allow the user to modify
the plugin’s behaviour. There are also a a set of global command line
options exposed to all plugins.

Running a plugin with options
-----------------------------

To run sos report and pass an option to a plugin use the ``-k``, or
``--plugin-option`` switches:

::

   # sos report -kxfs.logprint

::

   # sos report --plugin-option filesys.lsof

::

   # sos report -kfilesys.lsof,filesys.dumpe2fs

Adding an option to a plugin
----------------------------

Please see the :doc:`How to Write a
Plugin <write_a_plugin#add-plugin-options>`
page for more information on how to add or use plugin options.

Global options
--------------

Global plugin options are normal command line switches that are exposed
for all plugins to use. There are currently a few defined global plugin
options:

-  ``--verify``, causes plugins to perform plugin-specific data
   verification where possible (e.g. package manager verification. May
   greatly increase runtime).
-  ``--all-logs``, causes plugins to attempt to collect all available
   log data (may greatly increase the size of reports).
-  ``--log-size``, specify a limit for per-log file data collection

And several default plugin options assigned for each plugin

-  ``-k $plugin.timeout``, set the timeout for a specific $plugin, in
   seconds.
-  ``-k $plugin.postproc``, If set to false, skip postprocessing wthin
   $plugin. Defaults to True (i.e. do run postprocessing)
-  ``-k $plugin.cmd-timeout``, set the maximum timeout for individual
   command collections within a plugin.

Plugins access these via the same ``get_option()`` method used for
plugin specific options. Any dashes in the option name are replaced with
underscores:

.. code:: python


           limit = self.get_option("log_size")
           self.add_copy_spec_limit("/var/log/foo.log", sizelimit=limit)
           if self.get_option("all_logs"):
               self.add_copy_spec("/var/log/foo.log*")

           if self.get_option("verify"):
               self.add_cmd_output("foo --verify")

See the existing plugins for more examples of plugin options in use:

.. code:: python


    if self.get_option("verify"):
       if self.get_option("rpmva"):
           self.add_cmd_output("rpm -Va", root_symlink = "rpm-Va", timeout = 3600)
       else:
           pkgs_by_regex = self.policy().package_manager.all_pkgs_by_name_regex
           verify_list = map(pkgs_by_regex, self.verify_list)
           verify_pkgs = ""
           for pkg_list in verify_list:
               for pkg in pkg_list:
                   if 'debuginfo' in pkg or 'devel' in pkg:
                       continue
                   verify_pkgs = "%s %s" % (verify_pkgs, pkg)
           self.add_cmd_output("rpm -V %s" % verify_pkgs)
