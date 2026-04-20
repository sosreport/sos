How to Write a Plugin
=====================

What are SoS plugins?
---------------------

The ``report`` functionality of sos is based on plugins that typically
represent a specific component or product; E.G. the kernel, filesystems,
oVirt, etc…

When ``report`` runs, it will first look to see which plugins exist and
which of those should be enabled. Only plugins that pass an enablement
check for the specific host sos is being run on are executed. A plugin
should capture unique information for the component or product it is
written for (i.e. two plugins should not collect the same data bits).

Where do they go?
-----------------

Plugins live in the ``sos.report.plugins package``. This is the first
place that a proper python package exists on the python path
(e.g. ./sos/report/plugins)

The bare minimum
----------------

Please review the :doc:`Contribution Guidelines <contribution_guidelines>`
first to understand code contribution requirements and the style
guidelines sos has.

Create a generic plugin that runs everywhere.

.. code:: python

   from sos.report.plugins import Plugin, IndependentPlugin

   class Processor(Plugin, IndependentPlugin):
       """
       This plugin will capture information about the physical CPU(s)
       installed on the system.

       Per-CPU information will be gathered from /sys/devices/system/cpu,
       as well as output from commands such as lscpu, cpupower, cpuid, etc.
       """

       short_desc = 'CPU information'

The plugin’s docstring will be used for output along with
``sos help report.plugins.$plugin``. This should be an informative
description of the usecase of the plugin and an overview of what
collections take place. You do not need to detail every collection made
by the plugin.

``short_desc`` will be presented to the user in the output of the
``sos report --list-plugins`` command. This should be a very short
description of the plugin’s usecase.

The ``IndependentPlugin`` subclass is used to enable a plugin for *all*
distributions that sos currently supports. More on this later on.

Let’s copy some stuff
---------------------

In order for a plugin to actually do any work one of the hook methods
must be defined. The ``setup`` method is called during normal collection
on every enabled plugin.

.. code:: python

       def setup(self):
           self.add_copy_spec([
               "/proc/cpuinfo",
               "/sys/devices/system/cpu"
           ])

The above will copy the ``/proc/cpuinfo`` file, but for
``/sys/devices/system/cpu`` it will copy that entire directory.

If you only need to add a single file you can call the ``add_copy_spec``
method with a single string instead.

.. code:: python

       def setup(self):
           self.add_copy_spec("/path/to/something/interesting")

The ``add_copy_spec`` method accepts several optional parameters, that
may affect which files get collected and how many (or how large) files
get copied:

.. code:: python

       def add_copy_spec(self, copyspecs, sizelimit=None, maxage=None,
                         tailit=True, pred=None, tags=[]):

``copyspecs`` whether a single string or a list of strings, accepts
globs to match multiple files on the filesystem. The ``sizelimit``
parameters limits the maximum amount of data that will be copied on a
per-copyspec basis. For example, assuming a 25MB sizelimit, the
following would collect a maximum of 25MB from ``/var/log/messages``
*and* another 25MB from ``/var/log/secure``:

.. code:: python

       def add_copy_spec([
           '/var/log/messages',
           '/var/log/secure'
       ])

If ``sizelimit`` is hit, sos will tail the last X bytes of the file
where X is the set ``sizelimit`` minus any already collected content.

How to prevent collecting passwords?
------------------------------------

To prevent confidential data leak from the system, secrets like
passwords, keys,tokens etc. must be obfuscated. This is done within
``postproc`` method that allows cleaning secrets from collected files
and commands outputs:

.. code:: python

       def postproc(self):
           # from any /etc/tool/*conf files,
           # find patterns like secret: .. or password: ..
           # and replace the value by asterisks
           self.do_path_regex_sub(
               r"/etc/tool/(.*)\.conf$",
               r"((secret|password)\:) (.*)",
               r"\1 ********" 
               )
           # from the output of "command --with argument" (see below section how to collect it),
           # find patterns like pass=.. or password=..
           # and replace the value by asterisks
           self.do_cmd_output_sub(
               "command --with argument",
               r"pass([^\s=]*)=\S+",
               r"pass\1=********"
           )

Obfuscating SSL certificates spanned on multiple lines can be done via
``do_cmd_private_sub`` method.

I want to run a program too
---------------------------

If you wish to collect the output of a program as part of your
collection process call the ``add_cmd_output`` method:

.. code:: python

   from sos.report.plugins import Plugin, IndependentPlugin

   class Processor(Plugin, IndependentPlugin):
       short_desc = 'CPU information'

       def setup(self):
           self.add_cmd_output([
               "lscpu",
               "cpupower info"
           ])
           

Like ``add_copy_spec``, ``add_cmd_output`` accepts either a list of
strings or a single string. Also like ``add_copy_spec``, this method
provides for several optional ways to modify how command output gets
collected and saved:

.. code:: python

       def add_cmd_output(self, cmds, suggest_filename=None,
                          root_symlink=None, timeout=cmd_timeout, stderr=True,
                          chroot=True, runat=None, env=None, binary=False,
                          sizelimit=None, pred=None, subdir=None,
                          changes=False, foreground=False, tags=[]):

Generally speaking, most commands will be called without providing any
of the optional parameters. However, several of the more commonly used
parameters are as follows:

Setting ``suggest_filename`` allows a plugin to override the default
choice of file name in the report archive.

A symbolic link to the collected file from the report’s root directory
can be requested using the ``root_symlink`` parameter.

The ``timeout`` parameter sets a maximum time (in seconds) to wait for
the child process to exit. After this time sos will abandon the child
and continue with report generation.

If the ``stderr`` parameter is ``True`` the stderr stream of the child
process will be captured along with stdout; otherwise stderr is
discarded.

When the ``chroot`` parameter is ``True`` commands are executed in the
configured system root directory (which may not be ``/``). This
parameter has no effect unless sos is running in a chrooted environment.

The ``sizelimit`` parameter limits the amount of output collected, in
MB. The default is 25MB.

A directory may be specified via the ``runat`` program. The child will
switch to this directory before executing the command.

Any parameters provided to the method will be applied to every program
in the list. Note that if using the ``root_symlink`` or
``suggest_filename`` parameter only a single command is supported.

The ``add_cmd_output`` method will execute it’s argument without a shell
using the PATH specified by the active policy. There is normally no need
to specify an absolute path. If you need to use shell syntax this can be
done by calling ``sh -c "<command string>"``.

The output of the command will be added to the report archive under
``sos_commands/plugin_name/mangled_command_name``. Mangling converts
spaces to underscores and removes other characters that are illegal or
problematic in path names.

Additionally, the command will be added to the report index and manifest
automatically.

Attempting to run a command that isn’t installed is not treated as an
error (but errors produced by commands that are found are logged) - it’s
fine to go ahead and speculatively try commands in a plugin without
explicitly checking for their presence.

I want to run a program, then iterate over its results with another program
---------------------------------------------------------------------------

A not-uncommon scenario with plugins is that you want to use output from
one command to determine another set of commands to run. For example,
getting a list of network interfaces and then using that information to
get detailed information on each interface.

The ``podman`` plugin is a great example of this:

.. code:: python

           pnets = self.collect_cmd_output('podman network ls')
           if pnets['status'] == 0:
               nets = [pn.split()[0] for pn in pnets['output'].splitlines()[1:]]
               self.add_cmd_output([
                   "podman network inspect %s" % net for net in nets
               ], subdir='networks')

Here, we call ``collect_cmd_output`` to get a listing of podman
networks. This method will run immediately, save the output to the
archive just like ``add_cmd_output`` does, and also return that output
in a dict.

Once the command has returned, we check to make sure its exit code was
``0``, meaning a successful execution. The command output is accessible
via the ``output`` key for the dict. This then makes it trivial to
iterate over the output, and make successive ``add_cmd_output`` calls
for each network listed.

If you do not want the output to be saved to the archive, and instead
just need to grok the output for actually useful calls, then use
``exec_cmd`` instead of ``collect_cmd_output``.

How can I collect data that is not directly in a file or existing command output?
---------------------------------------------------------------------------------

Traditionally, sos plugins only executed existing commands or collected
existing files from the host. However, the API has recently been
expanded to allow plugin authors to perform “manual” collections - that
is, write data to the report that is not directly the result of a
command’s output, or the contents of an already existing file.

**Note:** this functionality is only available from sos-4.5 and later.

To do these types of collections, plugin authors should define a
``collect()`` method within their plugin. This method will be executed
during plugin collection, *after* collections of files and command
outputs have completed.

In order to write data to the archive, plugins should use the
``Plugin.collection_file()`` method, which will yield an open file
handler within the plugin’s directory within the archive/temporary
directory.

For example, see the ``process`` plugin:

.. code:: python

   import json
   import re

   from sos.report.plugins import Plugin, IndependentPlugin, PluginOpt


   class Process(Plugin, IndependentPlugin):

       short_desc = 'process information'

       plugin_name = 'process'
       profiles = ('system',)

   [...]
       def setup(self):
   [...]

       def collect(self):
           with self.collection_file('pids_to_packages.json') as pfile:
               if not self.policy.package_manager.query_path_command:
                   pfile.write('Package manager not configured for path queries')
                   return
               _ps = self.exec_cmd('ps --no-headers aex')
               pidpkg = {}
               paths = {}
               if not _ps['status'] == 0:
                   pfile.write(f"Unable to get process list: {_ps['output']}")
                   return
               for proc in _ps['output'].splitlines():
                   proc = proc.strip().split()
                   pid = proc[0]
                   path = proc[4]
                   if not self.path_exists(path):
                       continue
                   if path not in paths:
                       paths[path] = self.policy.package_manager.pkg_by_path(path)
                   pidpkg[pid] = {'path': path, 'package': paths[path]}

               pfile.write(json.dumps(pidpkg, indent=4))

Using a ``with`` context manager for managing the collection file is
best practice, as this ensures that the file is always properly closed,
even in the event of a plugin timeout during ``collect()`` execution.
The only **required** argument for this method is the name of the file
you wish to write to.

Within the body of the context manager is where the ``process`` plugin
is generating the data to be written to the
``sos_commands/process/pids_to_process.json``, and finally the data is
written using the standard ``write()`` method.

Note that for any contributions for such “manual” collections, the
``collect()`` method **must** be implemented in pure-python. No bash or
similar shell scripting is allowed. If a collection needs to handle
output from an existing command, but that output should not separately
be recorded in the archive, authors should use the ``Plugin.exec_cmd()``
method to execute the command ad-hoc and get the command’s output, as
seen above.

Dependencies
------------

You can inform sos that your plugin should only run when certain
conditions are met. The default behavior checks for the presence of
files or packages specified in the plugin class. More complex checks can
be implemented by overriding the ``check_enabled`` method of the base
``Plugin`` class.

.. code:: python

   from sos.report.plugins import Plugin, IndependentPlugin

   class Processor(Plugin, IndependentPlugin):
       short_desc = 'CPU information'

       files = ('/proc/cpuinfo',)
       packages = ('cpufreq-utils', 'cpuid')

**Note**: if you use a tuple for ``files`` or ``packages`` be sure that
you place the trailing comma in the case of a 1-tuple.
``('some string')`` does *not* create a 1-tuple, but
``('some string',)`` does.

Apart of ``files`` and ``packages``, a plugin can be enabled also by
``commands`` (“is either of the commands executable?”), ``kernel_mods``
(“is either kernel module loaded?”), ``services`` (“does either of
services exist?”), ``containers`` or ``architecture``.

Be aware that if *any* of the files or packages are found then the
plugin will attempt to run. If you need to ensure that multiple files
are in place or multiple packages are in place then you will want to
implement your own ``check_enabled`` method.

.. code:: python

   from sos.report.plugins import Plugin, RedHatPlugin
   from os.path import exists

   class DepTest(Plugin, RedHatPlugin):
       """This plugin depends on something"""

       def check_enabled(self):
           files = [
               '/path/to/thing/i/need',
               '/path/to/other/thing/i/need'
           ]
           return all(map(exists,files))

       def setup(self):
           self.add_copy_spec([
               "/path/to/something",
               "/path/to/something/else",
           ])

Add plugin options
------------------

Excerpt from the ``podman`` plugin

.. code:: python

   from sos.report.plugins import PluginOpt, Plugin

   class Podman(Plugin):
       option_list = [
           PluginOpt('all', default=False,
                     desc='collect for all containers, even terminated ones'),
           PluginOpt('logs', default=False,
                     desc='collect stdout/stderr logs for containers'),
           PluginOpt('size', default=False,
                     desc='collect image sizes for podman ps')
       ]

       def setup(self):
           ...
           # separately grab ps -s as this can take a *very* long time
           if self.get_option('size'):
               self.add_cmd_output('podman ps -as')

As can be seen above, options are added to plugins via
``PluginOpt(name='undefined', default=None, desc='', long_desc='', val_type=None)``
objects being added to the ``option_list`` class attr. Then, later on
the plugin may use ``self.get_option(name)`` to get the value of that
option - either default or the value passed by
``-k plugin.opt_name=value``.

``desc`` will be the short description printed in ``sos report -l``
output. ``long_desc`` is for the moment unused, but planned to be
referenced by the upcoming ``sos help`` subcommand to provide more
context around plugin options.

Because the argument handling for sos already uses logic around using a
comma (``,``) as a separator for list values, plugin options that can
take a list of values must use a non-comma delimiter. Recently the
preferred approach is to use a colon (``:``) as the delimiter for values
in a list for a plugin option.

Value type handling is handled by the ``PluginOpt`` class. By default,
the type accepted for a given option is determined by the type of the
``default`` value. If you need to override this, or accept multiple
different types, specify those types in a list passed to ``val_type``
when creating the plugin option.

OS Specific Plugins
-------------------

Plugins use a “tagging” class concept for enabling a plugin for specific
OSes/distributions.

As mentioned earlier, if your plugin can be run the exact same on all
supported distributions, import ``IndependentPlugin`` and subclass it in
your plugin.

However, if you need to do different things on different platforms you
need to define one plugin per platform, like so:

.. code:: python

   from sos.plugins import Plugin, RedHatPlugin, DebianPlugin

   class MyRedHatPlugin(Plugin, RedHatPlugin):

       name = "myplugin"

       def setup(self):
          pass # do red hat specific stuff


   class MyDebianPlugin(Plugin, DebianPlugin):
     
       name = "myplugin"

       def setup(self):
           pass # do debian specific stuff

Notice how both plugins have a class-level ``name`` attribute. This
should be the same for all platform-specific implementations of your
plugin. The name attribute determines the name presented to the user for
plugin selection as well as option definition.

In some cases you may wish to share certain bits between
platform-specific plugins, in this case you can make a common shared
superclass:

.. code:: python

   from sos.plugins import Plugin, RedHatPlugin, DebianPlugin

   class MyPlugin(Plugin):

       name = "myplugin"

       def setup(self):
           pass # do common things here


   class MyRedHatPlugin(MyPlugin, RedHatPlugin):

       def setup(self):
          super(MyRedHatPlugin, self).setup()
          pass # do red hat specific stuff


   class MyDebianPlugin(MyPlugin, DebianPlugin):

       def setup(self):
           super(MyDebianPlugin, self).setup()
           pass # do debian specific stuff

Note how the *leaf* classes are still the only ones that subclass things
like ``RedHatPlugin`` and ``DebianPlugin``. This ensures that your
shared plugin class does not get run as a plugin on its own. Note that
for this scheme to work correctly it’s important for the leaf classes to
use appropriate ``super(MySuperClass, self).method()`` calls in order to
properly inherit the generic plugin’s behavior (unless intentionally
overriding an entire method).

*Note: If any of the distributions for your plugin need a separate
distro-specific class, then you cannot use ``IndependentPlugin`` and
must explicitly subclass each distribution your plugin should support*

Gating command or file collection
---------------------------------

There may be times when you want a plugin to only perform a collection
when certain criteria is met. For example, collecting certain
information in the ``networking`` plugin may inadvertently load kernel
modules. SoS is committed to making no changes to the host system during
collection, so we would only want those collections to run if those
kernel modules are already loaded.

For this, SoS uses predicates. Predicates may be passed to either
``add_copy_spec`` or ``add_cmd_output`` via the ``pred=`` kwarg. This
predicate will then be evaluated to either ``True`` or ``False`` before
attempting the collection. If the predicate evaluates ``False``, the
collection is skipped.

Here is an example of a predicate from the ``networking`` plugin:

.. code:: python

   from sos.report.plugins import SoSPredicate

   [...]
       ip_macsec_show_cmd = "ip -s macsec show"
       macsec_pred = SoSPredicate(self, kmods=['macsec'])
       self.add_cmd_output(ip_macsec_show_cmd, pred=macsec_pred, changes=True)

In this example, we define a predicate that requires the ``macsec``
kernel module to be loaded. We then pass the predicate to
``add_cmd_output``, ensuring that ``ip -s macsec show`` command will
only be run if that module is loaded.

Predicates currently support testing for kernel modules, services
running, packages being installed, system architecture, and substrings
existing within command output.
