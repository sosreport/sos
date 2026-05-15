Using git hooks to automate tests
=================================

We have the flake8, pylint and unit tests automated with Cirrus it’s
useful to automatically check each commit before allowing it into the
tree. Git provides hooks that allow a script to run before a commit
takes place and that can reject the commit by exiting with failure. See
``man 5 githooks`` for more information.

To enable a simple hook that runs flake8, pylint and unit tests add a
file at ``.git/hooks/pre-commit`` with the following content:

.. code:: bash

   $ cat .git/hooks/pre-commit
   #!/bin/bash

   fail () {
       echo "$@: [FAILED]"
       exit 1
   }

   if git rev-parse --verify HEAD >/dev/null 2>&1
   then
           against=HEAD
   else
           # Initial commit: diff against an empty tree object
           against=4b825dc642cb6eb9a060e54bf8d69288fbee4904
   fi

   echo "Check flake8 conformance"
   tox -e flake8 || fail flake8
   echo "Check pylint conformance"
   tox -e pylint || fail pylint
   echo "checking unit test suite (py3)"
   tox -e unit_tests || fail unit_tests

   # If there are whitespace errors, print the offending file names and fail.
   exec git diff-index --check --cached $against --

A failure in any of the tests will cause the commit to be rejected. Fix
the problem, update the index and try again.

For current Fedora and Ubuntu systems you should have the ``tox``
package installed to be able to run the suite.

Other distributions may use different package and command names: consult
your distribution’s Python documentation for details.
