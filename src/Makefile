#
# Makefile for sos system support tools
#

NAME    = sos
VERSION = $(shell grep -e 'version = ' setup.py |cut -d \' -f 2)
REPO = https://sos.108.redhat.com/svn/sos
SVNTAG  = r$(subst .,-,$(VERSION))


all:

.PHONY: tag-release tarball release install version clean

diff-tag-release:
	svn diff $(REPO)/trunk/src $(REPO)/tags/$(SVNTAG)

tag-release:
	@svn list $(REPO)/tags/$(SVNTAG)/Makefile > /dev/null && \
	( \
		echo "The repository already contains a tag for version $(VERSION)"; \
		exit 1; \
	)
	@svn copy $(REPO)/trunk/src $(REPO)/tags/$(SVNTAG) \
	-m "Tagging the $(SVNTAG) release of the sos project"
	@echo "Tagged as $(SVNTAG)"

# if we don't compress them, rpmbuild does, and this breaks things
manpages: sosreport.1
	@gzip -c sosreport.1 > sosreport.1.gz

tarball: clean manpages
	@echo "Creating an archive from HEAD of development"
	@rm -rf /tmp/$(NAME)
	@svn export -q $(REPO)/trunk/src     /tmp/$(NAME) \
	 || echo GRRRrrrrr -- ignore [export aborted]
	@mv /tmp/$(NAME) /tmp/$(NAME)-$(VERSION)
	@cd /tmp/$(NAME)-$(VERSION); gzip -c sosreport.1 > sosreport.1.gz
	@cd /tmp; tar --bzip2 -cSpf $(NAME)-$(VERSION).tar.bz2 $(NAME)-$(VERSION)
	@rm -rf /tmp/$(NAME)-$(VERSION)
	@cp /tmp/$(NAME)-$(VERSION).tar.bz2 .
	@rm -f /tmp/$(NAME)-$(VERSION).tar.bz2
	@echo " "
	@echo "The final archive is ./$(NAME)-$(VERSION).tar.bz2."

release: clean manpages
	@svn list $(REPO)/tags/$(SVNTAG)/Makefile > /dev/null && \
	( \
		@echo "There is no tag in the repository for this version, must be tagged before release"; \
		exit 1; \
	)
	@echo "Creating an archive from tag $(SVNTAG)"
	@rm -rf /tmp/$(NAME)
	@svn export -q $(REPO)/tags/$(SVNTAG)     /tmp/$(NAME) \
	 || echo GRRRrrrrr -- ignore [export aborted]
	@mv /tmp/$(NAME) /tmp/$(NAME)-$(VERSION)
	@cd /tmp/$(NAME)-$(VERSION); gzip -c sosreport.1 > sosreport.1.gz
	@cd /tmp; tar --bzip2 -cSpf $(NAME)-$(VERSION).tar.bz2 $(NAME)-$(VERSION)
	@rm -rf /tmp/$(NAME)-$(VERSION)
	@cp /tmp/$(NAME)-$(VERSION).tar.bz2 .
	@rm -f /tmp/$(NAME)-$(VERSION).tar.bz2
	@echo " "
	@echo "The final archive is ./$(NAME)-$(VERSION).tar.bz2."

install:
	python setup.py install

version:
	@echo "The version is $(NAME)-$(VERSION)"

clean:
	@rm -fv *~ .*~ changenew ChangeLog.old $(NAME)-$(VERSION).tar.bz2 sosreport.1.gz

rpm:
	python setup.py bdist_rpm
