#!/bin/sh
############################################################
# Convert plans to pushplans
#
# Run:
#     sh pushplans/rename_push_to_pushplan.sh
# from the production pushmanager root such that the
# production config.yaml is present and readable
############################################################
SCRIPT=$(readlink -f $0)
SCRIPT_DIR=$(dirname $SCRIPT)

[ ! -r config.yaml ] && echo "No readable config.yaml present in the current directory" && exit 1

PYTHONPATH=. python -u "${SCRIPT_DIR}/../tools/rename_tag.py" plans pushplans
PYTHONPATH=. python -u "${SCRIPT_DIR}/../tools/rename_checklist_type.py" plans pushplans

# Revert steps if needed
#PYTHONPATH=. python -u "${SCRIPT_DIR}/../tools/rename_tag.py" pushplans plans
#PYTHONPATH=. python -u "${SCRIPT_DIR}/../tools/rename_checklist_type.py" pushplans plans
