Policy on changes to legacy 3.9
===============================

Currently, sos maintains a ``legacy-3.9`` branch for downstreams that
still ship a sos-3.9 package. This branch is to help those downstreams
backport fixes for their releases, and is not intended for active, new
development.

The following are general guidelines to follow when opening a PR against
the ``legacy-3.9`` branch:

-  Your commit *must* fix a specific issue/bug within the sos-3.9 line.
   I.E. no new features, bug and security fixes only.
-  All commits *must* apply cleanly to the ``legacy-3.9`` branch and
   address only the specific issue at hand.

   -  In other words, do not backport an entirely changed plugin from
      4.x. If the plugins have diverged significantly, then the fix must
      be written for the 3.9 version, which may differ from any fix
      presented against the current ``master``.

-  If one exists, please link the downstream bug in the commit message.
   E.G. have a line like ``Related: RHBZ123456``

Any and all other guidelines from the :doc:`Contribution
Guidelines <contribution_guidelines>` still apply.
