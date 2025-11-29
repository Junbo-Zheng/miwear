#!/bin/sh

flake8 . --count --show-source --statistics

black --check --diff .
