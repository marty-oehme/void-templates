#!/usr/bin/env sh

if [ -r /etc/default/zramd ]; then
    . /etc/default/zramd
fi

zramd start
