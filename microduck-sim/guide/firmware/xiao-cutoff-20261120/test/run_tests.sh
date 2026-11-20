#!/bin/sh
# Build and run the host test of the cutoff decisions. Writes test/test_output.log.
set -e
cd "$(dirname "$0")"
g++ -std=c++11 -Wall -Wextra -Werror -o test_cutoff_logic test_cutoff_logic.cpp
./test_cutoff_logic | tee test_output.log
