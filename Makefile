mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))

create:
	python3 -m virtualenv venv

install:
	venv/bin/python3 -m pip install -r requirements.txt

runsim:
	venv/bin/python3 simulations/src/run_par.py
