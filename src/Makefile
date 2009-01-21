#
# Makefile for sos system support tools
#

NAME	= sos
VERSION = 1.8
#RELEASE = 6
REPO = http://svn.fedorahosted.org/svn/sos
#SVNTAG	= r$(subst .,-,$(VERSION))_$(RELEASE)
SRCDIR = $(PWD)
# Needs to be changed to reflect
# your rpm development tree.
TOPDIR = $(HOME)/redhat/$(NAME)
TMPDIR = /tmp/$(NAME)-$(VERSION)
MANPAGE = $(PWD)/sosreport.1
SOURCE1 = $(PWD)/sos.conf
SOURCE2 = $(PWD)/sosreport.1.gz
SOURCE3 = $(PWD)/gpgkeys/rhsupport.pub

all:

.PHONY: tarball install clean rpm

tarball: clean mo gpgkey
	@echo "Build Archive"
	@test -f $(SOURCE2) || gzip -c $(MANPAGE) > $(SOURCE2)
	@mkdir $(TMPDIR)
	@python setup.py sdist -d $(TMPDIR)
	@mkdir $(PWD)/dist
	@cp $(TMPDIR)/* $(PWD)/dist
	@echo " "
	@echo "The final archive is $(PWD)/dist/"

install:gpgkey mo
	python setup.py install
	@rm -rf build/lib

clean:
	@rm -fv *~ .*~ changenew ChangeLog.old $(NAME)-$(VERSION).tar.gz
	@rm -rfv {dist,build}
	@rm -rf MANIFEST
	@rm -rfv $(TMPDIR)
	@rm -rf {$(SOURCE2),$(SOURCE3)}
	@for i in `ls po`; do \
		if [ -d po/$$i ]; then \
			rm -rf po/$$i; \
		fi; \
	done; \

# TODO: This needs work
internal-rpm: gpgkey
	@test -f sos-internal.spec
	@mkdir -p $(TOPDIR)/SOURCES $(TOPDIR)/SRPMS $(TOPDIR)/RPMS $(TOPDIR)/BUILD $(SRCDIR)/dist
	cp gpgkeys/rhsupport.pub gpgkeys/rhsupport.key $(TOPDIR)/SOURCES

#	this builds an RPM from the current working copy
	@cd $(TOPDIR)/BUILD ; \
	rm -rf $(NAME)-$(VERSION) ; \
	ln -s $(SRCDIR) $(NAME)-$(VERSION) ; \
	tar --gzip --exclude=.svn --exclude=svn-commit.tmp --exclude=$(NAME)-$(VERSION)/build --exclude=$(NAME)-$(VERSION)/dist \
	--exclude gpgkeys/rhsupport.pub --exclude gpgkeys/rhsupport.key \
	-chSpf $(TOPDIR)/SOURCES/$(NAME)-$(VERSION).tar.gz $(NAME)-$(VERSION) ; \
	rm -f $(NAME)-$(VERSION)

	rpmbuild -ba --define="_topdir $(TOPDIR)" sos-internal.spec
	@mv $(TOPDIR)/RPMS/noarch/$(NAME)-internal-*.rpm $(TOPDIR)/SRPMS/$(NAME)-internal-*.rpm dist/
	cp gpgkeys/rhsupport.key dist/

rpm: tarball
	@test -d $(TOPDIR) || mkdir -p $(TOPDIR)
	@mv dist/* $(TOPDIR)
	@test -f sos.spec
	rpmbuild -ba sos.spec

pot:
	python tools/pygettext.py -o po/sos.pot sosreport lib/sos/policyredhat.py

mo:
	@echo "Generating mo files"
	@for i in `ls po`; do \
		if [ $$i != 'sos.pot' ]; then \
			mkdir po/$${i%.po}; \
			python tools/msgfmt.py -o po/$${i%.po}/sos.mo po/$$i; \
		fi; \
	done; \

gpgkey:
	@echo "Building gpg key"
	@test -f gpgkeys/rhsupport.pub && echo "GPG key already exists." || \
	gpg --batch --gen-key gpgkeys/gpg.template
