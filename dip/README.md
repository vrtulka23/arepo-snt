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

Each `examples/<setup>/DIPfile` declares the complete ordered input list.
The generator discovers these manifests and loads the selected one with
`DIP.add_project()`; there is no Python registry of source files. Paths in a
manifest are relative to its directory, independent of the working directory.
The files are loaded in this order:

1. `profiles/schemas/export.dip`, then the selected shared or example-local unit profile
2. `profiles/schemas/`, the reusable `ideal_hydrodynamics.dip` and/or
   `standard_softenings.dip` layers where appropriate, and the selected
   `examples/<setup>/profile.dip`
3. example-owned tables, imported by the profile from named manifest sources
4. `examples/<setup>/overrides.dip`
5. `profiles/native_controls.dip`, which derives native switches from the
   final overridden values
6. example-owned `tables.dip`, where present, which imports scientific datasets
   and resolves their output filenames from the final settings

Each setup's `overrides.dip` is its user-editable overlay. Add ordinary DIPL
modifications there; they affect only that setup. Do not edit derived unit
definitions or generated files.
Local overlays isolate experiments; they do not change DIPL's evaluation
order or automatically recompute expressions already evaluated in a profile.

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
`environment.diph5` snapshot below the requested output directory, together
with the setup's imported scientific datasets in their original native file
layouts. It uses
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

The manifests select source files. Python renders indexed softening families and
output-schedule tables. `inventory.py` scans the untouched AREPO
`Template-Config.sh` and `src/io/parameters.c` for coverage auditing.

To load a setup directly with SciNumTools, without the AREPO generator:

```python
from scinumtools3.dip import DIP

dip = DIP()
dip.add_project("dip/examples/mhd_shock_tube/DIPfile")
env = dip.parse()
```

The same manifest works with `snt dip parse --project
dip/examples/mhd_shock_tube/DIPfile --print`. Add a setup by creating another
example directory with its own `DIPfile`; it is automatically available to
the generator's `--setup` option.

External `.dipt` files contain column declarations, the `---` separator, and
data rows. They are registered as `sources[]` in the manifest, with paths
relative to that manifest, and imported in the profile:

```dipl
output_schedule table = {schedule_data}
```

They are not standalone DIPL programs and must not be listed as `code[]`.

All five examples with enabled output lists have schedule tables: the two
cosmological volumes, the cosmological zoom, the galaxy merger, and the
isolated collisionless galaxy. Cosmological tables declare `scale_factor
float`; linear-time tables declare `time float arepo_time`. Both include
`write_flag int`. The three added schedules reproduce the upstream
`create.py` output lists, including their `%g` text precision. An enabled
schedule without the appropriate table column raises an error.

## Scientific datasets

The supplied numeric example tables are also represented as `.dipt` files:

- The shared cooling/UV dataset is in `tables/TREECOOL_ep.dipt`, imported by
  both star-formation setups and emitted at `cooling.uv_background_file` when
  cooling is enabled.
- MHD shock-tube and blast-wave reference solutions, halo-mass reference
  tables, and star-formation histories live in their examples' `tables/`
  directories.
- Both supplied `inputspec_ics.txt` spectrum datasets are included, although
  the supplied N-GenIC configurations select an analytic spectrum. Their
  two-number preamble is preserved separately from the four-column table.

Each manifest registers named sources. The corresponding `tables.dip` imports
them under `datasets`, with `arepo:dataset` attached to the explicit
`output_file` value solely for discovery. The upstream source is recorded once
as `?see` metadata on that value; the manifest alone locates the `.dipt` input.
Each dataset also declares ordered column names, an optional preamble, and a
`data table = {source}` import. For example:

```dipl
datasets.Masses_L50n32_z0
  output_file str = "Masses_L50n32_z0.txt"
    !tags ["arepo:dataset"]
    ?see "examples/cosmo_box_gravity_only_3d/Masses_L50n32_z0.txt"
  columns str[:] = ["mass"]
  data table = {dataset_Masses_L50n32_z0}
```

The explicit `columns` list is currently needed because SciNumTools expands
tables into value nodes without exposing durable table-column order through
its Python API. DIPH5 loading may reorder nodes; inferring columns from that
order would corrupt positional native files. This list can be removed when
the API exposes persistent table-column order. The cooling dataset
uses the existing typed export policy to depend on the cooling feature.

Columns preserve upstream numeric conventions without rescaling or assuming
physical units that have not been established. Spectrum column names remain
neutral because the example files do not document their interpretation.
The blast-wave's original comment is retained verbatim; its fourth column is
named pressure following the upstream checking code. Table values and their
declarations survive in DIPH5, and native files can be rendered from that
snapshot without the original sources. Native numeric output uses 17
significant digits to preserve binary64 values; whitespace can differ from
the source files.

There are 15 distinct additional table files and 16 imports across the
setups, alongside the five schedules. This covers all numeric `.txt`/`.dat`
tables currently supplied under upstream `examples/`, plus the shared
`data/TREECOOL_ep` dependency. Binary initial conditions, simulation-generated
logs, and configurations for external initial-condition generators retain
their existing roles; they are not converted into tables.

## Verify

From the repository root with the reference bindings built:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=snt3/build/python:dip/src python3 -B -m unittest discover -s dip/tests -v
```

Tests compare all sixteen setups against fingerprints of the previous
generator's native names and values, ignoring comments, whitespace and order.
The three formerly missing schedule fingerprints were updated to their
upstream values; their time ordering and write flags are also checked explicitly.
They also check schema and policy overrides, feature dependencies, unit conversion, derived
switches, error reporting, and rendering from DIPH5 snapshots. Each setup runs
in a separate process because its custom unit definitions share names with
other setups.
Dataset tests audit the supplied numeric-table inventory and compare every
generated table numerically against its upstream source, including after
DIPH5 loading.
