#!/usr/bin/env bash
# Build the pinned CPython 3.15 for the study (Ubuntu or Debian host).
#
#   scripts/build_cpython.sh            -> JIT build, yes-off, PGO + LTO
#   VARIANT=pystats scripts/build_cpython.sh -> diagnostic build with --enable-pystats
#
# Installs with `make altinstall`, so only python3.15 lands in PREFIX/bin.
set -euo pipefail

VARIANT="${VARIANT:-jit}"
TAG="v3.15.2"
LLVM_VERSION=21
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${SRC_DIR:-$HOME/src/cpython-$VARIANT}"

case "$VARIANT" in
  jit)
    PREFIX="${PREFIX:-/opt/cpython-3.15-jit}"
    CONFIGURE_FLAGS=(--enable-experimental-jit=yes-off --enable-optimizations --with-lto)
    ;;
  pystats)
    PREFIX="${PREFIX:-/opt/cpython-3.15-pystats}"
    CONFIGURE_FLAGS=(--enable-experimental-jit=yes-off --enable-pystats)
    ;;
  *)
    echo "unknown VARIANT: $VARIANT" >&2
    exit 2
    ;;
esac

# LLVM 21 builds the JIT stencils; clang-21, llvm-readobj-21, llvm-objdump-21
# and llvm-dwarfdump-21 must be discoverable (Tools/jit/README.md).
if ! command -v "clang-$LLVM_VERSION" >/dev/null 2>&1; then
  wget -qO /tmp/llvm.sh https://apt.llvm.org/llvm.sh
  chmod +x /tmp/llvm.sh
  sudo /tmp/llvm.sh "$LLVM_VERSION"
fi

sudo apt-get update
sudo apt-get install -y build-essential git pkg-config libssl-dev zlib1g-dev \
  libbz2-dev libreadline-dev libsqlite3-dev libffi-dev liblzma-dev uuid-dev

if [ ! -d "$SRC/.git" ]; then
  git clone --branch "$TAG" --depth 1 https://github.com/python/cpython.git "$SRC"
fi
cd "$SRC"
git fetch --depth 1 origin "refs/tags/$TAG:refs/tags/$TAG"
git checkout --detach "$TAG"
COMMIT="$(git rev-parse HEAD)"

./configure --prefix="$PREFIX" "${CONFIGURE_FLAGS[@]}"
make -j"$(nproc)"
sudo make altinstall

PY="$PREFIX/bin/python3.15"
META_DIR="$REPO_ROOT/results/meta"
mkdir -p "$META_DIR"
"$PY" - "$VARIANT" "$TAG" "$COMMIT" "$LLVM_VERSION" > "$META_DIR/cpython-$VARIANT-$(uname -m).json" <<'EOF'
import json, platform, subprocess, sys, sysconfig
variant, tag, commit, llvm = sys.argv[1:5]
def out(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines()[0]
    except Exception as exc:
        return f"unavailable: {exc}"
jit = getattr(sys, "_jit", None)
print(json.dumps({
    "variant": variant,
    "tag": tag,
    "commit": commit,
    "version": sys.version,
    "config_args": sysconfig.get_config_var("CONFIG_ARGS"),
    "cflags": sysconfig.get_config_var("CFLAGS"),
    "jit_available": bool(jit and jit.is_available()),
    "cc": out(["cc", "--version"]),
    "clang": out([f"clang-{llvm}", "--version"]),
    "machine": platform.machine(),
    "kernel": platform.release(),
}, indent=2))
EOF

echo "Built $VARIANT at $COMMIT -> $PY"
echo "Record the commit in pins.toml: [cpython] commit = \"$COMMIT\""
