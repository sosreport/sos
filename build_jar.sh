#!/bin/bash

BUILD_DIR=buildjar
ARCHIVE_NAME=sosreport.jar
DEST_JAR=$BUILD_DIR/$ARCHIVE_NAME
PO_DIR=$BUILD_DIR/sos/po

echo "Making build directories ..."
mkdir -p $PO_DIR

for po in `ls po/*.po`;
do
    dest=`basename $po | awk -F. '{print $1}'`
    dest=${PO_DIR}/${dest}.properties

    echo "Converting $po to $dest ..."
    msgcat -p -o $dest $po
done

echo "Duplicating en ..."
cp $PO_DIR/en.properties $PO_DIR/en_US.properties

echo "Removing .class and .pyc files"
find sos -name "*.class" | xargs rm
find sos -name "*.pyc" | xargs rm

echo "Adding in sos ..."
zip -r $DEST_JAR sos

echo "Adding in __run__.py ..."
zip -r $DEST_JAR __run__.py

echo "Adding in i18n ..."
cd $BUILD_DIR
zip -r $ARCHIVE_NAME sos

echo "Cleaning up ..."
cd -
rm -rf $BUILD_DIR/sos
