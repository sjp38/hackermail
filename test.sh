#!/bin/bash

HKML=./hkml
OUT=./test_out

$HKML ls linux-mm > $OUT || exit 1
$HKML ls linux-mm -i 2 >> $OUT || exit 2
$HKML format_reply linux-mm -i 2 >> $OUT || exit 3
$HKML fetch linux-mm workflows >> $OUT || exit 4
$HKML fetch >> $OUT || exit 5

mv .hkm .hkml

$HKML --hkml_dir .hkml ls linux-mm >> $OUT || exit 1
$HKML --hkml_dir .hkml ls linux-mm -i 2 >> $OUT || exit 2
$HKML --hkml_dir .hkml format_reply linux-mm -i 2 >> $OUT || exit 3
$HKML --hkml_dir .hkml fetch linux-mm workflows >> $OUT || exit 4
$HKML --hkml_dir .hkml fetch >> $OUT || exit 5

mv .hkml .hkm

cat $OUT
echo "SUCCESS"
