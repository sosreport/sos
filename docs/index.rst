SoS
===

Sos is an extensible, portable, support data collection tool primarily aimed at Linux distributions and other UNIX-like operating systems.

This is the SoS developer documentation, for user documentation refer to:

https://github.com/sosreport/sos/wiki

This project is hosted at:

https://github.com/sosreport/sos

For the latest version, to contribute, and for more information, please visit the project pages or join the mailing list.

To clone the current main (development) branch run:

.. code::

    git clone git@github.com:sosreport/sos.git

Reporting bugs
--------------

Please report bugs by opening an issue in the GitHub Issue Tracker.

Patches and pull requests
-------------------------

Patches can be submitted via the mailing list or as GitHub pull requests. If using GitHub please make sure your branch applies to the current main branch as a 'fast forward' merge (i.e. without creating a merge commit). Use the git rebase command to update your branch to the current main branch if necessary.

Documentation
=============

User and API `documentation <https://sos.readthedocs.org/en/latest/index.html>`_ is automatically generated using `Sphinx <https://www.sphinx-doc.org/>`_ and `Read the Docs <https://readthedocs.org/>`_.

Wiki
----

 :doc:`How to write a plugin <user_docs/writing_a_plugin>`

 :doc:`How to write a policy <user_docs/writing_a_policy>`

 :doc:`Plugin options <user_docs/plugin_options>`

To help get your changes merged quickly with as few revisions as possible please refer to the :doc:`Contributor Guidelines <user_docs/contribution_guidelines>` when submitting patches or pull requests.

Installation
============

Manual Installation
-------------------

.. code::

    python3 setup.py install

Pre-built Packaging
-------------------

Fedora/RHEL users install via dnf:

``dnf install sos``

Debian (11 and 12) users install via apt:

``apt install sosreport``

Debian (13 and above) users install via apt:

``apt install sos``

Ubuntu (14.04 LTS to 24.04 LTS) users install via apt:

``sudo apt install sosreport``

Ubuntu (26.04 LTS and above) users install via apt:

``sudo apt install sos``

Independent packaging is provided in the snap ecosystem, and users install via snap:

``snap install sosreport --classic``

User Docs
=========

.. toctree::
   :glob:
   :titlesonly:

   user_docs/*

API Reference
=============

.. toctree::
   :glob:
   :titlesonly:

   dev_docs/*
