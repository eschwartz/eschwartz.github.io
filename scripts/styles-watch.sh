#!/usr/bin/env bash
DIR=`dirname "${BASH_SOURCE[0]}"`;

cd ${DIR}/../assets/themes/eschwartz && \
  compass watch;