# Verification and maintainer workflow

## One entry point

[`setup.sh`](../setup.sh) resolves repository paths from its own location, so
it can be invoked from another working directory. From the repository root:

```bash
dip/setup.sh -b
dip/setup.sh -t
dip/setup.sh -g mhd_shock_tube
dip/setup.sh -c mhd_shock_tube
```

`-b` creates `dip/.venv` with access to the current Python's site packages,
builds this checkout's SciNumTools3 extension with CMake in
`dip/.snt3-build`, and links the resulting Python package into the venv.
Both directories are ignored by Git. Later invocations use the venv by
default; `PYTHON` explicitly selects another interpreter. `-b -t` builds and
then tests in one invocation. CMake, a C++17 compiler, HDF5, pybind11, and
NumPy are needed; CMake can fetch pybind11 if it is not installed, and the
script installs NumPy into the venv if it is not available.

`-t` runs the complete DIP test suite. `-g SETUP` generates native files into
`dip/generated/SETUP/`. `-c SETUP` regenerates the same setup and invokes
Arepo's Makefile with that `Config.sh`; build files and the executable go into
the same setup directory. `-g SETUP -c` is also accepted. `-c` requires a
configured `Makefile.systype` or `SYSTYPE` environment variable, as in
[Arepo's build guide](../../documentation/source/running.md). Set
`DIP_OUTPUT_ROOT` to place outputs
elsewhere. Compiling does not run a simulation.

The wrapper expects SciNumTools3 Python bindings with manifest overrides,
custom units, `Environment.select()`, value tags and metadata, and DIPH5
support. Without `-b` or an existing `dip/.venv`, it uses the existing
`snt3/build/python` build in this checkout. The direct test command is:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=snt3/build/python:dip/src \
  python3 -B -m unittest discover -s dip/tests -v
```

## What the tests establish

- [`test_bundled_examples.py`](../tests/test_bundled_examples.py) generates all
  16 setups and compares active `Config.sh` and `param.txt` names and values
  directly with the bundled Arepo examples. It ignores comments, whitespace,
  ordering, and equivalent numeric spelling, but compares path strings
  exactly. It also checks softening-family counts against Arepo's native
  default or explicit `NSOFTTYPES`.
- [`test_rendering.py`](../tests/test_rendering.py) checks override loading,
  persistence, tagged export behavior, validation errors, output schedules,
  and native and table rendering after DIPH5 reload. Each full setup runs in
  a separate process because custom unit names are registered process-wide.
- [`test_override_units.py`](../tests/test_override_units.py) checks overrides
  expressed in hours, metres, and centimetres, including changes to a code
  unit base, and rejects incompatible dimensions.
- [`test_setup_script.py`](../tests/test_setup_script.py) checks generation
  from another working directory and that compilation receives the selected
  config and isolated build paths. It uses a stand-in `make` so the test does
  not require an MPI compiler.
- [`table_inventory.json`](../tests/table_inventory.json) tracks the supplied
  numeric datasets. Tests compare rendered values with the upstream tables.

The checks prove source-file equivalence for the bundled examples and the
behavior listed above. Compiling with `-c` additionally checks the selected
configuration against the local compiler and libraries. Running a physical
simulation and checking its science outputs is a separate step.
