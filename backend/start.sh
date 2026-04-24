#!/bin/sh
set -e

python create_all_tables.py
uvicorn app.main:app --host 0.0.0.0 --port 8000