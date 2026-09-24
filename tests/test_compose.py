from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class ComposeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compose = yaml.safe_load(
            (ROOT / "compose.yaml").read_text(encoding="utf-8")
        )
        cls.services = cls.compose["services"]

    def test_gateway_and_database_ship_in_one_stack(self) -> None:
        self.assertEqual(set(self.services), {"litellm", "postgres"})
        self.assertIn("build", self.services["litellm"])
        self.assertEqual(self.services["postgres"]["image"], "postgres:16-alpine")

    def test_postgres_is_not_published_to_the_host(self) -> None:
        self.assertNotIn("ports", self.services["postgres"])

    def test_gateway_defaults_to_loopback_with_configurable_port(self) -> None:
        self.assertEqual(
            self.services["litellm"]["ports"],
            [
                "${LITELLM_BIND_ADDRESS:-127.0.0.1}:"
                "${LITELLM_PORT:-4000}:4000"
            ],
        )

    def test_database_data_uses_a_named_volume(self) -> None:
        self.assertIn("postgres-data", self.compose["volumes"])
        self.assertEqual(
            self.services["postgres"]["volumes"],
            ["postgres-data:/var/lib/postgresql/data"],
        )


if __name__ == "__main__":
    unittest.main()
