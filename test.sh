#!/bin/bash
source .venv/bin/activate
coverage erase
coverage run manage.py test $1 --settings=proj.test_settings
# coverage report
