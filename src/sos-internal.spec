%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

%define name sos-internal
%define version 1.0
%define release 0

Summary: Red Hat Support GPG private key
Name: %{name}
Version: %{version}
Release: %{release}%{?dist}
Group: Application/Tools

Source0: rhsupport.pub
Source1: rhsupport.key
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildArch: noarch
Url: http://hosted.fedoraproject.org/projects/sos

%description
Sos is a set of tools that gathers information about system
hardware and configuration. The information can then be used for
diagnostic purposes and debugging. Sos is commonly used to help
support technicians and developers.

%install
rm -rf ${RPM_BUILD_ROOT}
install -D -m600 %{SOURCE0} ${RPM_BUILD_ROOT}/usr/share/sos/rhsupport.pub
install -D -m644 %{SOURCE1} ${RPM_BUILD_ROOT}/usr/share/sos/rhsupport.key

%clean
rm -rf ${RPM_BUILD_ROOT}

%post
/usr/bin/gpg --import /usr/share/sos/rhsupport.pub
/usr/bin/gpg --allow-secret-key-import --import /usr/share/sos/rhsupport.key

%files
%defattr(-,root,root,-)
/usr/share/sos/rhsupport.pub
/usr/share/sos/rhsupport.key

%changelog
* Wed Sep  4 2007 Navid Sheikhol-Eslami <navid at redhat dot com> - 1.0
- the GPG key will be regenerated every time this package is built
