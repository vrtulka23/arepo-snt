#!/usr/bin/env bash
# Build the Python environment, test DIPL, generate, or compile a bundled setup.
set -euo pipefail

DIP_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
AREPO_DIR=$(cd -- "$DIP_DIR/.." && pwd)
BASE_PYTHON=${PYTHON:-python3}
PYTHON_BIN=$BASE_PYTHON
VENV_DIR="$DIP_DIR/.venv"
SNT_BUILD_DIR="$DIP_DIR/.snt3-build"
OUTPUT_ROOT=${DIP_OUTPUT_ROOT:-$DIP_DIR/generated}
case $OUTPUT_ROOT in
  /*) ;;
  *) OUTPUT_ROOT="$PWD/$OUTPUT_ROOT" ;;
esac

usage() {
  cat <<'EOF'
Usage: dip/setup.sh -b
       dip/setup.sh -t
       dip/setup.sh -g SETUP
       dip/setup.sh -c SETUP
       dip/setup.sh -g SETUP -c

  -b          Create dip/.venv and build this checkout's SciNumTools3 bindings.
  -t          Run the DIP test suite.
  -g SETUP    Generate Config.sh, param.txt, and supporting files.
  -c [SETUP]  Generate, then compile Arepo for SETUP (or the -g setup).
  -h          Show this help.

Flags can be combined, for example -b -t -g SETUP. An existing dip/.venv is
used automatically. Outputs go to dip/generated/SETUP/. Set SYSTYPE or
configure Makefile.systype before compiling. Set PYTHON to choose Python 3.
EOF
}

fail() {
  printf 'setup.sh: %s\n' "$*" >&2
  exit 2
}

set_setup() {
  local requested=$1
  [[ "$requested" =~ ^[a-zA-Z0-9_]+$ ]] || fail "Invalid setup name: $requested"
  [[ -z "$setup" || "$setup" == "$requested" ]] || fail "Conflicting setups: $setup and $requested"
  setup=$requested
}

setup=""
run_tests=false
build_venv=false
generate=false
compile=false

while (($#)); do
  case $1 in
    -b)
      build_venv=true
      shift
      ;;
    -t)
      run_tests=true
      shift
      ;;
    -g)
      (($# >= 2)) || fail "-g requires a setup name"
      set_setup "$2"
      generate=true
      shift 2
      ;;
    -c)
      compile=true
      generate=true
      shift
      if (($#)) && [[ $1 != -* ]]; then
        set_setup "$1"
        shift
      fi
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1 (use -h for help)"
      ;;
  esac
done

if ! $build_venv && ! $run_tests && ! $generate; then
  usage >&2
  exit 2
fi
if $generate; then
  [[ -n "$setup" ]] || fail "Specify a setup with -g SETUP or -c SETUP"
  [[ -f "$DIP_DIR/examples/$setup/DIPfile" ]] || fail "Unknown setup: $setup"
fi
if $compile && [[ -z "${SYSTYPE:-}" && ! -f "$AREPO_DIR/Makefile.systype" ]]; then
  fail "Set SYSTYPE or configure $AREPO_DIR/Makefile.systype before compiling"
fi

if $build_venv; then
  [[ -f "$AREPO_DIR/snt3/CMakeLists.txt" ]] || fail "SciNumTools3 source is missing at $AREPO_DIR/snt3"
  command -v cmake >/dev/null || fail "CMake is required to build SciNumTools3"
  "$BASE_PYTHON" -m venv --system-site-packages "$VENV_DIR"
  PYTHON_BIN="$VENV_DIR/bin/python"
  if ! "$PYTHON_BIN" -c 'import numpy' >/dev/null 2>&1; then
    "$PYTHON_BIN" -m pip install numpy
  fi
  cmake -S "$AREPO_DIR/snt3" -B "$SNT_BUILD_DIR" \
    -DPython3_EXECUTABLE="$PYTHON_BIN" \
    -DENABLE_UNIT_TESTS=OFF -DENABLE_BINDING_C=OFF \
    -DENABLE_EXEC_APPS=OFF -DENABLE_EXEC_EXAMPLES=OFF \
    -DENABLE_EXEC_BENCHMARKS=OFF -DENABLE_MAT=OFF
  cmake --build "$SNT_BUILD_DIR" --target _snt --parallel 2
  site_packages=$(
    "$PYTHON_BIN" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])'
  )
  printf '%s\n' "$SNT_BUILD_DIR/python" > "$site_packages/arepo-scinumtools3.pth"
  env -u PYTHONPATH "$PYTHON_BIN" -c 'from scinumtools3.dip import DIP; print("SciNumTools3 ready")'
elif [[ -z "${PYTHON:-}" && -x "$VENV_DIR/bin/python" ]]; then
  PYTHON_BIN="$VENV_DIR/bin/python"
fi

export PYTHONDONTWRITEBYTECODE=1
if [[ "$PYTHON_BIN" == "$VENV_DIR/bin/python" ]]; then
  export PYTHONPATH="$DIP_DIR/src"
else
  export PYTHONPATH="$AREPO_DIR/snt3/build/python:$DIP_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
fi

if $run_tests; then
  "$PYTHON_BIN" -B -m unittest discover -s "$DIP_DIR/tests" -v
fi

if $generate; then
  output="$OUTPUT_ROOT/$setup"
  "$PYTHON_BIN" -B -m arepo_dipl generate --setup "$setup" --output "$output"
fi

if $compile; then
  make_args=(
    "CONFIG=$output/Config.sh"
    "BUILD_DIR=$output/build"
    "EXEC=$output/Arepo"
    "PYTHON=$PYTHON_BIN"
  )
  if [[ -n "${SYSTYPE:-}" ]]; then
    export SYSTYPE
  fi
  (cd "$AREPO_DIR" && make "${make_args[@]}")
  printf 'Compiled %s\n' "$output/Arepo"
fi
