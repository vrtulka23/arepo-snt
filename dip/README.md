# DIPL / Arepo showcase

This directory is a standalone, semantic configuration layer for Arepo.  It
does not modify the Arepo source tree or the `snt3` link.

Each setup declares three physical code bases. The two cosmological setups
reuse `profiles/cosmological_units.dip`, while the MHD setup retains its
distinct `examples/mhd_shock_tube/units.dip`. `profiles/schemas/arepo_units.dip`
derives DIPL custom units named `arepo_length`, `arepo_mass`, and
`arepo_velocity` by directly referencing those code bases with `$unit`, then
declares derived units such as `arepo_time` and `arepo_density`. All code-space
settings in the profile use those units.

The files are loaded in this order:

1. the selected shared or example-local unit profile
2. `profiles/schemas/` (reference-derived code units, cosmology, snapshots, build, gravity, hydrodynamics, and mesh) and the selected `examples/<setup>/profile.dip`
3. optional DIPL tables owned by that example
4. `profiles/overrides.dip`

`profiles/` therefore contains only cross-example unit/schema contracts and
the final overlay. The last file is intentionally the only user-editable
layer. Add ordinary DIPL modifications there; do not edit derived unit
definitions or generated files.

In particular, every profile instantiates the shared `arepo_build` schema in
`profiles/schemas/build.dip`. The other shared contracts are split by concern:
`cosmology.dip`, `snapshots.dip`, `gravity.dip`, `hydrodynamics.dip`, and
`mesh.dip`. `arepo_build` is the compile-capability contract: profiles assign
only the flags and values that differ from safe defaults, while `catalog.py`
continues to own the translation to native Arepo names.
Compile-only features are direct boolean nodes (for example,
`build.physics.cooling`), not `enabled` subnodes. DIPL value nodes may have
children, so features with associated settings nest them under the boolean
flag, such as `build.gravity.particle_mesh.grid_resolution`.

## Generate

Install/build SciNumTools3's Python bindings, then run:

```bash
PYTHONPATH=src python3 -m arepo_dipl generate --output generated
```

The command writes `Config.sh`, `param.txt`, `output_list.txt`, and
`provenance.json` below the requested output directory. It uses Arepo-safe
comments in the two native files and stores catalog provenance in JSON.
`Environment.save()` cannot yet replace this with DIPH5 because the current
DIPH5 writer cannot serialize DIPL value nodes that have children.

Select the parallel 1D MHD shock-tube setup with:

```bash
PYTHONPATH=src python3 -m arepo_dipl generate --setup mhd_shock_tube --output generated/mhd
```

The gravity-only cosmological volume, including its generated output-list
table, is available as a third setup:

```bash
PYTHONPATH=src python3 -m arepo_dipl generate --setup cosmological_gravity_only --output generated/gravity-only
```

`catalog.py` is deliberately the one place containing native Arepo names.
Its entries are keyed by semantic DIPL fully-qualified paths.  `inventory.py`
also scans the untouched Arepo `Template-Config.sh` and `src/io/parameters.c`
so catalog coverage can be audited as Arepo evolves.
