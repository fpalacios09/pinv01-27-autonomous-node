#!/usr/bin/env bash
set -euo pipefail
version="${KUBO_VERSION:-0.42.0}"
[[ "$(uname -m)" == "aarch64" || "$(uname -m)" == "arm64" ]] || { echo "ERROR: se requiere ARM64" >&2; exit 1; }
workdir="$(mktemp -d)"; trap 'rm -rf "$workdir"' EXIT
cd "$workdir"
archive="kubo_v${version}_linux-arm64.tar.gz"
wget "https://dist.ipfs.tech/kubo/v${version}/${archive}"
tar -xzf "$archive"
cd kubo
sudo bash install.sh
ipfs version
