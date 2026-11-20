Debian and Ubuntu packaging using git
=====================================

Debian packaging for sosreport is done using the `gbp
buildpackage <https://manpages.debian.org/testing/git-buildpackage/gbp-buildpackage.1.en.html>`__
tool that facilitates the management of the build, patches,
pristine-tar, and upstream changes.

1. `Debian: Packaging a new release <#packaging-a-new-release>`__
2. `Debian: Backport process <#debian-backport-process>`__
3. `Debian: Sponsorship Differences <#sponsorship-differences>`__
4. `Ubuntu: Stable Release Updates (SRUs) <#ubuntu-sru-process>`__

Packaging a new release
-----------------------

First clone the repo and move into the directory

::

   git clone ssh://git@salsa.debian.org/sosreport-team/sosreport
   cd sosreport

Now checkout the backports branch, and merge the latest code into it

::

   git checkout debian/latest

Now we need to add the upstream repo

::

   git remote add upstream-git https://github.com/sosreport/sos

We fetch the latest code from upstream

::

   git fetch upstream-git

Now we want create the patch queue (we can skip this, if we have no
patches)

::

   gbp pq import  # only if you have patches against upstream

This in essence creates a new patch queue branch, so that anything we
add can be rebased if needed. What this means that in the latter part of
the steps, it can potentially update the patches so that they would
apply cleanly to the source.

Grab the latest debian package we have

::

   git checkout debian/latest

We now need to import the latest from upstream, this can be done by
creating an archive of the release that we want to package. The example
below uses version 4.10.2

::

   VERSION=4.10.2
   git archive --format=tar.gz --prefix=sos-${VERSION}/ -o ../sos_${VERSION}.orig.tar.gz ${VERSION}

Now we import the tarball.

::

   gbp import-orig ../sos_${VERSION}.orig.tar.gz -u ${VERSION}

This command will do multiple things 1. Upload the contents and the
changes to the ``upstream`` branch 2. Create a new tag for this, and
would be ``upstream/<upstream-tag>`` 3. It will create a new commit into
the ``pristine-tar`` branch that allows a person in the future to grab
the same tarball that is being used here for potential uploads 4. Will
update the ``debian/latest`` branch from the ``upstream`` branch

Only if we have patches

::

   gbp pq rebase
   gbp pq export
   gbp pq drop
   git add debian/patches
   git commit

If the commit requires to add a message, then generally use the
following message

::

   Drop patches already applied in new release.

We may want to add extra description of any other information that may
be relevant

Then we use ``dch -i -r unstable``, this will open a new interactive
editor for the new changelog entry. A few things will need to be amended

1. The version, this will typically be the upstream version then
   appended with -1, for example 4.10.2-1
2. The series, in most cases this will be unstable
3. The priority is always medium in 95% of the cases
4. Then add the items in the changelog. Now this is what is changed in
   the debian package, not the source code. You will add a bullet point
   for upstream new version, but that should suffice.
5. The email of the person making the upload. This needs to be the same
   email that was used for the GPG key signing and uploaded to mentors
6. Finally, the date, this is preceded with 2 spaces, and the date
   itself. The format of this can easily be taken from the ``date -R``
   command
7. We save the file, and the changelog would be updated.

We now add the ``debian/changelog`` to git, and add a new commit, and
then we can prep for upload to mentors.

::

   git add debian/changelog
   git commit -m "Add changelog for 4.10.2-1"
   git push origin

Now we build the package and upload to mentors or debian directly

::

   git-buildpackage -S -d
   dput ftp-master ../sos_4.10.2-1_source.changes

Debian Backport Process
-----------------------

First clone the repo and move into the directory

::

   git clone ssh://git@salsa.debian.org/sosreport-team/sosreport
   cd sosreport

Now checkout the backports branch, and merge the latest code into it.
The following command will specifically look at ``trixie-backport``, but
a similar concept can be applied for any other backports

::

   git checkout debian/trixie-backport
   git merge debian/latest

Resolve the merge conflicts. This usually means that the version from
the new version is on top of the previous backport, so in example below
is the top of ``debian/changelog`` from ``debian/trixie-backports``
branch when the merge was fixed

::

   sos (4.10.2-1) unstable; urgency=medium

     * New upstream release 4.10.2

     * For more details, full release note is available here:
       - https://github.com/sosreport/sos/releases/tag/4.10.2

     * d/control: Change maintainer to DPT
     * d/gbp.conf: Conform to DPT policy settings

    -- Arif Ali <arif-ali@ubuntu.com>  Mon, 15 Dec 2025 16:52:51 +0000

   sos (4.10.1-1~bpo13+1) trixie-backports; urgency=medium

     * Rebuild for trixie-backports.

    -- Arif Ali <arif-ali@ubuntu.com>  Thu, 27 Nov 2025 09:54:20 +0000

Then, typically, you will be guided to the shell, and the current state
of the git merge is still outstanding, so typically we can run the
commands below to resolve this

::

   git add debian/changelog
   git commit --no-edit

Now, we need to add the new changelog entry, the simplest way to do this
is by running the command below

::

   dch --bpo

This should open the editor to make any changes. In most cases no
changes would be needed. Just remove the extra bullet point, save and
commit the change; something on the lines of

::

   git commit -m "d/changelog: backport from 4.10.2-1"

Now we need to tag it

::

   git tag debian/4.10.2-1_bpo13+1

Push the branch and tag to the repo

::

   git push origin debian/trixie-backport
   git push origin debian/4.10.2-1_bpo13+1

Finally, we can build the source, and push to debian. Noting, that we
have added an extra -v flag to designate the previous version that was
uploaded to backports.

::

   dpkg-buildpackage -S -d -v4.10.1-1~bpo13+1
   dput ftp-master ../sos_4.10.2-1~bpo13+1_source.changes

Sponsorship differences
-----------------------

If you are going to request sponsorship, then you will need to upload to
mentors instead, and you would replace ftp-master with mentors. You will
need to create an account on mentors.debian.net if you have not got one
already, and then add your GPG key that would be used for signing your
package.

Once the upload to mentors is done, you should be able to submit a
request for sponsorship (RFS). A template for this will be available at
https://mentors.debian.net/sponsors/rfs-howto/sos/ (This link will only
be available when the upload is done). We then submit this to the
following mailing lists

* to: submit@bugs.debian.org
* cc: debian-python@lists.debian.org
* cc: debian-mentors@lists.debian.org

This ensures that the right people are looking at the RFS, and quicker
the sponsorship can go through.

Over time you may have built some relationship with a sponsor, and you
may be able to contact this person without submitting an RFS, and point
this person to your package that has been uploaded to mentors.

.. _ubuntu-sru-process:

Ubuntu Stable Release Updates (SRUs)
------------------------------------

Ubuntu has an SRU exception policy for ``sos`` / ``sosreport`` that
allows new upstream versions to be released to stable Ubuntu series. The
policy defines the eligibility criteria and requirements for
consideration; it does not guarantee that an update will be accepted.
Review the `SRU exception policy for sosreport
<https://ubuntu.com/project/docs/SRU/reference/exception-Sosreport-Updates/>`__
before preparing an update.

If the proposed microrelease SRU is justified under the policy, prepare
the Ubuntu package as follows. Repeat the branching and packaging steps
for each target Ubuntu series.

Clone the Ubuntu packaging repository and add remotes for upstream and
Debian. The upstream remote provides the release source, while the
Debian remote provides Debian packaging changes and patches to review.

::

   git ubuntu clone sos
   cd sos
   git remote add upstream git@github.com:sosreport/sos.git
   git remote add debian git@salsa.debian.org:python-team/packages/sosreport.git
   git fetch --all

Create a local branch from the Ubuntu development branch for the target
series. For example, to prepare sos 4.12.1 for Resolute:

::

   git checkout -b resolute-4.12.1 pkg/ubuntu/resolute-devel

Import the upstream release changes without replacing Ubuntu's
``debian`` directory. Upstream, Debian, and Ubuntu maintain that
directory independently. Substitute the release tag you are packaging:

::

   git diff @..4.12.1 -- ':(exclude)debian' | git apply
   git add -A
   git commit -m "Import 4.12.1 from upstream"

Review the Ubuntu patch series and remove patches that have already
been applied upstream or are otherwise no longer needed. Check each
patch before removing it.

::

   git rm debian/patches/<patch-file>
   vim debian/patches/series  # Remove references to now deleted patches
   git commit -m "Remove patches no longer needed"

Compare the state of the local tree to the tagged debian release and
review any differences. Typically there should only be differences in
the debian directory such as the changelog, copyright, new patches from
Debian, the watch and control files, and tests.

Typically the copyright file can be copied directly from Debian as it
will have the most up-to-date information. Review any new patches from
Debian for suitability in Ubuntu, and selectively apply changes as
needed. Contrastingly, the watch file and changelog should not be
copied.

::

   git diff HEAD..debian/<debian-tagged-release>
   git checkout debian/<debian-tagged-release> -- debian/<file>
   git add debian/<file>
   git commit -m "d/<file>: <summary>"

Regarding the relevant changes in ``debian/control``: add new build
dependencies when the required packages and versions are available in
Ubuntu, and update ``Breaks`` and ``Replaces`` as needed for the upgrade
path. If this is the first SRU for the target series, ie.  the first
release in the series to use an ``-XubuntuY`` version suffix, it is
necessary to update the maintainer field with ``update-maintainer`` and
commit the resulting change:

::

   update-maintainer
   git add debian/control
   git commit -m "d/control: Update maintainer to Ubuntu Developers"

Before proposing the SRU, create a Launchpad bug following the SRU
template. Include the justification, changes since the last Ubuntu
upload, a test plan, and the potential regressions and how they could
appear. Target both ``sos`` and ``sosreport`` packages, and mark the
relevant Ubuntu series as affected.

Update ``debian/changelog`` for the SRU. Set the package version and
Ubuntu series, link the Launchpad bug and upstream release notes, and
summarize packaging changes since the last Ubuntu upload.

::

   dch -i
   git add debian/changelog
   git commit -m "d/changelog: Update changelog for 4.12.1"

Push the branch to your personal Launchpad remote and open a merge
proposal against the target series' ``-devel`` branch. Once the PR
is open, subscribe the `~ubuntu-sponsors` team to the bug.

::

   git push <personal-remote> resolute-4.12.1
