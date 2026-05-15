# Copyright (C) 2022 Red Hat, Inc.
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


def mask_openstack_ini_secrets(apply_regex_sub):
    """Mask common OpenStack INI-style secret values.

    The ``apply_regex_sub`` argument should be a callable that accepts a
    ``regexp`` and ``subst`` string and applies the substitution to the
    desired file set.
    """
    protect_keys = [
        ".*_key",
        ".*_pass(wd|word)?",
        "password",
        "metadata_proxy_shared_secret",
        "rbd_secret_uuid",
    ]
    connection_keys = ["connection", "sql_connection", "transport_url"]
    join_con_keys = "|".join(connection_keys)

    apply_regex_sub(
        fr"(^\s*({'|'.join(protect_keys)})\s*=\s*)(.*)",
        r"\1*********"
    )
    apply_regex_sub(
        fr"(^\s*({join_con_keys})\s*=\s*(.*)://(\w*):)(.*)(@(.*))",
        r"\1*********\6"
    )
