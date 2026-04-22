How to Write a Policy
=====================

A policy is a bit of code that Sosreport delegates to to make decisions
about how to behave on a particular distribution. Each supported
distribution requires a policy class. Policies are responsible for
providing validation on whether or not a plugin can run on the system
they understand as well as provide a simple API into the package manager
(if applicable) among other distribution-level details.

What’s required?
----------------

SoS loads policies dynamically in the same way that it loads plugins.
All policies live in ``$SOSROOT/policies/distros/`` and are plain python
source files. The name of the python source file does not matter, but it
makes the most sense to name them after the distribution that they
support. Inside the file there must be at least one class that
subclasses the ``Policy`` superclass and implements a few methods.

The class below represents the minimum set of things that a policy is
required to do to be useful to Sosreport.

.. code:: python

   import os
   from sos.policies import Policy
   from sos.report.plugins import MyPluginSuperClass

   class MyPolicy(Policy):

       distro = "MyDistro"
       vendor = "MyVendor"
       vendor_urls = [("Community Website": "http://www.example.com/")]
       vendor_text = ""
       valid_subclasses = [MyPluginSuperClass]

       @classmethod
       def check(class_):
           return os.path.isfile('/path/to/my/distribution/identity')

The ``distro``, ``vendor``, ``vendor_urls`` and ``vendor_text`` class
variables are used as as substitutions in the preamble message displayed
before collection starts. The base Policy class provides a default
generic message but policy implementers are free to override this with
their own custom text (using the tags listed above to substitute
policy-defined values). The current default policy text is:

.. code:: python

       msg = _("""\
   This command will collect system configuration and diagnostic information \
   from this %(distro)s system. An archive containing the collected information \
   will be generated in %(tmpdir)s.

   For more information on %(vendor)s visit:

     %(vendor_url)s

   The generated archive may contain data considered sensitive and its content \
   should be reviewed by the originating organization before being passed to \
   any third party.

   No changes will be made to system configuration.
   %(vendor_text)s
   """)

The Red Hat Enterprise Linux policy provides an alternate set of tag
definitions and message:

.. code:: python

   class RHELPolicy(RedHatPolicy):
       distro = "Red Hat Enterprise Linux"
       vendor = "Red Hat"
       vendor_urls = [
           ('Distribution Website', 'https://www.redhat.com/'),
           ('Commercial Support', 'https://www.access.redhat.com/')
       ]
       msg = _("""\
   This command will collect diagnostic and configuration \
   information from this %(distro)s system and installed \
   applications.

   An archive containing the collected information will be \
   generated in %(tmpdir)s and may be provided to a %(vendor)s \
   support representative.

   Any information provided to %(vendor)s will be treated in \
   accordance with the published support policies at:\n
     %(vendor_url)s

   The generated archive may contain data considered sensitive \
   and its content should be reviewed by the originating \
   organization before being passed to any third party.

   No changes will be made to system configuration.
   %(vendor_text)s
   """)
   [...]

The ``check()`` method is called once per Policy subclass and is
responsible for letting SoS know if it thinks that the underlying
platform is the distribution it understands. The check made by this
method should be designed to be mutually exclusive with every other
Policy subclass as the first check that returns True wins.

Extras
------

There are numerous other methods that can be implemented by your Policy
class. Many of these methods have usable defaults in the Superclass.

.. code:: python

   def is_root(self)

This method is responsible for determining if the process owner is a
superuser. The default checks the user’s uid (on unix). This method must
be overriden for systems where testing os.getuid for zero is not
sufficient.

.. code:: python

   def get_preferred_archive(self)

This method is responsible for returning a subclass of the Archive
class. There are two concrete implementations provided in
``sos.archive``; ``TarFileArchive`` and ``ZipFileArchive``. The default
is ``TarFileArchive``. An abstract ``FileCacheArchive`` provides a
facility for building a temporary cache at a policy defined location in
the file system. Subclasses should override the ``finalize()`` method to
create a final archive file from the temporary tree. This class is used
by the current ``TarFileArchive`` implementation.

.. code:: python

   def validate_plugin(self, plugin_class)

The ``validate_plugin()`` method is called once for each plugin that is
dynamically loaded by Sosreport to determine its whether it should run
on the current distribution. This is usually done by checking the
superclass of the plugin. It is expected for plugins to tell sos which
distribution(s) they support by tagging themselves with the proper
superclasses. See
`How-to-Write-a-Plugin <https://github.com/sosreport/sos/wiki/How-to-Write-a-Plugin>`__
for further information. You should only override this method if you
need to do something more complex than checking the plugin’s class
hierarchy.

Linux Policies
--------------

Be aware that if you wish to add a policy for a Linux-based operating
system that you will want to start with the ``LinuxPolicy`` superclass.
This policy contains many helpful defaults that should save you a lot of
work.

Package Managers
----------------

Package Manager abstractions are used to standardize how SoS policies
obtain and provide package information from a host. At the time of this
writing there are ``PackageManager`` classes for ``rpm`` and ``dpkg``.
To use one of these in a new policy, simply import it and assign the
``package_manager`` class variable to an instance of it:

.. code:: python

   from sos.policies.distros import LinuxPolicy
   from sos.policies.package_managers.rpm import RpmPackageManager


   class MyLinuxPolicy(LinuxPolicy):

       def __init__(self, sysroot=None, init=None, probe_runtime=True,
                    remote_exec=None):
           self.package_manager = RpmPackageManager(chroot=sysroot,
                                                    remote_exec=remote_exec)

If the above doesn’t work for you then you will need to implement a
``PackageManager`` class that plugins can interact with. Generally all
you must do is define how to get the full list of packages:

.. code:: python

   from sos.policies.package_managers import PackageManager

   class MyPackageManager(PackageManager):

       def all_pkgs(self):
           return {
               'package_name': {
                   'name': 'package_name',
                   'version': ('1', '0', '0'), # version 1.0.0
                   # so on and so on...
               }
           }

The default PackageManager class should work if you lack a real package
manager on the system.

.. code:: python


   class PackageManager(object):

       def all_pkgs_by_name(self, name):
           """
           Return a list of packages that match name.
           """
           return fnmatch.filter(self.allPkgs().keys(), name)

       def all_pkgs_by_name_regex(self, regex_name, flags=None):
           """
           Return a list of packages that match regex_name.
           """
           reg = re.compile(regex_name, flags)
           return [pkg for pkg in self.allPkgs().keys() if reg.match(pkg)]

       def pkg_by_name(self, name):
           """
           Return a single package that matches name.
           """
           try:
               self.all_pkgs_by_name(name)[-1]
           except Exception:
               return None

       def all_pkgs(self):
           """
           Return a list of all packages.
           """
           return []

       def pkg_nvra(self, pkg):
           fields = pkg.split("-")
           version, release, arch = fields[-3:]
           name = "-".join(fields[:-3])
           return (name, version, release, arch)

Container Runtimes
------------------

Policies in sos support discovery and use of abstracted container
runtimes to interact with containers that may be running on the system.
This in turn allows plugins to consistently discover and execute
commands for/inside containers.

.. code:: python

   class ContainerRuntime(object):
       """Encapsulates a container runtime that provides the ability to plugins to
       check runtime status, check for the presence of specific containers, and
       to format commands to run in those containers

       :param policy: The loaded policy for the system
       :type policy: ``Policy()``

       :cvar name: The name of the container runtime, e.g. 'podman'
       :vartype name: ``str``

       :cvar containers: A list of containers known to the runtime
       :vartype containers: ``list``

       :cvar images: A list of images known to the runtime
       :vartype images: ``list``

       :cvar binary: The binary command to run for the runtime, must exit within
                     $PATH
       :vartype binary: ``str``
       """

       name = 'Undefined'
       containers = []
       images = []
       volumes = []
       binary = ''
       active = False

As of this writing, there is support for ``docker`` and ``podman``
runtimes. New container runtimes can be built off of the base
``ContainerRuntime`` class, and assuming the runtimes are OCI compliant,
are trivial to introduce. For example, the ``podman`` runtime only needs
to specify the name of the runtime, and the name of the binary used to
execute runtime commands (e.g. ``podman ls``). In this case, as with
docker, the name and binary are the same:

.. code:: python

   class PodmanContainerRuntime(ContainerRuntime):
       """Runtime class to use for systems running Podman"""

       name = 'podman'
       binary = 'podman'

The default check to see if a runtime is in use, is simply if the binary
exists on the system. If you need to implement a ``ContainerRuntime``
that needs a more comprehensive check, override the
``check_is_active()`` method, as we do with ``docker`` which also must
have a daemon running:

.. code:: python

       def check_is_active(self):
           # the daemon must be running
           if (is_executable('docker') and
                   (self.policy.init_system.is_running('docker') or
                    self.policy.init_system.is_running('snap.docker.dockerd'))):
               self.active = True
               return True
           return False

Policies will load *all* runtimes found on the system when sos
initializes, however the runtime it defaults to can be controlled via
the ``default_container_runtime`` attribute which currently defaults to
``docker``. Simply override this attribute in your policy to change the
default runtime.

The default runtime comes into play in plugins, when containers can be
queried and have commands executed within them. All the container
methods support a ``runtime`` parameter allowing plugin authors to be
sure of where the data they’re requesting comes from. If ``runtime`` is
not set in the calls, it defaults to the default runtime for the policy
(or, the only active runtime if only one is discovered during
initialization).
