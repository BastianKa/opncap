# SPDX-License-Identifier: Apache-2.0
# Run from the software/ directory.
.PHONY: gen check test test-py test-c
gen:
	python3 protocol/gen.py
check:
	python3 protocol/gen.py --check
test: check test-py test-c
test-py:
	cd host && python3 -m unittest discover -s tests -v
test-c:
	mkdir -p build
	cc -std=c11 -Wall -Wextra -Werror -Ifirmware/qmk_userspace/keyboards/opncap/opncap_v0_3 protocol/tests/test_protocol.c -o build/test_protocol
	build/test_protocol protocol/tests/vectors.txt
