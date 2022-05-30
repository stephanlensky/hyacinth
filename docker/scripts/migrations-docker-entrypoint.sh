#!/bin/bash
for filename in migrations/*.py; do
    echo "Applying migration $filename..."
    poetry run python $filename
done