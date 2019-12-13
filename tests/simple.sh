#/bin/bash
# A quick port of the travis tests to bash, requires root
# TODO
# * look into using a framework..
# * why --dry-run fails?
# * why --experimental fails?
# * https://github.com/sosreport/sos/issues/1921
# * make it better validate archives and contents

PYTHON=${1:-/usr/bin/python3}
SOSPATH=${2:-./sosreport}

NUMOFFAILURES=0

run_expecting_sucess () {
    #$1 - is command options
    #$2 - kind of check to do, so far only extract
    FAIL=false
    # Make sure clean
    rm -f stderr stdout /tmp/sosreport*.tar.*
    rm -rf /tmp/sosreport_test/

    echo "######### RUNNING $1 #########"
    $PYTHON $SOSPATH $1 2> stderr 1> stdout

    if [ $? -eq 0 ]; then
      echo "### Success"
    else
      echo "!!! FAILED !!!"
      FAIL=true
    fi

    if [ -s stderr ]; then
       FAIL=true
       echo "!!! FAILED !!!"
       echo "### start stderr"
       cat stderr
       echo "### end stderr"
    fi

    echo "### start stdout"
    cat stdout
    echo "### end stdout"

    if [ "extract" = "$2" ]; then
        echo "### start extraction"
        rm -f /tmp/sosreport*md5
        mkdir /tmp/sosreport_test/
        tar xfa /tmp/sosreport*.tar* -C /tmp/sosreport_test --strip-components=1
        if [ -s /tmp/sosreport_test/sos_logs/*errors.txt ]; then
            FAIL=true
            echo "!!! FAILED !!!"
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

# If /etc/sos.conf doesn't exist let's just make it..
if [ -f /etc/sos.conf ]; then
   echo "/etc/sos.conf already exists"
else
   echo "Creating /etc/sos.conf"
   touch /etc/sos.conf
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

# Workaround Travis bug (requires -n lxd)
if [ $TRAVIS = true ]; then
    run_expecting_sucess " --batch   -z xz   --log-size 1 -n lxd" extract
else
    run_expecting_sucess " --batch   -z xz   --log-size 1" extract
fi

run_expecting_sucess " --batch   -z gzip" extract
run_expecting_sucess " --batch   -z bzip2   -t 1 -n hardware" extract
run_expecting_sucess " --batch   --quiet    -e opencl -k kernel.with-timer" extract
run_expecting_sucess " --batch   --case-id 10101   --all-logs --since=20191007" extract
run_expecting_sucess " --batch   --verbose   --no-postproc" extract

if [ $NUMOFFAILURES -gt 0 ]; then
  echo "FAILED $NUMOFFAILURES"
  exit 1
else
  echo "Everything worked!"
  exit 0
fi

# vim: set et ts=4 sw=4 :
