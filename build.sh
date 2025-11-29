#!/bin/sh

set -e

flake8 . --count --show-source --statistics

black --check --diff .

./miwear/log.py -s ./test --filename 123

./miwear/targz.py --path test

./miwear/gz.py --path test

./miwear/unzip.py --path test

md5sum -c test/123.md5

./miwear/log.py -s test -f ./test/456（1）.tar.gz
