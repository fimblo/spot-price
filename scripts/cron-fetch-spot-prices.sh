#!/bin/bash

MY_DIR=$(dirname $0)
cd ${MY_DIR}/..

source .venv/bin/activate
python scripts/fetch_spot_prices.py

