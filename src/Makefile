#
# Makefile for sos system support tools
#

NAME    = sos
VERSION = $(shell awk '/^%define version / { print $$3 }' sos.spec)
REPO = https://sos.108.redhat.com/svn/sos
SVNTAG  = r$(subst .,-,$(VERSION))
SRCDIR = $(PWD)
TOPDIR = $(PWD)/build/rpm-$(NAME)-$(VERSION)


all:

.PHONY: tag-release tarball release install version clean

diff-tag:
	svn diff $(REPO)/trunk/src $(REPO)/tags/$(SVNTAG)

tag:
	@if ( svn list $(REPO)/tags/$(SVNTAG)/Makefile &> /dev/null ); then \
		echo "The repository already contains a tag for version $(VERSION)"; \
		exit 1; \
	fi
	@svn copy $(REPO)/trunk/src $(REPO)/tags/$(SVNTAG) \
	-m "Tagging the $(SVNTAG) release of the sos project"
	@echo "Tagged as $(SVNTAG)"

tag-force:
	@echo svn del $(REPO)/tags/$(SVNTAG)
	@echo make diff-tag

tarball: clean
	@echo "Creating an archive from HEAD of development"
	@rm -rf /tmp/$(NAME)
	@svn export -q $(REPO)/trunk/src     /tmp/$(NAME) \
	 || echo GRRRrrrrr -- ignore [export aborted]
	@mv /tmp/$(NAME) /tmp/$(NAME)-$(VERSION)
	@cd /tmp; tar --bzip2 -cSpf $(NAME)-$(VERSION).tar.bz2 $(NAME)-$(VERSION)
	@rm -rf /tmp/$(NAME)-$(VERSION)
	@mv /tmp/$(NAME)-$(VERSION).tar.bz2 .
	@echo " "
	@echo "The final archive is ./$(NAME)-$(VERSION).tar.bz2."

release: clean
	@if ( ! svn list $(REPO)/tags/$(SVNTAG)/Makefile &> /dev/null ); then \
		echo "There is no tag in the repository for this version, must be tagged before release"; \
		exit 1; \
	fi
	@echo "Creating an archive from tag $(SVNTAG)"
	@rm -rf /tmp/$(NAME)
	@svn export -q $(REPO)/tags/$(SVNTAG)     /tmp/$(NAME) \
	 || echo GRRRrrrrr -- ignore [export aborted]
	@mv /tmp/$(NAME) /tmp/$(NAME)-$(VERSION)
	@cd /tmp; tar --bzip2 -cSpf $(NAME)-$(VERSION).tar.bz2 $(NAME)-$(VERSION)
	@rm -rf /tmp/$(NAME)-$(VERSION)
	@cp /tmp/$(NAME)-$(VERSION).tar.bz2 .
	@rm -f /tmp/$(NAME)-$(VERSION).tar.bz2
	@echo " "
	@echo "The final archive is ./$(NAME)-$(VERSION).tar.bz2."

install:mo
	python setup.py install
	@rm -rf build/lib

version:
	@echo "The version is $(NAME)-$(VERSION)"

clean:
	@rm -fv *~ .*~ changenew ChangeLog.old $(NAME)-$(VERSION).tar.bz2 sosreport.1.gz
	@rm -rfv build/*

rpm:	mo
	@test -f sos.spec
	@mkdir -p $(TOPDIR)/SOURCES $(TOPDIR)/SRPMS $(TOPDIR)/RPMS $(TOPDIR)/BUILD $(SRCDIR)/dist

#	this builds an RPM from the current working copy
	@cd $(TOPDIR)/BUILD ; \
	rm -rf $(NAME)-$(VERSION) ; \
	ln -s $(SRCDIR) $(NAME)-$(VERSION) ; \
	tar --gzip --exclude=.svn --exclude=svn-commit.tmp --exclude=$(NAME)-$(VERSION)/build --exclude=$(NAME)-$(VERSION)/dist \
	-chSpf $(TOPDIR)/SOURCES/$(NAME)-$(VERSION).tar.gz $(NAME)-$(VERSION) ; \
	rm -f $(NAME)-$(VERSION)

#	this builds an RPM from HEAD
#	@rm -rf $(TOPDIR)/BUILD/$(NAME)-$(VERSION)
#	@svn export -q $(REPO)/trunk/src $(TOPDIR)/BUILD/$(NAME)-$(VERSION)
#	@cd $(TOPDIR)/BUILD ; tar --gzip -cSpf $(TOPDIR)/SOURCES/$(NAME)-$(VERSION).tar.gz $(NAME)-$(VERSION); rm -rf $(NAME)-$(VERSION)

	rpmbuild -ba --define="_topdir $(TOPDIR)" sos.spec
	@mv $(TOPDIR)/RPMS/noarch/$(NAME)-$(VERSION)*.rpm $(TOPDIR)/SRPMS/$(NAME)-$(VERSION)*.rpm $(TOPDIR)/SOURCES/$(NAME)-$(VERSION).tar.gz dist/

pot:
	python tools/pygettext.py -o locale/sos.pot sosreport

mo:
	python tools/msgfmt.py locale/*/LC_MESSAGES/sos.po
