#!/bin/sh
set -eu

echo "INFO: Building arma-reforger-test image..."

docker build -t arma-reforger-test .

echo "INFO: arma-reforger-test is built. Set REFORGER_IMAGE=arma-reforger-test."
