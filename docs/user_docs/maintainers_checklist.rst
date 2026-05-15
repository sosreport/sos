Maintainers checklist for releasing a new version or tag
========================================================

-  ideally week before the planned release date, write a last call for
   merge requests that want to get into the release

-  check if latest commit does not break some tests

-  optionally, run some own smoke tests on the current ``main``

-  do a commit bumping release, like
   https://github.com/sosreport/sos/commit/c1e0741844c8854e6d68389280700a688be515cf

   -  example commands for semi-automated change (need a manual review!)

::

   newvers=4.6.2  # populate accordingly
   oldvers=$(grep ^version docs/conf.py | cut -d\' -f2)
   logdate=$(date "+%a %b %d %Y")
   gituser="$(git config --get user.name) <$(git config --get user.email)>"

   sed -i "s/version = '${oldvers}'/version = '${newvers}'/1" docs/conf.py
   sed -i "s/release = '${oldvers}'/release = '${newvers}'/1" docs/conf.py

   sed -i "s/__version__ = \"${oldvers}\"/__version__ = \"${newvers}\"/1" sos/__init__.py

   sed -i "s/Version: ${oldvers}/Version: ${newvers}/1" sos.spec
   sed -i "/%changelog/a * ${logdate} ${gituser} = ${newvers}\n- New upstream release\n" sos.spec

   # when dch from devscripts package is present:
   DEBEMAIL="${gituser}" dch -v ${newvers} --distribution unstable "New upstream release" 
   # .. otherwise:
   debdate=$(date -R -u)

   ed -s debian/changelog << EOF
   0 i
   sos (${newvers}) unstable; urgency=medium

     * New upstream release

    -- ${gituser}  ${debdate}

   .
   w
   EOF

   git diff

   git add docs/conf.py sos/__init__.py sos.spec debian/changelog

-  in https://github.com/sosreport/sos/releases , draft a new release:

   -  Choose a tag *without* ``sos-`` prefix, i.e. just like 4.6.1 and
      not sos-4.6.1
   -  Release title = ``sos-<tag>`` (i.e. ``sos-4.6.1``)
   -  for the release text, follow structure from
      e.g. https://github.com/sosreport/sos/releases/tag/4.6.0

      -  ideally, insert there the “New Contributors” section from
         pregenerated release note text.

-  announce it with the same text on the
   `sos-devel <https://www.redhat.com/mailman/listinfo/sos-devel>`__
   mailing list
