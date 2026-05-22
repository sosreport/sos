Maintainers how to merge PR
===========================

Shared Goals:

* never have merge commits in the sosreport repo.

Normal CL workflow (from bmr-cymru in
https://github.com/sosreport/sos/issues/1856#issuecomment-553394943):

::

   $ git checkout -b bmr-merge
   $ sospull TurboTurtle:somebranch
   $ git rebase main
   $ git commit -s --amend # add Signed-off-by and Resolves/Closes tags
   $ git checkout main
   $ git merge bmr-merge
   $ git branch -d bmr-merge

Depending on conflicts in the branch sometimes it’s easier to ``git pull
--rebase`` (otherwise you can end up resolving the conflict once when you
first pull it onto your tree, and a second time when you rebase over
master...).

sospull is a shell function:

::

   sospull () { git pull https://github.com/$(echo $@|sed 's/:/\/sos /'); }
