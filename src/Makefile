#
# Makefile for sos system support tools
#

NAME    = sos
VERSION = $(shell awk '/define version/ { print $$3 }' sos.spec)
RELEASE = $(shell awk '/define release/ { print $$3 }' sos.spec)
CVSTAG  = r$(subst .,-,$(VERSION)-$(RELEASE))
CVSROOT = $(shell cat CVS/Root)


all:

changelog:
	@rcs2log | sed "s|@.*redhat\.com|@redhat.com|" | sed "s|@.*redhat\.de|@redhat.com|" | sed "s|@redhat\.de|@redhat.com|" | sed "s|@@|@|" | \
	sed "s|/usr/local/CVS/$(NAME)/||g" | sed "s|/cvs/rhl/$(NAME)/||g" > changenew
	mv ChangeLog ChangeLog.old
	cat changenew ChangeLog.old > ChangeLog
	rm -f changenew

tag-archive:
	@cvs -Q tag -F $(CVSTAG)
	echo "$(CVSTAG)"

create-archive: tag-archive
	@rm -rf /tmp/$(NAME)
	@cd /tmp; cvs -Q -d $(CVSROOT) export -r$(CVSTAG) $(NAME) || echo GRRRrrrrr -- ignore [export aborted]
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
