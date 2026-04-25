#!/bin/sh

echo "INFO: Building arma-reforger-test image..."

docker build -t arma-reforger-test .

echo "INFO: arma-reforger-test is built. Please update your docker compose. "
