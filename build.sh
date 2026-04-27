#!/bin/sh
#
# Local build and test script - mirrors .github/workflows/lint.yml
# Usage: ./build.sh
#

set -eu

readonly TEST_DATA="tests/data"
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

step() {
	printf "\n${CYAN}=== %s ===${NC}\n" "$1"
}

pass() {
	printf "${GREEN}✓ %s${NC}\n" "$1"
}

fail() {
	printf "${RED}✗ %s${NC}\n" "$1"
	exit 1
}

# ---- Lint ----

step "flake8"
flake8 . --count --show-source --statistics || fail "flake8"
pass "flake8"

step "black"
black --check --diff . || fail "black"
pass "black"

step "mypy"
mypy miwear/ --ignore-missing-imports || fail "mypy"
pass "mypy"

# ---- Unit Tests ----

step "pytest"
python3 -m pytest tests/ -v || fail "pytest"
pass "pytest"

# ---- Integration Tests ----

step "miwear_log"
./miwear/log.py "${TEST_DATA}/123.tar.gz"
./miwear/log.py "${TEST_DATA}/456（1）.tar.gz"
./miwear/log.py "${TEST_DATA}/crash_txt.tar.gz"
pass "miwear_log"

step "miwear_targz"
./miwear/targz.py --path "${TEST_DATA}"
pass "miwear_targz"

step "miwear_gz"
./miwear/gz.py --path "${TEST_DATA}"
pass "miwear_gz"

step "miwear_unzip"
./miwear/unzip.py --path "${TEST_DATA}"

pass "miwear_unzip"
step "md5sum"
md5sum -c "${TEST_DATA}/123.md5"
pass "md5sum"

# ---- Done ----

printf "\n${GREEN}=== All passed ===${NC}\n"
