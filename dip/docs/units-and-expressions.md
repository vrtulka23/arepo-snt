# Units and expressions

## Physical bases become Arepo code units

Every setup selects physical length, mass, and velocity bases. Most idealised
examples use [`standard_units.dip`](../profiles/standard_units.dip), where one
code length is `0.01 m` (one centimetre). Cosmological volumes use
[`cosmological_units.dip`](../profiles/cosmological_units.dip); the original
MHD shock tube uses its [own bases](../examples/mhd_shock_tube/units.dip).

[`arepo_units.dip`](../profiles/schemas/arepo_units.dip) derives custom DIPL
units by referring to those selected values:

```dipl
$unit arepo_length = {?code_units.length}
$unit arepo_time = 1*arepo_length/arepo_velocity
$unit arepo_density = 1*arepo_mass/arepo_length3
```

The [simulation schema](../profiles/schemas/simulation.dip) then declares
`simulation.domain.box.size` in `arepo_length`. An override of `2 m` in an
idealised setup emits `BoxSize 200`, since each code length is one centimetre.
If the override also changes `code_units.length` to `2 cm`, `1 m` emits
`BoxSize 50` and `UnitLength_in_cm 2`. These are asserted in
[`test_override_units.py`](../tests/test_override_units.py), along with a
time conversion (`1 h` to `3600 s`) and rejection of a length set in seconds.
The tests reload DIPH5 and check that native rendering stays the same.

`code_units.length`, `mass`, and `velocity` each have an export policy that
converts their physical value to the cgs units expected by Arepo. Other
code-space values usually preserve their numeric value after conversion into
the selected `arepo_*` unit. The conversion is performed by SciNumTools
through the [renderer](../src/arepo_dipl/rendering.py).

## Expressions connect scientific inputs to native values

The [cosmological star-formation profile](../examples/cosmological_star_formation/profile.dip)
declares its initial redshift once and derives the start scale factor:

```dipl
initial_redshift = 127
begin float = ( 1 / ( 1 + {?simulation.time.initial_redshift} ) )
```

This yields `TimeBegin 0.0078125`. Overriding the redshift with `63` yields
`TimeBegin 0.015625`. The same profile derives the dark-energy density as
`1 - cosmology.matter_density` and dark-matter density as total matter minus
baryons. The [cosmology schema](../profiles/schemas/cosmology.dip) retains
their descriptions and validation conditions.

The [native controls](../profiles/native_controls.dip) are expressions too:
`simulation.time.coordinate = "scale_factor"` yields
`ComovingIntegrationOn 1`; `build.physics.cooling = true` yields
`CoolingOn 1`. These translations are DIPL values and therefore remain
visible, with their provenance, in `environment.diph5`.

Expressions are evaluated as the project is parsed. Set independent inputs
before their dependents in a profile; an override cannot introduce a forward
reference. See the [manifest and override guide](model-and-overrides.md) for
source ordering.
