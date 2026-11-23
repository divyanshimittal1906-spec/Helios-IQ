#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r apps/api/requirements.txt

cd apps/web
npm install
