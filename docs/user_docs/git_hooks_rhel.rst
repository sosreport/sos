Using git hooks to automate tests with RHEL
===========================================

This is another :doc:`pre-commit <git_hooks>`
git hook script that will automate the process of checking the commit
before allowing it into the tree. This hook uses the ``python-3.3`` libs
and binaries located in the channel called `SCL or Software
Collections. <https://access.redhat.com/documentation/en-US/Red_Hat_Developer_Toolset/2/html/Software_Collections_Guide/index.html>`__
which includes a separate binary called ``scl``. In this version of the
``pre-commit`` the tool ``scl`` is used to run the automated
``python 3.3`` tests. For more information about using ``git`` with RHEL
then see the following article: :doc:`How to push a branch to sos git repo on
RHEL <push_branch_rhel>`.

::

   $ cat ~/.git-templates/hooks/pre-commit
   #!/bin/bash
   # pre-commit
   #
   # Author: Shane Bradley (sbradley AT redhat.com)
   # URL: https://github.com/sosreport/sos/wiki/Using-git-hooks-to-automate-tests
   # Description: This script will be ran before a commit is successfully
   # committed. They are python tests that makes sure that the conform to "pep8"
   # and there are no compatibility issues with python 2 and 3.
   #
   # This script is based on the orginal script on the sos wiki, but adds support
   # to running the python 3 using the "scl" python environment.
   #
   # Usage: This file is used by git and ran after a commit is done. It is not
   # intended to be ran by user.
   #
   # The file should be copied to either the global hooks directory or the local
   # repo directory: <local git repo>/.git/hooks/pre-commit.
   #
   # The script needs to have the exeute bit set, for example:
   # $ chmod +x <local git repo>/.git/hooks/pre-commit

   do_nosetests33() {
       # Run python 3.3 tests against the files being commmitted.
       if which scl > /dev/null 2>&1; then
           scl enable python33 "$1 -v --with-coverage --cover-package=sos --cover-html";
       else
           do_nosetests $1;
       fi
   }

   do_nosetests() {
       # Run python 2 tests against the files being commmitted.
       $1 -v --with-coverage --cover-package=sos --cover-html;
   }

   fail () {
       echo "$@: [FAILED]";
       exit 1;
   }

   # Main
   if git rev-parse --verify HEAD >/dev/null 2>&1
   then
       against=HEAD;
   else
       # Initial commit: diff against an empty tree object.
       against=4b825dc642cb6eb9a060e54bf8d69288fbee4904;
   fi

   echo "Starting PRE-Commit tests before changes are committed.";
   echo "Checking pep8 conformance.";
   pep8 sos || fail pep8;
   echo "Checking unit test suite against python 3.";
   do_nosetests33 nosetests-3.3 || fail nosetests-3.3;
   echo "Checking unit test suite against python 2.";
   do_nosetests nosetests || fail nosetests;

   #If there are whitespace errors, print the offending file names and fail.
   exec git diff-index --check --cached $against --

