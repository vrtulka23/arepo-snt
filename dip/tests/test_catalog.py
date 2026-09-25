from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from arepo_dipl.catalog import CONFIG, PARAMETERS
from arepo_dipl.inventory import runtime_tags, template_flags


ROOT = Path(__file__).parents[2]


class CatalogTests(unittest.TestCase):
    def test_selected_native_names_are_unique_per_target(self):
        for entries in (CONFIG, PARAMETERS):
            for index, entry in enumerate(entries):
                for other in entries[index + 1 :]:
                    if entry.native != other.native:
                        continue
                    # A setup-specific mapping may reuse a native name only
                    # when the two setup branches cannot be active together.
                    self.assertIsNotNone(entry.setup)
                    self.assertIsNotNone(other.setup)
                    self.assertNotEqual(entry.setup, other.setup)

    def test_arepo_inventory_is_readable(self):
        self.assertIn("COOLING", template_flags(ROOT))
        self.assertIn("PMGRID", template_flags(ROOT))
        self.assertIn("InitCondFile", runtime_tags(ROOT))

    def test_selected_profile_has_semantic_core_mappings(self):
        fqps = {entry.fqp for entry in PARAMETERS}
        self.assertIn("code_units.length", fqps)
        self.assertIn("simulation.domain.box.size", fqps)
        self.assertIn("star_formation.supernova_temperature", fqps)

    def test_mhd_setup_is_registered(self):
        from arepo_dipl.generator import SETUPS

        self.assertEqual(SETUPS["mhd_shock_tube"][1].name, "profile.dip")
        self.assertEqual(SETUPS["cosmological_gravity_only"][1].name, "profile.dip")

    def test_every_profile_instantiates_the_shared_runtime_schemas(self):
        schemas = ROOT / "dip" / "profiles" / "schemas"
        build_schema = (schemas / "build.dip").read_text()
        self.assertIn("$schema arepo_build", build_schema)
        self.assertNotIn("enabled bool", build_schema)
        self.assertIn("particle_mesh bool = false\n      ?descr", build_schema)
        self.assertIn("grid_resolution int = 0", build_schema)
        self.assertTrue((schemas / "cosmology.dip").is_file())
        self.assertTrue((schemas / "snapshots.dip").is_file())
        self.assertTrue((schemas / "input.dip").is_file())
        self.assertTrue((schemas / "output.dip").is_file())
        self.assertTrue((schemas / "resources.dip").is_file())
        self.assertTrue((schemas / "simulation.dip").is_file())
        self.assertTrue((schemas / "gravity.dip").is_file())
        self.assertTrue((schemas / "hydrodynamics.dip").is_file())
        self.assertTrue((schemas / "mesh.dip").is_file())
        self.assertIn("force_accuracy : gravity_force_accuracy", (schemas / "gravity.dip").read_text())
        self.assertIn("$schema gravity_softening_length", (schemas / "gravity.dip").read_text())
        self.assertIn("regularization : mesh_regularization", (schemas / "mesh.dip").read_text())
        units = (schemas / "arepo_units.dip").read_text()
        self.assertIn("$unit arepo_length = {?code_units.length}", units)
        self.assertIn("$unit arepo_density = 1*arepo_mass/arepo_length3", units)
        self.assertIn("initial_conditions : initial_conditions_settings", (schemas / "input.dip").read_text())
        self.assertIn("snapshots : snapshot_settings", (schemas / "output.dip").read_text())
        resources = (schemas / "resources.dip").read_text()
        simulation = (schemas / "simulation.dip").read_text()
        self.assertIn("wall_clock : wall_clock_resources", resources)
        self.assertIn("limit float s\n    !condition ({.} > 0 s)", resources)
        self.assertIn("time : simulation_time", simulation)
        self.assertIn("size float arepo_length\n    !condition ({.} > 0 arepo_length)", simulation)
        for profile in (ROOT / "dip" / "examples").glob("*/profile.dip"):
            text = profile.read_text()
            self.assertIn("build : arepo_build", text)
            self.assertIn("input : input_settings", text)
            self.assertIn("output : output_settings", text)
            self.assertIn("resources : resources_settings", text)
            self.assertIn("simulation : simulation_settings", text)
            self.assertIn("gravity : gravity_settings", text)
            self.assertIn("hydrodynamics : hydrodynamics_settings", text)
            self.assertIn("mesh : mesh_settings", text)
            self.assertIn("comoving list : gravity_softening_length", text)
            self.assertIn("comoving[]\n      length =", text)


if __name__ == "__main__":
    unittest.main()
