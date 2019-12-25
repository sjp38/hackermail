#!/bin/bash

HKML=./hkml

$HKML ls linux-mm || exit 1
$HKML ls linux-mm 2 || exit 2
$HKML format_reply linux-mm 2 || exit 3
$HKML fetch linux-mm workflows || exit 4
$HKML fetch || exit 5

mv .hkm .hkml

$HKML --hkml_dir .hkml ls linux-mm || exit 1
$HKML --hkml_dir .hkml ls linux-mm 2 || exit 2
$HKML --hkml_dir .hkml format_reply linux-mm 2 || exit 3
$HKML --hkml_dir .hkml fetch linux-mm workflows || exit 4
$HKML --hkml_dir .hkml fetch || exit 5

mv .hkml .hkm

echo "SUCCESS"
