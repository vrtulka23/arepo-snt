"""Load DIPL, derive custom code units, validate, and render Arepo files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .rendering import GenerationError, format_value, render_native, value_at


ROOT = Path(__file__).resolve().parents[2]
PROFILES = ROOT / "profiles"
EXAMPLES = ROOT / "examples"
SCHEMAS = (
    PROFILES / "schemas" / "arepo_units.dip",
    PROFILES / "schemas" / "experiment.dip",
    PROFILES / "schemas" / "cosmology.dip",
    PROFILES / "schemas" / "snapshots.dip",
    PROFILES / "schemas" / "input.dip",
    PROFILES / "schemas" / "output.dip",
    PROFILES / "schemas" / "resources.dip",
    PROFILES / "schemas" / "simulation.dip",
    PROFILES / "schemas" / "build.dip",
    PROFILES / "schemas" / "analysis.dip",
    PROFILES / "schemas" / "cooling.dip",
    PROFILES / "schemas" / "star_formation.dip",
    PROFILES / "schemas" / "gravity.dip",
    PROFILES / "schemas" / "hydrodynamics.dip",
    PROFILES / "schemas" / "mesh.dip",
)


def _require_dipl() -> Any:
    try:
        from scinumtools3.dip import DIP  # type: ignore
    except ImportError as exc:
        raise GenerationError(
            "SciNumTools3 Python bindings are required. Build/install snt3 before generating artifacts."
        ) from exc
    return DIP


_value = value_at


SETUPS = {
    "cosmological_star_formation": (
        PROFILES / "cosmological_units.dip",
        EXAMPLES / "cosmological_star_formation" / "profile.dip",
        EXAMPLES / "cosmological_star_formation" / "output_schedule.dipt",
    ),
    "mhd_shock_tube": (
        EXAMPLES / "mhd_shock_tube" / "units.dip",
        EXAMPLES / "mhd_shock_tube" / "profile.dip",
    ),
    "cosmological_gravity_only": (
        PROFILES / "cosmological_units.dip",
        EXAMPLES / "cosmological_gravity_only" / "profile.dip",
        EXAMPLES / "cosmological_gravity_only" / "output_schedule.dipt",
    ),
    "alfven_wave_1d": (PROFILES / "standard_units.dip", PROFILES / "ideal_hydrodynamics.dip", EXAMPLES / "alfven_wave_1d" / "profile.dip"),
    "cosmo_zoom_gravity_only_3d": (PROFILES / "cosmological_units.dip", PROFILES / "ideal_hydrodynamics.dip", EXAMPLES / "cosmo_zoom_gravity_only_3d" / "profile.dip"),
    "current_sheet_2d": (PROFILES / "standard_units.dip", PROFILES / "ideal_hydrodynamics.dip", EXAMPLES / "current_sheet_2d" / "profile.dip"),
    "galaxy_merger_star_formation_3d": (PROFILES / "cosmological_units.dip", PROFILES / "ideal_hydrodynamics.dip", EXAMPLES / "galaxy_merger_star_formation_3d" / "profile.dip"),
    "gresho_2d": (PROFILES / "standard_units.dip", PROFILES / "ideal_hydrodynamics.dip", EXAMPLES / "gresho_2d" / "profile.dip"),
    "interacting_blastwaves_1d": (PROFILES / "standard_units.dip", PROFILES / "ideal_hydrodynamics.dip", EXAMPLES / "interacting_blastwaves_1d" / "profile.dip"),
    "isolated_galaxy_collisionless_3d": (PROFILES / "cosmological_units.dip", PROFILES / "ideal_hydrodynamics.dip", EXAMPLES / "isolated_galaxy_collisionless_3d" / "profile.dip"),
    "noh_2d": (PROFILES / "standard_units.dip", PROFILES / "ideal_hydrodynamics.dip", EXAMPLES / "noh_2d" / "profile.dip"),
    "noh_3d": (PROFILES / "standard_units.dip", PROFILES / "ideal_hydrodynamics.dip", EXAMPLES / "noh_3d" / "profile.dip"),
    "polytrope_1d_spherical": (PROFILES / "standard_units.dip", PROFILES / "ideal_hydrodynamics.dip", EXAMPLES / "polytrope_1d_spherical" / "profile.dip"),
    "shocktube_1d": (PROFILES / "standard_units.dip", PROFILES / "ideal_hydrodynamics.dip", EXAMPLES / "shocktube_1d" / "profile.dip"),
    "wave_1d": (PROFILES / "standard_units.dip", PROFILES / "ideal_hydrodynamics.dip", EXAMPLES / "wave_1d" / "profile.dip"),
    "yee_2d": (PROFILES / "standard_units.dip", PROFILES / "ideal_hydrodynamics.dip", EXAMPLES / "yee_2d" / "profile.dip"),
}

SOFTENING_PROFILES = {
    "alfven_wave_1d": PROFILES / "standard_softenings.dip",
    "cosmo_zoom_gravity_only_3d": PROFILES / "standard_softenings.dip",
    "current_sheet_2d": PROFILES / "standard_softenings.dip",
    "galaxy_merger_star_formation_3d": PROFILES / "two_softenings.dip",
    "gresho_2d": PROFILES / "standard_softenings.dip",
    "interacting_blastwaves_1d": PROFILES / "standard_softenings.dip",
    "isolated_galaxy_collisionless_3d": PROFILES / "two_softenings.dip",
    "noh_2d": PROFILES / "standard_softenings.dip",
    "noh_3d": PROFILES / "standard_softenings.dip",
    "polytrope_1d_spherical": PROFILES / "standard_softenings.dip",
    "shocktube_1d": PROFILES / "standard_softenings.dip",
    "wave_1d": PROFILES / "standard_softenings.dip",
    "yee_2d": PROFILES / "standard_softenings.dip",
}


def load_environment(setup: str = "cosmological_star_formation") -> Any:
    """Load one self-contained DIPL setup and its reference-derived units."""
    DIP = _require_dipl()
    try:
        unit_file, *sources = SETUPS[setup]
    except KeyError as exc:
        raise GenerationError(f"Unknown setup `{setup}`. Choose one of: {', '.join(SETUPS)}.") from exc
    if softening_profile := SOFTENING_PROFILES.get(setup):
        sources = (sources[0], softening_profile, *sources[1:])
    dip = DIP()
    for source in (PROFILES / "schemas" / "export.dip", unit_file, *SCHEMAS, *sources, PROFILES / "overrides.dip", PROFILES / "native_controls.dip"):
        dip.add_file(source)
    return dip.parse()


def _collection_values(env: Any, fqp: str, member: str = "length") -> list[Any]:
    """Read a named value below each DIPL collection-item container."""
    values: list[Any] = []
    index = 0
    while True:
        try:
            values.append(_value(env, f"{fqp}[{index}].{member}"))
        except GenerationError:
            return values
        index += 1


def _render_config(env: Any) -> str:
    lines = ["#!/bin/bash", "# Generated by dip/src/arepo_dipl; do not edit.", ""]
    return "\n".join(lines + render_native(env, "config")) + "\n"


def _render_parameters(env: Any) -> str:
    lines = ["% Generated by dip/src/arepo_dipl; do not edit.", "% DIPL environment and provenance are in environment.diph5.", ""]
    lines.extend(render_native(env, "param"))
    # Arepo exposes these as indexed flat tag families, while the semantic
    # model retains their collection meaning and unit validation.
    for native_prefix, fqp in (
        ("SofteningComovingType", "gravity.softenings.comoving"),
        ("SofteningMaxPhysType", "gravity.softenings.physical_maximum"),
    ):
        for index, value in enumerate(_collection_values(env, fqp)):
            lines.extend((
                f"% DIPL {fqp}[{index}]: gravitational softening in arepo_length.",
                f"{native_prefix}{index:<22}{format_value(value)}",
            ))
    for index, value in enumerate(_value(env, "gravity.softenings.particle_type_map")):
        lines.extend((
            f"% DIPL gravity.softenings.particle_type_map[{index}].",
            f"SofteningTypeOfPartType{index:<19}{format_value(value)}",
        ))
    return "\n".join(lines) + "\n"


def _render_schedule(env: Any) -> str:
    if not _value(env, "output.schedule.enabled"):
        return ""
    try:
        times = _value(env, "output_schedule.scale_factor")
        flags = _value(env, "output_schedule.write_flag")
    except GenerationError:
        # Some upstream examples name an output-list file but do not ship it.
        # Preserve that reference in param.txt without inventing a table.
        return ""
    return "\n".join(f"{a:.12g} {int(b)}" for a, b in zip(times, flags)) + "\n"


def generate(output: Path, setup: str = "cosmological_star_formation") -> Path:
    env = load_environment(setup)
    output.mkdir(parents=True, exist_ok=True)
    (output / "Config.sh").write_text(_render_config(env))
    (output / "param.txt").write_text(_render_parameters(env))
    (output / "output_list.txt").write_text(_render_schedule(env))
    env.save(output / "environment.diph5")
    return output
