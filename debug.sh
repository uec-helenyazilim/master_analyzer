# !/bin/bash

# base setup script
source ./setup.sh
clear

# start flask server (debug mode)
flask --app app.py --debug run

