#!/bin/bash

HKML=./hkml

$HKML ls linux-mm || exit 1
$HKML ls linux-mm 2 || exit 2
$HKML format_reply linux-mm 2 || exit 3
$HKML fetch linux-mm workflows || exit 4
