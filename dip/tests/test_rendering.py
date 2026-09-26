"""Behavioral coverage for tag-driven exports and the catalog migration."""

import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from scinumtools3.dip import DIP, Environment
from arepo_dipl.rendering import GenerationError, render_native


ROOT = Path(__file__).parents[1]


def parse(source):
    parser = DIP()
    parser.add_file(ROOT / "profiles" / "schemas" / "export.dip")
    parser.add_string(source)
    return parser.parse()


def entries(env, target):
    return [line for line in render_native(env, target) if not line.startswith(("#", "%"))]


class RenderingTests(unittest.TestCase):
    def test_discovery_schema_override_and_persistence(self):
        env = parse('''$schema controls
  enabled bool = false
    !tags ["arepo:config"]
    ?native ["FEATURE", "SECOND_FEATURE"]
  speed float = 1 m/s
    !tags ["arepo:param"]
    ?native "Speed"
    export : arepo_export
      units = "cm/s"
  disabled bool = false
    !tags ["arepo:config"]
    ?native "DISABLED"
  runtime_switch bool = false
    !tags ["arepo:param"]
    ?native "RuntimeSwitch"
settings : controls
  enabled = true
  speed = 3
unexported int = 99
  ?native "NotExported"
''')
        # A previously unknown schema needs no Python registration.
        self.assertEqual(entries(env, "config"), ["FEATURE", "SECOND_FEATURE"])
        self.assertEqual([line.split() for line in entries(env, "param")],
                         [["RuntimeSwitch", "0"], ["Speed", "300"]])
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "environment.diph5"
            env.save(path)
            loaded = Environment()
            loaded.load(path)
            for target in ("config", "param"):
                self.assertEqual(render_native(env, target), render_native(loaded, target))

    def test_feature_dependencies_and_positive_values(self):
        env = parse('''feature bool = false
second_feature bool = true
zero int = 0
  !tags ["arepo:config"]
  ?native "ZERO"
  export : arepo_export
    omit_nonpositive = true
active int = 2
  !tags ["arepo:config"]
  ?native "ACTIVE"
  export : arepo_export
    omit_nonpositive = true
gated int = 3
  !tags ["arepo:param"]
  ?native "Gated"
  export : arepo_export
    requires_enabled = ["feature", "second_feature"]
chosen int = 4
  !tags ["arepo:param"]
  ?native "Chosen"
  export : arepo_export
    requires_enabled = ["second_feature"]
other int = 5
  !tags ["arepo:param"]
  ?native "Other"
  export : arepo_export
    enabled = false
''')
        self.assertEqual(entries(env, "config"), ["ACTIVE=2"])
        self.assertEqual([line.split() for line in entries(env, "param")], [["Chosen", "4"]])

    def test_export_errors_are_actionable(self):
        cases = [
            ('x int = 1\n  !tags ["arepo:param"]\n', "has no `?native`"),
            ('x int = 1\n  !tags ["arepo:param", "arepo:gate:feature"]\n', "Unknown export tag"),
            ('x int = 1\n  !tags ["arepo:param"]\n  export : arepo_export\n'
             '    requires_enabled = ["missing"]\n', "Missing active DIPL node"),
            ('feature int = 1\nx int = 1\n  !tags ["arepo:param"]\n'
             '  export : arepo_export\n    requires_enabled = ["feature"]\n', "must be a boolean feature"),
            ('x int = 1\n  !tags ["arepo:param"]\n  export\n    untis str = "cm"\n', "Unknown export setting"),
            ('x int = 1\n  !tags ["arepo:param"]\n  export\n    enabled str = "yes"\n', "Invalid type"),
            ('x int = 1\n  !tags ["arepo:param"]\n  ?native "Same"\n'
             'y int = 2\n  !tags ["arepo:param"]\n  ?native "Same"\n', "Duplicate native name"),
        ]
        for source, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(GenerationError, re.escape(message)):
                entries(parse(source), "param")

    def test_policy_and_feature_overrides_are_applied_at_export(self):
        env = parse('''feature bool = false
x float = 2 m
  !tags ["arepo:param"]
  ?native "Length"
  export : arepo_export
    requires_enabled = ["feature"]
    enabled = false
feature = true
x.export.enabled = true
x.export.units = "cm"
''')
        self.assertEqual([line.split() for line in entries(env, "param")], [["Length", "200"]])

    def test_derived_controls_follow_overrides(self):
        parser = DIP()
        parser.add_string('''simulation.time.coordinate str = "linear"
simulation.domain.boundary str = "non_periodic"
build.physics.cooling bool = false
build.physics.star_formation bool = false
''')
        parser.add_string('build.physics.cooling = true\nsimulation.time.coordinate = "scale_factor"\n')
        parser.add_file(ROOT / "profiles" / "native_controls.dip")
        self.assertEqual(dict(line.split() for line in entries(parser.parse(), "param")), {
            "ComovingIntegrationOn": "1", "PeriodicBoundariesOn": "0",
            "CoolingOn": "1", "StarformationOn": "0",
        })

    def test_all_setups_preserve_native_outputs(self):
        # Fingerprints captured from the pre-migration generator. Ignore comments,
        # whitespace and line ordering, but retain every native name and value.
        expected = json.loads((ROOT / "tests" / "native_output_hashes.json").read_text())
        script = '''import json, sys, tempfile
from pathlib import Path
from scinumtools3.dip import Environment
from arepo_dipl.generator import generate, _render_config, _render_parameters, _render_schedule
with tempfile.TemporaryDirectory(dir=sys.argv[2]) as directory:
    path = generate(Path(directory), sys.argv[1])
    outputs = {name: (path / name).read_text() for name in ("Config.sh", "param.txt", "output_list.txt")}
    env = Environment()
    env.load(path / "environment.diph5")
    assert _render_config(env) == outputs["Config.sh"]
    assert _render_parameters(env) == outputs["param.txt"]
    assert _render_schedule(env) == outputs["output_list.txt"]
    print(json.dumps(outputs))
'''
        # Different setups redefine the same custom units, so isolate their
        # process-global PUEL registrations, as separate CLI invocations do.
        for setup, hashes in expected.items():
            with self.subTest(setup=setup):
                outputs = json.loads(subprocess.check_output(
                    [sys.executable, "-B", "-c", script, setup, str(ROOT)], text=True))
                for name, text in outputs.items():
                    canonical = "\n".join(sorted(
                        " ".join(line.split()) for line in text.splitlines()
                        if line.strip() and not line.startswith(("#", "%"))))
                    self.assertEqual(hashlib.sha256(canonical.encode()).hexdigest(), hashes[name],
                                     f"{setup}/{name} changed:\n{text}")


if __name__ == "__main__":
    unittest.main()
