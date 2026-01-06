#!/usr/bin/env bash
echo "current directory: $(pwd)"

# set file directory variable to place the virtual environment
VENV_DIR=".venv"

# create venv if it doesn't exist
if [ ! -d $VENV_DIR ]; then 
    # assuming global python environment is active, we can call venv module to create the virtual environment 
    py -m venv $VENV_DIR
fi

# activate the new virtual environment before installing the libraries
source $VENV_DIR/Scripts/activate

# print the current active venv
echo "current active environment:"
which python

# install libraries
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
