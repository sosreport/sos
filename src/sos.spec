#NEEDSWORK:
#- Your upstream software release number is different from the rpm release
#number.  Upstream release is the rpm version.  rpm release would be how many
#times we've had to respin this version of the software for various reasons
#(build system changes, gcc changes, spec bug fixes, etc...)  The two should
#_not_ be tied together.
#- Changelog entry doesn't match release number.  (10 vs 11)
#- %setup section should have -q.

%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: System Support Tools
Name: sos
Version: 1.0
# change release in setup.py and this file
Release: 10%{?dist}
License: GPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
Requires: python >= 0:2.3
URL: http://sos.108.redhat.com
# Using local source tarball until this can be released to public CVS system
Source0: %{name}-%{version}.tar.bz2

%description
SOS is a set of tools that gathers information about system
hardware and configuration. The information can then be used for
diagnostic purposes and debugging. Sos is commonly used to help
support technicians and developers.

 
%prep
%setup -q

%build
python setup.py -q build

%install
rm -rf ${RPM_BUILD_ROOT}
# The python setup.py does the same thing as the make install in other packages
%{__python} setup.py -q install --root=${RPM_BUILD_ROOT}

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%{_sbindir}/sosreport
%dir %{python_sitelib}/sos/
%{python_sitelib}/sos/plugins
%{python_sitelib}/sos/plugintools.py*
%{python_sitelib}/sos/__init__.py*
%{python_sitelib}/sos/helpers.py*
%{python_sitelib}/sos/policyredhat.py*
%doc README TODO

%changelog
* Mon Aug 21 2006 Steve Conklin <sconklin at redhat dot com> - 0.1-11
- Code cleanup, fixed a regression in threading

* Mon Aug 14 2006 Steve Conklin <sconklin at redhat dot com> - 0.1-10
- minor bugfixes, added miltithreading option, setup now quiet

* Mon Jul 17 2006 Steve Conklin <sconklin at redhat dot com> - 0.1-9
- migrated to svn on 108.redhat.com, fixed a problem with command output linking in report

* Mon Jun 19 2006 Steve Conklin <sconklin at redhat dot com> - 0.1-6
- Added LICENSE file containing GPL

* Wed May 31 2006 Steve Conklin <sconklin at redhat dot com> - 0.1-5
- Added fixes to network plugin and prepped for Fedora submission

* Wed May 31 2006 John Berninger <jwb at redhat dot com> - 0.1-4
- Reconsolidated subpackages into one package per discussion with sconklin

* Mon May 22 2006 John Berninger <jwb at redhat dot com> - 0.1-3
- Added ftp, ldap, mail, named, samba, squid SOS plugins
- Fixed various errors in kernel and hardware plugins

* Mon May 22 2006 John Benringer <jwb at redhat dot com> - 0.1-2
- split off cluster plugin into subpackage
- correct file payload lists

* Mon May 22 2006 John Berninger <jwb at redhat dot com> - 0.1-1
- initial package build 
