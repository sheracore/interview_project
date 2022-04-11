#!/bin/bash
source .venv/bin/activate
python manage.py shell_plus --ipython --settings=proj.settings
