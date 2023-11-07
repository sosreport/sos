#!/bin/bash
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
# A quick port of the travis tests to bash, requires root
# TODO
# * look into using a framework..
# * why --dry-run fails?
# * why --experimental fails?
# * make it better validate archives and contents

PYTHON=${1:-/usr/bin/python3}
SOSPATH=${2:-./bin/sos report --batch --tmp-dir=/tmp }

NUMOFFAILURES=0
summary="\nSummary\n"
FAIL_LIST=""

run_expecting_success () {
    #$1 - is command options
    #$2 - kind of check to do, so far only extract
    FAIL=false
    # Make sure clean
    rm -f /dev/shm/stderr /dev/shm/stdout /tmp/sosreport*.tar.*
    rm -rf /tmp/sosreport_test/
    
    start=`date +%s`
    echo "######### RUNNING $1 #########"
    $PYTHON $SOSPATH $1 2> /dev/shm/stderr 1> /dev/shm/stdout
    
    if [ $? -eq 0 ]; then
      echo "### Success"
    else
      echo "!!! FAILED !!!"
      add_failure "$1 failed during execution"
    fi

    end=`date +%s`
    runtime=$((end-start))
    echo "#### Sos Total time (seconds):" $runtime

    if [ -s /dev/shm/stderr ]; then
       add_failure "test generated stderr output, see above"
       echo "### start stderr"
       cat /dev/shm/stderr
       echo "### end stderr"
    fi
    
    echo "### start stdout"
    cat /dev/shm/stdout
    echo "### end stdout"

    if [ "extract" = "$2" ]; then
        echo "### start extraction"
        rm -f /tmp/sosreport*sha256
        mkdir /tmp/sosreport_test/
        tar xfa /tmp/sosreport*.tar* -C /tmp/sosreport_test --strip-components=1
        if [ -s /tmp/sosreport_test/sos_logs/*errors.txt ]; then
            FAIL=true
            echo "!!! FAILED !!!"
            add_failure "Test $1 generated errors"
            echo "#### *errors.txt output"
            ls -alh /tmp/sosreport_test/sos_logs/
            cat /tmp/sosreport_test/sos_logs/*errors.txt
        fi
        echo "### stop extraction"
    fi

    echo "######### DONE WITH $1 #########"

    if $FAIL; then
      NUMOFFAILURES=$(($NUMOFFAILURES + 1))
      return 1
    else
      return 0
    fi
}

update_summary () {
    size="$(grep Size /dev/shm/stdout)"
    size="$(echo "${size:-"Size 0.00MiB"}")"
    summary="${summary} \n failures ${FAIL} \t time ${runtime} \t ${size} \t ${1} "
}

update_failures () {
    if $FAIL; then
      NUMOFFAILURES=$(($NUMOFFAILURES + 1))
    fi
}

add_failure () {
    FAIL=true
    echo "!!! TEST FAILED: $1 !!!"
    FAIL_LIST="${FAIL_LIST}\n \t ${FUNCNAME[1]}: \t\t ${1}"
}

# Test a no frills run with verbosity and make sure the expected items exist
test_normal_report () {
    cmd="-vvv"
    # get a list of initial kmods loaded
    kmods=( $(lsmod | cut -f1 -d ' ' | sort) )
    run_expecting_success "$cmd" extract
    if [ $? -eq 0 ]; then
        if [ ! -f /tmp/sosreport_test/sos_reports/sos.html ]; then
            add_failure "did not generate html reports"
        fi
        if [ ! -f /tmp/sosreport_test/sos_reports/manifest.json ]; then
            add_failure "did not generate manifest.json"
        fi
        if [ ! -f /tmp/sosreport_test/free ]; then
            add_failure "did not create free symlink in archive root"
        fi
        if [ ! "$(grep "DEBUG" /tmp/sosreport_test/sos_logs/sos.log)" ]; then
            add_failure "did not find debug logging when using -vvv"
        fi
        # new list, see if we added any
        new_kmods=( $(lsmod | cut -f1 -d ' ' | sort) )
        if [ "$(printf '%s\n' "${kmods[@]}" "${new_kmods[@]}" | sort | uniq -u)" ]; then
            add_failure "new kernel modules loaded during execution"
            echo "$(printf '%s\n' "${kmods[@]}" "${new_kmods[@]}" | sort | uniq -u)"
        fi
        update_failures
    update_summary "$cmd"
    fi
}

# Test for correctly skipping html generation, and label setting
test_noreport_label_only () {
    cmd="--no-report --label TEST -o hardware"
    run_expecting_success "$cmd" extract
    if [ $? -eq 0 ]; then
        if [ -f /tmp/sosreport_test/sos_reports/sos.html ]; then
            add_failure "html report generated when --no-report used"
        fi
        if [ ! $(grep /tmp/sosreport-*TEST* /dev/shm/stdout) ]; then
            add_failure "no label set on archive"
        fi
        count=$(find /tmp/sosreport_test/sos_commands/* -type d | wc -l)
        if [[ "$count" -gt 1 ]]; then
            add_failure "more than one plugin ran when using -o hardware"
        fi
        update_failures
    fi
    update_summary "$cmd"
}

# test using mask
test_mask () {
    cmd="--mask"
    run_expecting_success "$cmd" extract
    if [ $? -eq 0 ]; then
        if [ ! $(grep host0 /tmp/sosreport_test/hostname) ]; then
            add_failure "hostname not obfuscated with --mask"
        fi
        # we don't yet support binary obfuscation, so skip binary matches
        if [ "$(grep -rI `hostname` /tmp/sosreport_test/*)" ]; then
            add_failure "hostname not obfuscated in all places"
            echo "$(grep -rI `hostname` /tmp/sosreport_test/*)"
        fi
        # only tests first interface
        mac_addr=$(cat /sys/class/net/$(ip route show default | awk '/default/ {print $5}')/address)
        if [ "$(grep -rI $mac_addr /tmp/sosreport_test/*)" ]; then
            add_failure "MAC address not obfuscated in all places"
            echo "$(grep -rI $mac_addr /tmp/sosreport_test/*)"
        fi
        # only tests first interface
        ip_addr=$(ip route show default | awk '/default/ {print $3}')
        if [ "$(grep -rI $ip_addr /tmp/sosreport_test/*)" ]; then
            add_failure "IP address not obfuscated in all places"
            echo "$(grep -rI $ip_addr /tmp/sosreport_test/*)"
        fi
        update_failures
    fi
    update_summary "$cmd"
}

# test log-size, env vars, and compression type
test_logsize_env_gzip () {
    cmd="--log-size 0 --no-env-vars -z gzip"
    run_expecting_success "$cmd" extract
    if [ $? -eq 0 ]; then
        if [ -f /tmp/sosreport_test/environment ]; then
            add_failure "env vars captured when using --no-env-vars"
        fi
        if [ ! $(grep /tmp/sosreport*.gz /dev/shm/stdout) ]; then
            add_failure "archive was not gzip compressed using -z gzip"
        fi
        update_failures
    fi
    update_summary "$cmd"
}

# test plugin enablement, plugopts and at the same time ensure our list option parsing is working
test_enable_opts_postproc () {
    cmd="-e opencl -v -k kernel.with-timer,libraries.ldconfigv --no-postproc"
    run_expecting_success "$cmd" extract
    if [ $? -eq 0 ]; then
        if [ ! "$(grep "opencl" /dev/shm/stdout)" ]; then
            add_failure "force enabled plugin opencl did not run"
        fi
        if [ ! -f /tmp/sosreport_test/proc/timer* ]; then
            add_failure "/proc/timer* not captured when using -k kernel.with-timer"
        fi
        if [ ! -f /tmp/sosreport_test/sos_commands/libraries/ldconfig_-v* ]; then
            add_failure "ldconfig -v not captured when using -k libraries.ldconfigv"
        fi
        if [ "$(grep "substituting" /tmp/sosreport_test/sos_logs/sos.log)" ]; then
            add_failure "post-processing ran while using --no-post-proc"
        fi

        update_failures
    update_summary "$cmd"
    fi
}

# test if --build and --threads work properly
test_build_threads () {
    cmd="--build -t1 -o host,kernel,filesys,hardware,date,logs"
    run_expecting_success "$cmd"
    if [ $? -eq 0 ]; then
        if [ ! "$(grep "Your sosreport build tree" /dev/shm/stdout)" ]; then
            add_failure "did not save the build tree"
        fi
        if [ $(grep "Finishing plugins" /dev/shm/stdout) ]; then
            add_failure "did not limit threads when using --threads 1"
        fi
        update_failures
        update_summary "$cmd"
    fi
}

# If /etc/sos/sos.conf doesn't exist let's just make it
if [ -f /etc/sos/sos.conf ]; then
   echo "/etc/sos/sos.conf already exists"
else
   echo "Creating /etc/sos.conf"
   mkdir /etc/sos
   touch /etc/sos/sos.conf
fi


# Runs not generating sosreports
run_expecting_success " -l"; update_summary "List plugins"
run_expecting_success " --list-presets"; update_summary "List presets"
run_expecting_success " --list-profiles"; update_summary "List profiles"

# Runs generating sosreports
# TODO:
# - find a way to test if --since is working
test_build_threads
test_normal_report
test_enable_opts_postproc
test_noreport_label_only
test_logsize_env_gzip
test_mask

echo -e $summary

if [ $NUMOFFAILURES -gt 0 ]; then
  echo -e "\nTests Failed: $NUMOFFAILURES\nFailures within each test:"
  echo -e $FAIL_LIST
  exit 1
else
  echo "Everything worked!"
  exit 0
fi

# vim: set et ts=4 sw=4 :
