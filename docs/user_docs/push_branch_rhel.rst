How to push a branch to sos git repo on RHEL
============================================

This article explains how to commit a branch with patches to the
`sos <https://github.com/sosreport/sos>`__ git repository using RHEL 7.
**This article assumes that user has permissions to push commits to**
`sos <https://github.com/sosreport/sos>`__\ **.**

Please note that before committing a branch to
`sos <https://github.com/sosreport/sos>`__ git repository that it is
recommended that a ``pre-commit`` git script is ran when the code is
committed. How to set this up is explained in the following article:
:doc:`Using git hooks to automate tests with RHEL <git_hooks_rhel>`.
It is suggest that this hook is installed in global hooks directory for
``git`` before cloning the `sos <https://github.com/sosreport/sos>`__
git repository or installed afterwards in local
repository(``.git/hooks/pre-commit``).

For the ``pre-commit`` script to run successfully, RHEL 7 needs the
following packages installed:

* ``python-2.7``: ``python``, ``python-six``, ``python-nose``, ``python-coverage``,
  and ``python-pep8`` 
* ``python-3.3``: ``python33``, ``python33-python-nose``, ``python33-python-six``,
  ``python33-python-coverage``, and ``scl-utils``

The ``python-2.7`` packages are included in the RHEL 7 base channel
except for ``python-pep8`` which is located on
`EPEL <http://download.fedoraproject.org/pub/epel/7/x86_64/repoview/epel-release.html>`__.
To install these then run commands similar to the following:

::

   $ sudo rpm -ivh http://mirror.nexcess.net/epel/7/x86_64/e/epel-release-7-5.noarch.rpm
   $ sudo subscription-manager repos --enable rhel-7-server-extras-rpms
   $ sudo yum --y -enablerepo=epel install python-pep8 python-six python-nose

The ``python-3.3`` libs and binaries are located in the channel called
`SCL or Software
Collections. <https://access.redhat.com/documentation/en-US/Red_Hat_Developer_Toolset/2/html/Software_Collections_Guide/index.html>`__.

::

   $ sudo subscription-manager repos --enable rhel-server-rhscl-7-rpms
   $ yum install python33 python33-python-nose python33-python-six scl-utils

*The reason that we install the ``scl`` packages is so that we can
easily switch ``python-2.7`` to ``python-3.3`` without changing the main
environment and all can be done with a simple command.*

Create a new sos ``git`` branch
-------------------------------

Upstream uses the following branch
``remotes/origin/master`` where all the branches that contain fixes will
eventually be merged into. All of our local branches should be built
against the ``master`` on the remote
`sos <https://github.com/sosreport/sos>`__ git repository.

*It is recommend that for each patch or set of related patches that a
branch be created that will contains only those patches. The branch name
should be simple description that explaining the patches contain in the
new branch.*

::

   $ mkdir ~/git/sos
   $ cd ~/git/sos
   $ git clone git://github.com/sosreport/sos.git sos-sbradley-parted_sector_units
   $ cd ~/git/sos/sos-sbradley-parted_sector_units
   $ cp ~/pre-commit .git/hooks/pre-commit
   $ git checkout -b sbradley-parted_sector_units  

-  Omit the ``-b`` if remote branch already exists. If already remote a
   ``checkout`` will automatically create a local tracking branch for
   you. This article focused on remote branches that does not exist.
-  The copying of the ``pre-commit`` hook script can be skipped if
   exists global. If the ``pre-commit`` hook script exists locally then
   when the new cloned repository was created a copy of that hook should
   have been copied to
   ``<path to cloned git repo>/.git/hooks/pre-commit``.\*

Pushing a new remote branch to the ``git`` repository
-----------------------------------------------------

Once you have
some changes that needed to be committed then follow a similar procedure
as below. Make sure that your commit message follows the guidelines that
are outlined in the following article: :doc:`Contribution
Guidelines <contribution_guidelines>`.
*The ``--amend`` command only needs to be ran if you want to make
changes to the commit message.*

The commit message should include you signature which is automatically
added with the command ``git commit -s``. *Your name and email should be
added to your ``git`` config file before adding your signature will
work*:

::

   $ git branch
       master
     * sbradley-parted_sector_units
   $ git add sos/plugins/block.py
   $ git commit -s 
   $ git push -u origin sbradley-parted_sector_units
   $ git show
   $ git branch --all

The commit message should look something like the following which
conforms to our :doc:`Contribution Guidelines <contribution_guidelines>`
and include a ``Fixes`` line if there is an issue opened that is
resolved with this commit:

::

   # git log -1
   commit f2d9d8d04ec2781dd515d0bb370df2ac59983b68
   Author: Shane Bradley <sbradley@redhat.com>
   Date:   Tue Jan 20 11:08:59 2015 -0500

       [block] Don't use parted human readable output 

       Changed the parted command to return data in sectors units
       instead of human readable form.
    
       Fixes: #42

       Signed-off-by: Shane Bradley <sbradley@redhat.com>

If the commit was successful then you should see hash that was created.
If there was errors then then commit will fail. Once those
errors (generated possibly by the ``pre-commit`` script) are resolved
then you can commit the patches again.

After pushing changes to a remote branch
----------------------------------------

After pushing changes to a
remote branch, the next step is to do ``pull request`` as stated in the
:doc:`Contribution
Guidelines <contribution_guidelines>`.
These steps are outlined in the following article: `Creating a pull
request - User
Documentation <https://help.github.com/articles/creating-a-pull-request/>`__.

References
----------

* :doc:`SOS Contribution Guidelines <contribution_guidelines>`
* `Example branching model <http://nvie.com/posts/a-successful-git-branching-model/>` that
  has useful information about ``git`` branching. 
* :doc:`Using git hooks to automate tests <git_hooks>`
* :doc:`Using git hooks to automate tests with RHEL <git_hooks_rhel>`
