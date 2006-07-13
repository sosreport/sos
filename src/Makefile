#
# Makefile for sos system support tools
#

NAME    = sos
VERSION = $(shell awk '/define version/ { print $$3 }' sos.spec)
RELEASE = $(shell awk '/define release/ { print $$3 }' sos.spec)
REPO = https://sos.108.redhat.com/svn/sos
SVNTAG  = r$(subst .,-,$(VERSION)-$(RELEASE))
CVSROOT = $(shell cat CVS/Root)


all:

tag-archive:
	@svn copy $(REPO)/trunk/src $(REPO)/tags/$(SVNTAG) \
	-m "Tagging the $(SVNTAG) release of the sos project"
	@echo "$(SVNTAG)"

create-archive: tag-archive
	@rm -rf /tmp/$(NAME)
	@svn export $(REPO)/tags/$(SVNTAG)/src /tmp/$(NAME) \
	 || echo GRRRrrrrr -- ignore [export aborted]
	@mv /tmp/$(NAME) /tmp/$(NAME)-$(VERSION)
	@cd /tmp; tar --bzip2 -cSpf $(NAME)-$(VERSION).tar.bz2 $(NAME)-$(VERSION)
	@rm -rf /tmp/$(NAME)-$(VERSION)
	@cp /tmp/$(NAME)-$(VERSION).tar.bz2 .
	@rm -f /tmp/$(NAME)-$(VERSION).tar.bz2
	@echo " "
	@echo "The final archive is ./$(NAME)-$(VERSION).tar.bz2."

archive: clean tag-archive create-archive

install:
	python setup.py install

version:
	@echo "The version is $(NAME)-$(VERSION)-$(RELEASE)"


clean:
	@rm -fv *~ .*~ changenew ChangeLog.old $(NAME)-$(VERSION)-$(RELEASE).tar.bz2
