#!/bin/sh
############################################################
# Convert plans to pushplans
#
# Run as sh pushplans/rename_push_to_pushplan.sh
# from pushmanager root
############################################################
SCRIPT=$(readlink -f $0)
SCRIPT_DIR=$(dirname $SCRIPT)
echo $SCRIPT_DIR

python -u "${SCRIPT_DIR}/../tools/rename_tag.py" plans pushplans
python -u "${SCRIPT_DIR}/../tools/rename_checklist_type.py" plans pushplans

# Revert steps if needed
#python -u "${SCRIPT_DIR}/../tools/rename_tag.py" pushplans plans
#python -u "${SCRIPT_DIR}/../tools/rename_checklist_type.py" pushplans plans
