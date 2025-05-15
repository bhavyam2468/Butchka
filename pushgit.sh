#!/bin/bash

cd "$(dirname "$0")" || exit 1

git add .
git commit -m "Update: $(date)"
git push origin main
