NAME=sos

all:
	echo "Nothing to build"

install:
	mkdir -p $(DESTDIR)/usr/share/$(NAME)/testsuite/config
	mkdir -p $(DESTDIR)/usr/share/$(NAME)/testsuite/$(NAME).test
	install -m644 *.exp $(DESTDIR)/usr/share/$(NAME)/testsuite/.
	install -m644 config/unix.exp $(DESTDIR)/usr/share/$(NAME)/testsuite/config/.
	install -m644 $(NAME).test/*.exp $(DESTDIR)/usr/share/$(NAME)/testsuite/$(NAME).test/.

clean:
