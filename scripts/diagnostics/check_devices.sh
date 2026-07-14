#!/usr/bin/env bash
set -u
ls -l /dev/mcu /dev/adapter 2>/dev/null || true
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true
id
dfu-util --list 2>/dev/null || true
