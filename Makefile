# File:    Makefile
# Version: GNU Make 3.81
# Author:  Nicholas Russo (njrusmc@gmail.com)
# Purpose: Phony targets used for linting (YAML/Python) and running
#          the script for some quick testing. The 'test' target runs
#          the lint, unit testing, and playbook testing in series.
#          Individual targets can be run as well, typically for CI.
#          See .travis.yml for the individual target invocations.

.DEFAULT_GOAL := test
.PHONY: test
test:	lint bfq

.PHONY: cont
cont:
	@echo "Starting  batfish container"
	ansible-playbook tests/unittest_playbook.yml
	sudo docker container prune --force
	sudo docker container run --name batfish \
		--volume batfish-data:/data \
		--publish 8888:8888 --publish 9997:9997 --publish 9996:9996 \
		--detach batfish/allinone:2023.12.16.1270
	@echo "Completed batfish container"

.PHONY: lint
lint:
	@echo "Starting  lint"
	# find . -name "*.py" | xargs pylint
	# find . -name "*.py" | xargs black -l 80 --check
	pylint bf_pytest.py
	black --line-length 80 --check bf_pytest.py
	@echo "Completed lint"

.PHONY: bfq
bfq:
	@echo "Starting  batfish questions"
	pytest --verbose bf_pytest.py
	@echo "Completed batfish questions"

.PHONY: clean
clean:
	@echo "Starting  clean"
	find . -name "*.pyc" | xargs -r rm
	@echo "Completed clean"
