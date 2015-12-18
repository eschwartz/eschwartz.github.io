#!/usr/bin/env bash
DIR=`dirname "${BASH_SOURCE[0]}"`;

## kill background tasks on SIGINT
trap 'kill %1; kill %2' SIGINT

${DIR}/styles-watch.sh & ${DIR}/serve-dev.sh