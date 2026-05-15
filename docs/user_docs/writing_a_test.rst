How to Write a Test
===================

SoS, as of April 2021, uses the *python-avocado* testing framework to
handle test cases in validating release and code changes. This allows
for easy creation of new test cases, and facilitates higher confidence
in downstream releases of SoS. Additionally, it provides an easy
framework to allow those downstreams to push tests back into upstream.

As a general rule, *all* test cases defined in the test suite *must*
pass for any PR to be merged.

If you are adding new functionality with your PR, it should bring with
it enough test cases (even if it’s only 1) to vet that new
functionality. **If you are enhancing an existing plugin or creating a
new plugin, it is highly recommended to include a test case, though not
required.**

Ideally, bug fix PRs should also include a regression test if it is
feasible to do so in test VMs (which will run on GCE).

Testing environment
-------------------

All tests are conducted on fresh VMs provisioned in GCE for every PR
opened. Any subsequent updates to the PR will trigger a new round of
tests (and thus a new set of VMs provisioned for that test run). These
VMs are provisioned by CirrusCI, and not directly through GCE APIs.

Currently, tests are performed for **Fedora** and **Ubuntu**
distributions. We are planning to add **CentOS Stream** and eventually
**RHEL** to this list, once the infrastructure is available to do so.

Testing methodology
-------------------

Tests are logically categorized into “stages” as follows:

::

   stage 0 -> Unittests
   stage 1 -> Basic function tests, no mocking allowed
   stage 2 -> Mocked tests for specific scenarios/regressions

There are plans to potentially add “stage 3” tests which would allow for
complex networking configurations and potentially multi-host
arrangements, once the testing infrastructure allows for that.

Stage 0 tests are conducted by ``nose`` and are traditional unit tests.
Stage 1 tests involve executing actual ``sos`` commands, saving the
output and then inspecting the output and investigating test system
state (mostly to ensure that state was not changed by the ``sos``
command execution). Stage 2 tests will allow for changes *prior* to the
``sos`` command execution, such as dropping specific files on the
filesystem. Any changes made by a stage 2 test setup are removed after
the test has concluded.

For each PR, stage 0 and stage 1 tests are always run. Stage 1 tests are
run against the distribution list above, for both the “current” release
and the release immediate prior to that one. Stage 2 tests are run for
current releases only.

To run the test suite manually, for stage 1, run the following from the
git checkout:

::

   # PYTHONPATH=tests/ avocado run -t stageone tests/

If you are on a system that can withstand interim changes during the
test suite, you can use ``-t stagetwo`` to run the stage 2 mocking
tests. It is not recommended to run *both* stage 1 and stage 2 tests in
the same invocation, as there is no guarantee of the order in which the
individual tests will run.

Writing a test for SoS
----------------------

Most tests focus around ``sos report`` or specific plugins. These can
either be stage 1 or stage 2 tests. When determining which stage the
test belong to, consider the following:

-  Do I need to test that specific content within a file is properly
   removed via post processing?
-  Do I need to make sure a specific command/binary is present that is
   likely not a default installation?
-  Do I need to test that my iteration loop in a plugin over a config
   file is working as expected?

If you answered yes to any of these, you likely want a **stage 2** test,
and if not then a **stage 1** test is fine.

Writing a Stage 1 test
~~~~~~~~~~~~~~~~~~~~~~

Stage 1 tests are fairly straight forward. All these tests must subclass
``StageOneReportTest`` and set the ``sos_cmd`` class attr. From there,
you only need to define ``test_`` methods that test for your criteria.
Additionally, you’ll need to set the avocado tags in the class
docstring.

For example, consider this test:

.. code:: python

   from sos_tests import StageOneReportTest


   class NormalSoSReport(StageOneReportTest):
       """
       :avocado: tags=stageone
       """

       sos_cmd = '-vvv --label thisismylabel'

       def test_debug_in_logs_verbose(self):
           self.assertSosLogContains('DEBUG')

       def test_postproc_called(self):
           self.assertSosLogContains('substituting scrpath')

       def test_label_applied_to_archive(self):
           self.assertTrue('thisismylabel' in self.archive)

       def test_free_symlink_created(self):
           self.assertFileCollected('free')

First we instantiate a new class which subclasses
``StageOneReportTest``. This allows us to ensure that avocado will run
the sos command built from ``sos_cmd``, extract the resulting archive,
and make sure our assertions are relative to that extracted archive.

Avocado will execute all ``test_*`` methods defined within a class,
including the “base tests” defined in ``StageOneReportTest``. That way,
you only need to write test methods for the exact criteria you’re
testing, rather than re-writing several tests such as our “no new kmods
were loaded” test.

The ``:avocado: tags=stageone`` line in the docstring ensures that
avocado identifies this test as stageone.

Here’s a breakdown of the remaining items in this test class:

-  ``sos_cmd`` - This class attr defines the options passed to an
   ``sos report`` execution. You only need to specify options, not the
   binary, path, or ``--batch``.
-  ``assertSosLogContains`` - Ensure that the given string appears in
   ``sos_logs/sos.log``. There is also ``assertSosLogNotContains`` which
   ensures the string does not appear there.
-  ``assertFileCollected`` - Ensure the given file appears in the
   archive. There is also ``assertFileNotCollected`` for ensuring a file
   was not collected. Note that this is for *single* files only. If you
   need to match globs, use ``assertFileGlobInArchive`` or
   ``assertFileGlobNotInArchive``.

Writing a Stage 2 test
~~~~~~~~~~~~~~~~~~~~~~

Stage 2 tests have all the bits of stage 1, with mocking functionality
strapped on top. For these, you’ll subclass ``StageTwoReportTest``.

Let’s take a look at the following theoretical stage 2 test:

.. code:: python


   from sos_tests import StageTwoReportTest

   class FooTest(StageTwoReportTest):

       files = [('bar', '/etc/foo/bar')]
       packages = {'rhel': 'foobar'}
       install_plugins = ['foo']

       sos_cmd '-v '

       def test_foo_plugin_enabled(self):
           self.assertPluginIncluded('foo')

       def test_foo_collected(self):
           self.assertFileCollected('/etc/foo/bar')

There’s a lot going on here, mostly with mocking. As stated above, Stage
2 tests will perform mocking operations *before* an sos command
execution, and clean up that mocking once it is complete. Let’s break
this down:

-  ``files`` - This is a list of files that should be dropped on the
   test system’s filesystem. The values of this list should be tuples,
   in the format of ``(relative_src, absolute_dest)``. Meaning, files
   should be placed in the same (sub)dir as the test ``.py`` file. It is
   a good idea to create a subdirectory for each new stagetwo test, and
   place all mocked files therein.
-  ``packages`` - This dict defines the list of packages to be
   installed, and is distro-dependent. These packages will be installed
   on the test system before the test, and uninstalled after the test.
   For RH family systems, you only need to define ``rhel``, ``fedora``,
   or ``centos`` here and it will apply to all 3. In the rare event the
   package name differs between say ``rhel`` and ``fedora``, simply
   define the right package name for each individually in this dict.
-  ``install_plugins`` - A list of “fake” plugins to install for the
   local sos branch in order to run the plugin for the test. If your
   test requires the use of a plugin that does not exist in sos
   (e.g. one used specifically to test sos functionality, like timeouts)
   you can include that plugin here. These plugins should be written to
   the same directory as the test file - ideally, in a dedicated subdir
   within the ``tests/`` tree, and the name(s) in this list should be
   the filename without the ``.py`` extention.

My test only applies to a specific distribution, how do I prevent it from failing on other distributions?
---------------------------------------------------------------------------------------------------------

At current, you can limit specific test *methods* but not entire test
*classes*. You can do this via helper decorators provided in
``sos_tests``.

.. code:: python


   from sos_tests import StageOneReportTest, redhat_only, ubuntu_only

   class Barfoo(StageOneReportTest):

      sos_cmd = '--some-option'

      @redhat_only
      def test_redhat_criteria(self):
          [...some assertion...]

      @ubuntu_only
      def test_ubuntu_criteria(self):
          [...some assertion...]

The above test class will run the respectively decorated methods on test
systems matching those distributions, and **skip** the test on all
others. For both distributions, the ``test_*`` methods defined in the
base ``StageOneReportTest`` will run as normal.

Like the ``packages`` attr for mocking, ``@redhat_only`` applies to
RHEL, Fedora, and CentOS.

I need to do some non-mocking setup prior to a test executing
-------------------------------------------------------------

If you need to do some pre-test setup within a test class, use the
``pre_sos_setup()`` method. This method will run prior to sos execution,
but note that it is not acceptable to do any mocking in this function.
As an example use case, look at one of our smoke tests:

.. code:: python

   class AllPluginSmokeTest(StageOneReportTest):
       """This test forcibly enables ALL plugins available to the local branch
       and aims to make sure that there are no exceptions generated during the
       execution

       :avocado: tags=stageone
       """

       def pre_sos_setup(self):
           _cmd = '%s report --list-plugins' % SOS_BIN
           out = process.run(_cmd, timeout=300).stdout.decode()
           reg = DISABLED + '(.*?)' + OPTIONS
           self.plugs = []
           for result in re.findall(reg, out, re.S):
               for line in result.splitlines():
                   try:
                       self.plugs.append(line.split()[0])
                   except Exception:
                       pass

           self.sos_cmd = '-e %s' % ','.join(p for p in self.plugs)

In this test case, we need to generate a list of all locally available
plugins. So we run ``--list-plugins`` in ``pre_sos_setup()`` and then
grok the output, setting ``sos_cmd`` appropriately from that list.

I have a test case for a downstream bugzilla/launchpad/etc…
-----------------------------------------------------------

Great! We love getting new regression tests from downstreams. It is
preferred that tests like this be placed under
``tests/vendor_tests/<vendor>/``, and ideally identify which BZ/LP/etc
they are for. For example, ``tests/vendor_tests/redhat/bz12345.py``
makes it easy at a glance to see what that test is addressing from that
vendor.
