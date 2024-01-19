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
	sudo docker container prune --force
	sudo docker container run --name batfish \
		--volume batfish-data:/data \
		--publish 8888:8888 --publish 9997:9997 --publish 9996:9996 \
		--detach batfish/allinone:2023.12.16.1270
	nc -v -n -w 1 127.0.0.1 8888
	nc -v -n -w 1 127.0.0.1 9997
	nc -v -n -w 1 127.0.0.1 9996
	@echo "Completed batfish container"

.PHONY: lint
lint:
	@echo "Starting  lint"
	# find . -name "*.py" | xargs pylint
	# find . -name "*.py" | xargs black -l 80 --check
	# pylint bf_pytest.py
	# black --line-length 80 --check *.py
	black --line-length 80 *.py
	@echo "Completed lint"

.PHONY: bf
bf:
	@echo "Starting  batfish tests"
	pytest --verbose bf_pytest.py --snapshot_name pre
	@echo "Completed batfish tests"

.PHONY: gns3
gns3:
	@echo "Starting  gns3 deployment"
	python deploy_topology.py http://192.168.120.128:80/v2 pre
	@echo "Completed gns3 deployment"

.PHONY: clean
clean:
	@echo "Starting  clean"
	sudo docker container ls --all --quiet | sudo xargs docker stop | sudo xargs docker rm
	find . -name "*.pyc" | xargs -r rm
	@echo "Completed clean"
