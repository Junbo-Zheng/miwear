#!/bin/sh

set -e

flake8 . --count --show-source --statistics

black --check --diff .

./miwear/log.py --filename ./test/123.tar.gz

./miwear/targz.py --path test

./miwear/gz.py --path test

./miwear/unzip.py --path test

md5sum -c test/123.md5

./miwear/log.py ./test/456（1）.tar.gz
