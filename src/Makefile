#
# Makefile for sos system support tools
#

NAME    = sos
VERSION = $(shell awk '/Version/ { print $$2 }' sos.spec)
REPO = https://sos.108.redhat.com/svn/sos
SVNTAG  = r$(subst .,-,$(VERSION))
SVN_TAG_CONTENTS := $(shell svn list $(REPO)/tags/$(SVNTAG)/Makefile)


all:

.PHONY: tag-release tarball release install version clean

tag-release:
ifeq ($(strip $(SVN_TAG_CONTENTS)), Makefile)
	@echo "The repository already contains a tag for version $(VERSION)"
else
	@svn copy $(REPO)/trunk/src $(REPO)/tags/$(SVNTAG) \
	-m "Tagging the $(SVNTAG) release of the sos project"
	@echo "$(SVNTAG)"
	@svn update ../../tags
endif

# if we don't compress them, rpmbuild does, and this breaks things
manpages: sosreport.1
	@gzip -c sosreport.1 > sosreport.1.gz

tarball: clean manpages
	@echo "Creating an archive from HEAD of development"
	@rm -rf /tmp/$(NAME)
	@svn export -q $(REPO)/trunk/src     /tmp/$(NAME) \
	 || echo GRRRrrrrr -- ignore [export aborted]
	@mv /tmp/$(NAME) /tmp/$(NAME)-$(VERSION)
	@cd /tmp; tar --bzip2 -cSpf $(NAME)-$(VERSION).tar.bz2 $(NAME)-$(VERSION)
	@rm -rf /tmp/$(NAME)-$(VERSION)
	@cp /tmp/$(NAME)-$(VERSION).tar.bz2 .
	@rm -f /tmp/$(NAME)-$(VERSION).tar.bz2
	@echo " "
	@echo "The final archive is ./$(NAME)-$(VERSION).tar.bz2."

release: clean tag-release manpages
ifeq ($(strip $(SVN_TAG_CONTENTS)), Makefile)
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
else
	@echo "There is no tag in the repository for this version, must be tagged before release"
endif

install:
	python setup.py install

version:
	@echo "The version is $(NAME)-$(VERSION)"

clean:
	@rm -fv *~ .*~ changenew ChangeLog.old $(NAME)-$(VERSION).tar.bz2 sosreport.1.gz
