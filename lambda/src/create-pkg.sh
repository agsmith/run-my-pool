#!/bin/bash
set -euo pipefail

requirements_file="$path_cwd/src/requirements.txt"
target_dir="$path_cwd/src"

if [ ! -f "$requirements_file" ]; then
  echo "Missing Lambda requirements lock: $requirements_file" >&2
  exit 1
fi

echo "Installing hash-verified Lambda dependencies..."
python3 -m pip install \
  --require-hashes \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --target "$target_dir" \
  -r "$requirements_file"
