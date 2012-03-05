#
# Makefile for sos system support tools
#

NAME	= sos
VERSION = $(shell echo `awk '/^Version:/ {print $$2}' sos.spec`)
RELEASE = $(shell echo `awk '/^Release:/ {gsub(/\%.*/,""); print $2}' sos.spec`)
REPO = http://github.com/sosreport

SUBDIRS = po sos sos/plugins sos/policies
PYFILES = $(wildcard *.py)
# OS X via brew
# MSGCAT = /usr/local/Cellar/gettext/0.18.1.1/bin/msgcat
MSGCAT = msgcat

# Default to Red Hat GPG template
GPG_TPL=rh

DIST_BUILD_DIR = dist-build
RPM_DEFINES = --define "_topdir %(pwd)/$(DIST_BUILD_DIR)" \
	--define "_builddir %{_topdir}" \
	--define "_rpmdir %{_topdir}" \
	--define "_srcrpmdir %{_topdir}" \
	--define "_specdir %{_topdir}" \
	--define "_sourcedir %{_topdir}"
RPM = rpmbuild
RPM_WITH_DIRS = $(RPM) $(RPM_DEFINES)
ARCHIVE_DIR = $(DIST_BUILD_DIR)/$(NAME)-$(VERSION)

ARCHIVE_NAME = sosreport.zip
SRC_BUILD = $(DIST_BUILD_DIR)/sdist
PO_DIR = $(SRC_BUILD)/sos/po
ZIP_DEST = $(SRC_BUILD)/$(ARCHIVE_NAME)

build:
	for d in $(SUBDIRS); do make -C $$d; [ $$? = 0 ] || exit 1 ; done

install: updateversion
	mkdir -p $(DESTDIR)/usr/sbin
	mkdir -p $(DESTDIR)/usr/share/man/man1
	mkdir -p $(DESTDIR)/usr/share/man/man5
	mkdir -p $(DESTDIR)/usr/share/$(NAME)/extras
	@gzip -c man/en/sosreport.1 > sosreport.1.gz
	@gzip -c man/en/sos.conf.5 > sos.conf.5.gz
	mkdir -p $(DESTDIR)/etc
	install -m755 sosreport $(DESTDIR)/usr/sbin/sosreport
	install -m644 sosreport.1.gz $(DESTDIR)/usr/share/man/man1/.
	install -m644 sos.conf.5.gz $(DESTDIR)/usr/share/man/man5/.
	install -m644 LICENSE README $(DESTDIR)/usr/share/$(NAME)/.
	install -m644 $(NAME).conf $(DESTDIR)/etc/$(NAME).conf
	install -m644 gpgkeys/rhsupport.pub $(DESTDIR)/usr/share/$(NAME)/.
	for d in $(SUBDIRS); do make DESTDIR=`cd $(DESTDIR); pwd` -C $$d install; [ $$? = 0 ] || exit 1; done

updateversion:
	sed 's/@SOSVERSION@/$(VERSION)/g' sos/__init__.py.in > sos/__init__.py
  
$(NAME)-$(VERSION).tar.gz: clean gpgkey
	@mkdir -p $(ARCHIVE_DIR)
	@tar -cv sosreport sos doc man po sos.conf LICENSE README sos.spec Makefile | tar -x -C $(ARCHIVE_DIR)
	@mkdir -p $(ARCHIVE_DIR)/gpgkeys
	@cp gpgkeys/$(GPG_TPL)support.pub $(ARCHIVE_DIR)/gpgkeys/.
	@tar Ccvzf $(DIST_BUILD_DIR) $(DIST_BUILD_DIR)/$(NAME)-$(VERSION).tar.gz $(NAME)-$(VERSION)

clean:
	@rm -fv *~ .*~ changenew ChangeLog.old $(NAME)-$(VERSION).tar.gz sosreport.1.gz sos.conf.5.gz
	@rm -rf rpm-build
	@for i in `find . -iname *.pyc`; do \
		rm $$i; \
	done; \
	for d in $(SUBDIRS); do make -C $$d clean ; done

srpm: clean $(NAME)-$(VERSION).tar.gz
	$(RPM_WITH_DIRS) -ts $(DIST_BUILD_DIR)/$(NAME)-$(VERSION).tar.gz

rpm: clean $(NAME)-$(VERSION).tar.gz
	$(RPM_WITH_DIRS) -tb $(DIST_BUILD_DIR)/$(NAME)-$(VERSION).tar.gz

gpgkey:
	@echo "Building gpg key"
	@test -f gpgkeys/$(GPG_TPL)support.pub && echo "GPG key already exists." || \
	gpg --batch --gen-key gpgkeys/$(GPG_TPL).template

po: clean
	mkdir -p $(PO_DIR)
	for po in `ls po/*.po`; do \
		$(MSGCAT) -p -o $(PO_DIR)/sos_$$(basename $$po | awk -F. '{print $$1}').properties $$po; \
	done; \

	cp $(PO_DIR)/sos_en.properties $(PO_DIR)/sos_en_US.properties
	cp $(PO_DIR)/sos_en.properties $(PO_DIR)/sos.properties

as7: po updateversion
	cp -r sos/* $(SRC_BUILD)/sos/
	find $(SRC_BUILD)/sos/plugins/ -not -name "*as7.py" -not -name "*__init__.py" -type f -delete

zip: po
	zip -r $(ZIP_DEST) sos
	zip -r $(ZIP_DEST) __run__.py
	cd $(SRC_BUILD) && zip -r $(ARCHIVE_NAME) sos
	cd $(SRC_BUILD) && rm -rf sos

test:
	@for test in `ls tests/*test*.py`; do \
		echo $$test; \
		PYTHONPATH=`pwd` python $$test; \
	done; \

nose:
	nosetests -v --with-cover --cover-package=sos --cover-html
