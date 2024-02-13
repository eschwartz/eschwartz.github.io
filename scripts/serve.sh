#!/usr/bin/env bash
DIR=`dirname "${BASH_SOURCE[0]}"`;

cd ${DIR}/../ && bundle exec jekyll serve --watch;

