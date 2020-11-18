# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
#/bin/bash
# A quick port of the travis tests to bash, requires root
# TODO
# * look into using a framework..
# * why --dry-run fails?
# * why --experimental fails?
# * make it better validate archives and contents

PYTHON=${1:-/usr/bin/python3}
SOSPATH=${2:-./bin/sos report}

NUMOFFAILURES=0
summary="Summary\n"

run_expecting_sucess () {
    #$1 - is command options
    #$2 - kind of check to do, so far only extract
    FAIL=false
    # Make sure clean
    rm -f /dev/shm/stderr /dev/shm/stdout /var/tmp/sosreport*.tar.*
    rm -rf /var/tmp/sosreport_test/
    
    start=`date +%s`
    echo "######### RUNNING $1 #########"
    $PYTHON $SOSPATH $1 2> /dev/shm/stderr 1> /dev/shm/stdout
    
    if [ $? -eq 0 ]; then
      echo "### Success"
    else
      echo "!!! FAILED !!!"
      FAIL=true
    fi

    end=`date +%s`
    runtime=$((end-start))
    echo "#### Sos Total time (seconds):" $runtime

    if [ -s /dev/shm/stderr ]; then
       FAIL=true
       echo "!!! FAILED !!!"
       echo "### start stderr"
       cat /dev/shm/stderr
       echo "### end stderr"
    fi
    
    echo "### start stdout"
    cat /dev/shm/stdout
    echo "### end stdout"

    if [ "extract" = "$2" ]; then
        echo "### start extraction"
        rm -f /var/tmp/sosreport*md5
        mkdir /var/tmp/sosreport_test/
        tar xfa /var/tmp/sosreport*.tar* -C /var/tmp/sosreport_test --strip-components=1
        if [ -s /var/tmp/sosreport_test/sos_logs/*errors.txt ]; then
            FAIL=true
            echo "!!! FAILED !!!"
            echo "#### *errors.txt output"
            ls -alh /var/tmp/sosreport_test/sos_logs/
            cat /var/tmp/sosreport_test/sos_logs/*errors.txt
        fi
        echo "### stop extraction"
    fi
    
    size="$(grep Size /dev/shm/stdout)"
    summary="${summary} \n failures ${FAIL} \t time ${runtime} \t ${size} \t ${1} "

    echo "######### DONE WITH $1 #########"

    if $FAIL; then
      NUMOFFAILURES=$(($NUMOFFAILURES + 1))
      return 1
    else
      return 0
    fi
}

# If /etc/sos/sos.conf doesn't exist let's just make it..
if [ -f /etc/sos/sos.conf ]; then
   echo "/etc/sos/sos.conf already exists"
else
   echo "Creating /etc/sos.conf"
   mkdir /etc/sos
   touch /etc/sos/sos.conf
fi

# Runs not generating sosreports
run_expecting_sucess " -l"
run_expecting_sucess " --list-presets"
run_expecting_sucess " --list-profiles"

# Test generating sosreports, 3 (new) options at a time
# Trying to do --batch   (1 label/archive/report/verbosity change)   (other changes)
run_expecting_sucess " --batch   --build   --no-env-vars "  # Only --build test
run_expecting_sucess " --batch   --no-report   -o hardware " extract
run_expecting_sucess " --batch   --label TEST   -a  -c never" extract
run_expecting_sucess " --batch   --debug  --log-size 0  -c always" extract
run_expecting_sucess " --batch   -z xz   --log-size 1" extract
run_expecting_sucess " --batch   -z gzip" extract
run_expecting_sucess " --batch   -t 1 -n hardware" extract
run_expecting_sucess " --batch   --quiet    -e opencl -k kernel.with-timer" extract
run_expecting_sucess " --batch   --case-id 10101   --all-logs --since=$(date -d "yesterday 13:00" '+%Y%m%d') " extract
run_expecting_sucess " --batch   --verbose   --no-postproc" extract
run_expecting_sucess " --batch   --mask" extract

echo $summary

if [ $NUMOFFAILURES -gt 0 ]; then
  echo "FAILED $NUMOFFAILURES"
  exit 1
else
  echo "Everything worked!"
  exit 0
fi

# vim: set et ts=4 sw=4 :
