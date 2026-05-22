Contribution Guidelines
=======================

Code Requirements and Style Guidelines
--------------------------------------

-  **python-3.8** is the minimum python version target for sos. All code
   contributions **must** function on this version.

   -  This is due to downstream requirements for distributions that ship
      sos. We do not break supported downstreams.

-  Code contributions **must** adhere to PEP8 style guidelines. The
   ``flake8`` linter is used to ensure this compliance.

   -  Of particular note is nesting a list over multiple lines.
      Established sos-style is to indent the list contents with one item
      per line, with the opening and closing brackets in line with the
      calling method. For example:

      .. code:: python

       self.add_copy_spec([
           '/some/path/collection',
           '/another/path/collection'
       ])

      ..

      -  This nesting style does not apply to parameters in method
         definitions.

   -  sos uses **spaces** for indentation with a tab-width of 4.

-  `Sphinx
   style <https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html>`__
   is **recommended** when writing docstrings, though this is not a hard
   requirement as long as the docstring content is clear and easily
   understandable.
-  f-strings are **required** for all string interpolation instead of
   ``format()`` or legacy string substitution approaches.

Submitting Pull requests:
-------------------------

-  Commit messages should be split over multiple lines where necessary
   and are (with the exception of e.g. long command, log, or other
   output that should be included verbatim) hard-wrapped at 72
   characters.

-  Please write clear commit subjects and messages

   -  The subject should make it clear what the patch changes for e.g.:

      ``[archive] Fix TarArchive permission handling``

      is preferred over:

      ``Fix permission handling``

   -  Commits that affect a single plugin should be tagged with the
      plugin name in brackets in the subject line, for e.g.:

      ``[networking] Add NetworkManager nmcli support``

   -  Include any issues the code fixes (e.g. Closes: #1) on a separate
      line

   -  If working around python or other external behavior describe this
      in the full commit message for e.g.:

     ::

       commit 6501013bb780161e941f5e078a6ed7052f670a51
       Author: Bryn M. Reeves <bmr@redhat.com>
       Date:   Mon Jun 2 15:27:10 2014 +0100

           Make sure grub password regex handles all cases

           The regex to match passwords in grub.conf needs to handle both
           the --md5 and non-md5 cases and to apply the substitution only
           to the secret part (password or password hash).

           This needs to deal with the fact that python will return 'None'
           for unmatched pattern groups leading to an exception in re.subn()
           if not all referenced groups match for a given string (in contrast
           to e.g. the perl approach of treating these groups as the empty
           string).

           Make this explicit by using an empty alternate in the possibly
           unmatched '--md5' group:

                       r"(password\s*)(--md5\s*|\s*)(.*)",
                       r"\1\2********"

           Signed-off-by: Bryn M. Reeves <bmr@redhat.com>

-  Each developer should fork sos into their accounts repository.

   -  Not required, but advisable to use
      `feature/patch <http://nvie.com/posts/a-successful-git-branching-model/>`__
      branches when working with new code.

-  All pull requests should be against **main** branch
-  We avoid merge commits in main so branches may need to be rebased
   over the main-du-jour prior to merging
-  All unit tests must pass before the pull request is accepted.

   -  Testing for sos is automated - a CirrusCI build is run for each
      pull request.
   -  To save time developers can enable :doc:`local git test hooks <git_hooks>`

-  All commits **must** be accompanied by a
   ``Signed-off-by: Firstname Lastname <email@example.com>``

   -  This sign-off indicates that the contributor
      acknowledges/accepts/etc the `Developer Certificate of Origin
      (DCO) <https://developercertificate.org/>`__.

      -  Effectively, you are saying “I am either the author of these
         changes or have the permission of the author and I am entitled
         to contribute these changes under the project license”.

   -  ``<email at example dot com>`` and other obfuscations are fine
      too.
   -  Use ``git commit -s`` to automatically add a Signed-off-by with
      your configured git user details.

-  Make sure you are following `pep8 style
   guidelines <http://www.python.org/dev/peps/pep-0008/>`__
-  All regex substitutions (i.e. ``postproc()`` obfuscations) must
   include an example in comments

   -  Required as of 4.1. Older regex substitutions may not have
      examples, but these should be updated over time.

Optional but very helpful
~~~~~~~~~~~~~~~~~~~~~~~~~

-  Any functional tests we should be aware of in order to verify the
   pull requests.
-  Where possible a test case for the in-tree test suite. Unittests are
   currently run via nose, integration tests are run via avocado.

   -  See the existing cases in ``tests/`` for examples and :doc:`How to
      Write a Test <writing_a_test>` for an in-depth explanation.

License Header and Copyright Assignment
---------------------------------------

A header must be included in any new python source files that may be
added to the project. This header is copied below for convenience,
however any python file within the ``sos/`` directory can be referenced
as well.

::

   # This file is part of the sos project: https://github.com/sosreport/sos
   #
   # This copyrighted material is made available to anyone wishing to use,
   # modify, copy, or redistribute it subject to the terms and conditions of
   # version 2 of the GNU General Public License.
   #
   # See the LICENSE file in the source distribution for further information.

Like many open source projects, sos is distributed under the GPL. This
can generally be understood to be a
“`copyleft <https://en.wikipedia.org/wiki/Copyleft>`__” license. That
being said, contributors will notice that (nearly) every source file
within the project has a copyright line included with the license
header.

**NOTE**: the project is licensed under GPLv2 “only”. Previous to
sos-4.8.0 there was some ambiguity in this, with some source files
implying “or later”, e.g. GPLv3. We have since clarified this (see
#3705) and the entire project is meant to be GPLv2 only.

Going into depth about why this is the case is beyond the scope of this
article, but suffice to say it is a requirement that any new source file
contributed to the project that is included in packaged releases (in
short, anything in the ``bin/`` or ``sos/`` directories) have a
copyright line above the license header.

In general, the format of this copyright line should be similar to the
following:

``# Copyright (C) <Year> <Company (optional)> <Contributor Name> <<Contributor Email>>``

For example:

``# Copyright (C) 2022 Red Hat Inc., Jake Hunsaker <jhunsake@redhat.com>``

The company assignment is optional and is determined by the individual
making the contribution. If you are contributing to sos as part of a job
function, consult with your legal team to decide if you need to assign
it to your employer or not. If you are not making the contribution as
part of a job function, feel free to omit any company assignment and
simply include your name and email (using an email obfuscation as in
commit messages is fine).

Maintainers
-----------

The sos team follows a 2 person review process. When a pull request
comes in it will be assigned reviewers from the sosreport team. Both
reviewers must approve the pull request before a merge can take place.
The exception for this is for PRs coming from a member of the
maintainer’s team, in which case only 1 approval is needed as the
committing maintainer has an implicit approval, unless that maintainer
specifically asks for 2 approvals before merge on a given PR.

After the first review, the reviewing maintainer should add the **Needs
second ACK** label for visibility, assuming they grant a review
approval. Otherwise, the reviewing maintainer should add the appropriate
label(s) to signify changes or further review being needed.
