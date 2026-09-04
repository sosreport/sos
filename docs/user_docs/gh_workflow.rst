GitHub Actions
==============

What is GitHub Actions?
-----------------------

`GitHub Actions <https://github.com/features/actions>`__ is the
provider sos uses to run our test suite for new PRs. Whenever a new PR
is opened (as long as it is not a draft PR), GitHub Actions launches a
set of tasks to setup a matrix of testing instances in GitHub runners,
copies the PR branch there, runs the test suite, and then reports the
results back to GitHub.

How are GitHub Actions defined?
-------------------------------

GitHub Actions uses the ``.github/workflows`` directory in the repo to
source the configuration of how our tests are run. Forks of the main
repo do **not** inherit the ability to run workflows via GitHub
Actions, even if the configuration file is modified in the fork.

Within ``.github/workflows/main-pipeline.yaml``, tasks are defined via
top-level ``job`` elements, for example:

.. code:: yaml

      flake8:
        needs: filters
        if: needs.filters.outputs.all_count > needs.filters.outputs.docs_count
        uses: ./.github/workflows/tox.yaml
        with:
          test_name: flake8

Then the ``.github/workflows/tox.yaml`` workflow is defined as follows:

.. code:: yaml

    name: Tox

    on:
      workflow_call:
        inputs:
          test_name:
            required: true
            type: string

    jobs:
      test:
        name: ${{ inputs.test_name }}
        runs-on: "ubuntu-latest"

        steps:
          - name: Checkout code
            uses: actions/checkout@v6

          - name: Install test dependencies
            run: |
              sudo apt update
              sudo apt -y install tox

          - name: Run Flake8
            run: |
              tox -e ${{ inputs.test_name }}

The above task typically starts as a VM on GitHub's runners and runs
``flake8`` on the PR to ensure PEP8 compliance. The main action(s) of a
task is defined by the ``test_name`` element, and is passed to the
``tox.yaml`` workflow, in the above case ``flake8``. In this case
``tox -e flake8`` will be run as a task.

For more information on how GitHub Actions can be defined, please see
the `official GitHub Actions
documentation <https://docs.github.com/en/actions>`__.

Our test suite (see :doc:`How to write a Test <writing_a_test>`) is run
via a workflow for each stage we’ve defined tests for, and for each
distribution we have defined support and have contributors for.

As of this writing, sos leverages GitHub Actions to run tests on:

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

A GitHub Action workflow failed with my PR, but it doesn’t look related to my changes
-------------------------------------------------------------------------------------

Occasionally, workflows will fail to start or hit some other
internal-to-GitHub Actions issue. When this happens the maintainers
will usually come through and restart the jobs before long. However, if
it has been more than a day or two since your PR was opened/updated and
there is still a failure in the test suite due to a GitHub Actions
issue, please simply tag one of the maintainers (e.g. @turboturtle)
and ask for the job(s) to be restarted.
