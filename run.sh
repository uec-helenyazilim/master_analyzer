# !/bin/bash

# base setup script
source ./setup.sh
clear

# set title
echo -ne "\033]0;Master Analyzer Server\007"

# start fastapi server
fastapi run main.py --host 127.0.0.1 --port 5000

