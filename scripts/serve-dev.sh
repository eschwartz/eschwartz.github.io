#!/usr/bin/env bash
DIR=`dirname "${BASH_SOURCE[0]}"`;

# Set ruby version
# see https://jekyllrb.com/docs/installation/macos/
# source $(brew --prefix)/opt/chruby/share/chruby/chruby.sh
# source $(brew --prefix)/opt/chruby/share/chruby/auto.sh
# chruby ruby-3.1.3
#
# Run `bundle install` to install ruby dependencies

cd ${DIR}/../ && bundle exec jekyll serve --watch --drafts;
