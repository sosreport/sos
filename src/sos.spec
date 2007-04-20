%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: System Support Tools
Name: sos
Version: 1.3
Release: 3%{?dist}
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
%{_mandir}/man1/sosreport.1.gz
%doc README TODO

%changelog
* Mon Apr 16 2007 Steve Conklin <sconklin at redhat dot com> - 1.3-3
- including patches to fix the following:
- bz_219745 sosreport needs a man page
- bz_219667 sosreport does not terminate cleanly on ^C
- bz_233375 Make SOS flag the situation when running on a fully virtu...
- bz_234873 rhel5 sos needs to include rpm-va by default
- bz_219669 sosreport multi-threaded option sometimes fails
- bz_219671 RFE for sosreport - allow specification of plugins to be run
- bz_219672 RFE - show progress while sosreport is running
- bz_219673 Add xen information gathering to sosreport
- bz_219675 Collect information related to the new driver update model
- bz_219877 'Cancel' button during option selection only cancels sele...

* Tue Feb 20 2007 John Berninger <jwb at redhat dot com> - 1.3-2
- Add man page

* Fri Dec 15 2006 Steve Conklin <sconklin at redhat dot com> - 1.3-1
- really fixed bz_219654

* Fri Dec 15 2006 Steve Conklin <sconklin at redhat dot com> - 1.2-1
- fixed a build problem

* Fri Dec 15 2006 Steve Conklin <sconklin at redhat dot com> - 1.1-1
- Tighten permissions of tmp directory so only readable by creator bz_219657
- Don't print message 'Problem at path ...'  bz_219654
- Removed useless message bz_219670
- Preserve file modification times bz_219674
- Removed unneeded message about files on copyProhibitedList bz_219712

* Wed Aug 30 2006 Steve Conklin <sconklin at redhat dot com> - 1.0-1
- Seperated upstream and RPM versioning

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
