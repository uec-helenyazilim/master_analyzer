# !/bin/bash

# base setup script
source ./setup.sh
clear

# start flask server (debug mode)
fastapi dev main.py --host 127.0.0.1 --port 5000
