#!/usr/bin/env bash
DIR=`dirname "${BASH_SOURCE[0]}"`;

cd ${DIR}/../ && jekyll serve --watch --drafts;
