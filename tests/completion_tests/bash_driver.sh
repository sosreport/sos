#!/bin/bash
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
#
# Simulate bash completion of one or more sos command lines.
#
# usage: bash_driver.sh [--no-bash-completion] SCRIPT SOS_BIN LINE...
#
# Each LINE is the text before the cursor, without the leading `sos`. For each
# LINE, a '### LINE' header is printed, followed by the resulting COMPREPLY.

if [[ $1 == --no-bash-completion ]]; then
    shift
elif [[ -f /usr/share/bash-completion/bash_completion ]]; then
    source /usr/share/bash-completion/bash_completion
fi
source "$1"
sos_bin=$2
shift 2

# compopt only works while readline is completing, which is not the case here
compopt() { :; }

for args in "$@"; do
    COMP_LINE="$sos_bin $args"
    COMP_POINT=${#COMP_LINE}
    # split words as readline does with the default COMP_WORDBREAKS, where a
    # trailing '=' or ':' is the current word
    read -ra COMP_WORDS <<<"$(sed 's/[=:]/ & /g' <<<"$COMP_LINE")"
    if [[ $COMP_LINE == *" " ]]; then
        COMP_WORDS+=("")
    fi
    COMP_CWORD=$((${#COMP_WORDS[@]} - 1))
    COMPREPLY=()
    _comp_cmd_sos sos "${COMP_WORDS[COMP_CWORD]}" \
        "${COMP_WORDS[COMP_CWORD - 1]}"
    echo "### $args"
    printf '%s\n' "${COMPREPLY[@]}"
done
