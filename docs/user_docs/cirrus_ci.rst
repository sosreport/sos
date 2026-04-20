Cirrus CI
=========

What is Cirrus CI?
------------------

`Cirrus CI <https://cirrus-ci.org/>`__ is the provider sos uses to run
our test suite for new PRs. Whenever a new PR is opened (as long as it
is not a draft PR), Cirrus launches a set of tasks to setup a matrix of
testing instances in Google Cloud Engine, copies the PR branch there,
runs the test suite, and then reports the results back to GitHub.

The ability to run instances in GCE is funded by Red Hat. Direct control
over the GCE and Cirrus projects for sos is currently vested in project
maintainers working for Red Hat.

How are Cirrus tasks defined?
-----------------------------

Cirrus uses the ``.cirrus.yml`` file in the repo to source the
configuration of how our tests are run. Forks of the main repo do
**not** inherit the ability to run tasks via Cirrus, even if the
configuration file is modified in the fork.

Within ``.cirrus.yml``, tasks are defined via top-level ``task``
elements, for example:

.. code:: yaml

   # Run a simple lint on the community cluster
   flake8_task:
       alias: "flake8_test"
       name: "Flake8 linting test"
       container:
           image: alpine/flake8:latest
       flake_script: flake8 sos

The above task starts a container on Cirrus’ community cluster to run
``flake8`` on the PR to ensure PEP8 compliance. The main action(s) of a
task is defined by ``script`` elements, in the above case
``flake_script``. Cirrus will run any ``_script`` elements in defined
order as part of the task.

For more information on how Cirrus tasks can be defined, please see the
`official Cirrus
documentation <https://cirrus-ci.org/guide/quick-start/>`__.

Our test suite (see :doc:`How to write a Test <writing_a_test>`) is
run via a task for each stage we’ve defined tests for, and for each
distribution we have defined support and have contributors for.

As of this writing, sos leverages cirrus to run tests on:

-  CentOS Stream
-  Fedora
-  Ubuntu
-  Debian

RHEL testing is handled downstream by Red Hat currently, however
contributors should feel comfortable with tests passing for CentOS
Stream if their contributions are primarily aimed at RHEL.

If you would like to add distributions to the testing matrix, please
open an issue requesting as much. While there are no hard and fast
requirements for adding a distribution to the matrix, there is a cost
associated with every distribution tested so the project asks for a
level of continued contribution in order to add a distribution to
automated testing.

A Cirrus task failed with my PR, but it doesn’t look related to my changes
--------------------------------------------------------------------------

Occasionally, tasks will fail to start or hit some other
internal-to-cirrus issue. When this happens the maintainers will usually
come through and restart the jobs before long. However, if it has been
more than a day or two since your PR was opened/updated and there is
still a failure in the test suite due to a Cirrus issue, please simply
tag one of the maintainers (e.g. @turboturtle) and ask for the job(s) to
be restarted.
