#
# Makefile for sos system support tools
#

NAME	= sos
VERSION = $(shell echo `awk '/^Version:/ {print $$2}' sos.spec`)
RELEASE = $(shell echo `awk '/^Release:/ {gsub(/\%.*/,""); print $2}' cas.spec`)
#RELEASE = 6
REPO = http://svn.fedorahosted.org/svn/sos
#SVNTAG	= r$(subst .,-,$(VERSION))_$(RELEASE)
SRCDIR = $(PWD)
# Needs to be changed to reflect
# your rpm development tree.
TOPDIR = $(HOME)/rpmbuild/SOURCES
TMPDIR = /tmp/$(NAME)-$(VERSION)
MANPAGE = $(PWD)/sosreport.1
SOURCE1 = $(PWD)/sos.conf
SOURCE3 = $(PWD)/gpgkeys/rhsupport.pub

all:

.PHONY: tarball install clean rpm

tarball: clean gpgkey
	@echo "Build Archive"
	@mkdir $(TMPDIR)
	@python setup.py sdist -d $(TMPDIR)
	@mkdir $(PWD)/dist
	@cp $(TMPDIR)/* $(PWD)/dist
	@echo " "
	@echo "The final archive is $(PWD)/dist/"

clean:
	@rm -fv *~ .*~ changenew ChangeLog.old $(NAME)-$(VERSION).tar.gz
	@rm -rfv {dist,build,sos.egg-info}
	@rm -rf MANIFEST
	@rm -rfv $(TMPDIR)
	@for i in `find . -iname *.pyc`; do \
		rm $$i; \
	done; \

rpm:
	@test -d $(TOPDIR) || mkdir -p $(TOPDIR)
	@mv dist/* $(TOPDIR)
	@test -f sos.spec
	rpmbuild -ba sos.spec

gpgkey:
	@echo "Building gpg key"
	@test -f gpgkeys/rhsupport.pub && echo "GPG key already exists." || \
	gpg --batch --gen-key gpgkeys/gpg.template
