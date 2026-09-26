# DIPL / Arepo showcase

This directory is a standalone, semantic configuration layer for Arepo.  It
does not modify the Arepo source tree or the `snt3` link.

Each setup declares three physical code bases. Cosmological examples reuse
`profiles/cosmological_units.dip`; the idealised examples reuse
`profiles/standard_units.dip`; and the original MHD setup retains its distinct
`examples/mhd_shock_tube/units.dip`. `profiles/schemas/arepo_units.dip`
derives DIPL custom units named `arepo_length`, `arepo_mass`, and
`arepo_velocity` by directly referencing those code bases with `$unit`, then
declares derived units such as `arepo_time` and `arepo_density`. All code-space
settings in the profile use those units.

The files are loaded in this order:

1. `profiles/schemas/export.dip`, then the selected shared or example-local unit profile
2. `profiles/schemas/`, the reusable `ideal_hydrodynamics.dip` and/or
   `standard_softenings.dip` layers where appropriate, and the selected
   `examples/<setup>/profile.dip`
3. optional DIPL tables owned by that example
4. `profiles/overrides.dip`
5. `profiles/native_controls.dip`, which derives native switches from the
   final overridden values

`profiles/overrides.dip` is the user-editable overlay. Add ordinary DIPL
modifications there; do not edit derived unit
definitions or generated files.

In particular, every profile instantiates the shared `arepo_build` schema in
`profiles/schemas/build.dip`. The other shared contracts are split by concern:
`experiment.dip`, `input.dip`, `output.dip`, `resources.dip`,
`simulation.dip`, `cosmology.dip`, `snapshots.dip`, `analysis.dip`, `gravity.dip`,
`hydrodynamics.dip`, and `mesh.dip`. The
input/output, resource, and simulation schemas retain Arepo parameter-file
documentation and options; profiles supply only values that vary.
`arepo_build` is the compile-capability contract: profiles assign
only the flags and values that differ from safe defaults. Each DIPL value's
`?native` metadata owns its translation to the corresponding Arepo name;
`!tags` selects the output target; optional typed `export` children declare
conversion and applicability settings.
Compile-only features are direct boolean nodes (for example,
`build.physics.cooling`), not `enabled` subnodes. DIPL value nodes may have
children, so features with associated settings nest them under the boolean
flag, such as `build.gravity.particle_mesh.grid_resolution`.

## Generate

Install/build SciNumTools3's Python bindings with `Environment.select()` and
`ValueNode.tags`/`metadata` support, then run from `dip/`:

```bash
PYTHONPATH=src python3 -m arepo_dipl generate --output generated
```

The command writes `Config.sh`, `param.txt`, `output_list.txt`, and a complete
`environment.diph5` snapshot below the requested output directory. It uses
Arepo-safe comments in the two native files. DIPH5 2.3 records evaluated
values, units, node settings, source and trace provenance, custom-unit
registrations, value-bearing groups, and collection-item data. The snapshot
can be loaded in a fresh process without preloading the DIPL source files.

All sixteen Arepo examples with a bundled `Config.sh` and `param.txt` have a
named setup. For example, select the parallel 1D MHD shock-tube setup with:

```bash
PYTHONPATH=src python3 -m arepo_dipl generate --setup mhd_shock_tube --output generated/mhd
```

The gravity-only cosmological volume, including its generated output-list
table, is available as a third setup:

```bash
PYTHONPATH=src python3 -m arepo_dipl generate --setup cosmological_gravity_only --output generated/gravity-only
```

For the local reference build, run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=snt3/build/python:dip/src python3 -B -m arepo_dipl generate --output dip/generated
```

## Export declarations

`rendering.py` discovers nodes with `env.select(tags_all=["arepo:config"])`
or `arepo:param`, using their full paths and `?native` metadata. There is no
per-parameter Python catalog. For example, a schema can declare:

```dipl
cooling bool = false
  !tags ["arepo:config"]
  ?native "COOLING"
```

| Tag | Meaning |
| --- | --- |
| `arepo:config` | Export to `Config.sh`. True booleans emit bare flags; false booleans are omitted; scalars emit `NAME=value`. |
| `arepo:param` | Export to `param.txt` as `Name value`; booleans become `0` or `1`. |

Tags only classify values. Settings that need conversion or conditional
export use the ordinary DIPL schema `arepo_export`, defined in
`profiles/schemas/export.dip`:

```dipl
length float = 1 kpc
  !tags ["arepo:param"]
  ?native "UnitLength_in_cm"
  export : arepo_export
    units = "cm"
```

| Export field | Type and default | Meaning |
| --- | --- | --- |
| `enabled` | bool, `true` | Include the setting when its other conditions pass. |
| `units` | str, `"native"` | Preserve the declared numeric value by default; otherwise convert to this unit expression through SciNumTools. |
| `omit_nonpositive` | bool, `false` | Omit numeric values that are zero or negative. |
| `requires_enabled` | str array, `[]` | Full paths of boolean features that must all be true. |

For example, `requires_enabled = ["build.physics.cooling"]` makes a parameter
conditional on cooling. Dependencies are looked up at export time, so final
user overrides are respected. Missing or non-boolean dependencies are errors.
These are typed DIPL fields, not expressions embedded in tags. Ordinary
parameters need no `export` child at all.

All export conventions belong to `dip/`; SciNumTools supplies schemas,
selection, units and persistence. There are no setup-name predicates in the
renderer. Example-local parameters are exported where they are declared;
the three examples needing `CellShapingFactor` explicitly set its
`export.enabled` to true. Their native outputs are unchanged.
`?requires` remains descriptive metadata, not an implicit export condition.
Value overrides preserve schema tags; an explicit `!tags` assignment replaces
the tag list, so include all intended export tags when changing it.

Outputs are sorted by full DIPL path for stable results before and after
DIPH5 persistence. Unknown or incorrectly typed export fields, legacy policy
tags, missing native names, and duplicate active native names raise errors.
`profiles/native_controls.dip` supplies derived runtime switches after the
user overlay because DIPL references capture values at definition time.

Python still selects source files and renders indexed softening families and
output-schedule tables. `inventory.py` scans the untouched AREPO
`Template-Config.sh` and `src/io/parameters.c` for coverage auditing.

## Verify

From the repository root with the reference bindings built:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=snt3/build/python:dip/src python3 -B -m unittest discover -s dip/tests -v
```

Tests compare all sixteen setups against fingerprints of the previous
generator's native names and values, ignoring comments, whitespace and order.
They also check schema and policy overrides, feature dependencies, unit conversion, derived
switches, error reporting, and rendering from DIPH5 snapshots. Each setup runs
in a separate process because its custom unit definitions share names with
other setups.
