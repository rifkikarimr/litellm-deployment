import unittest

from scripts.sync_db_password import validate_settings


class DatabasePasswordSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = {
            "POSTGRES_USER": "litellm",
            "POSTGRES_DB": "litellm",
            "POSTGRES_PASSWORD": "local-test-secret",
            "DATABASE_URL": (
                "postgresql://litellm:local-test-secret@postgres:5432/litellm"
            ),
        }

    def test_accepts_consistent_compose_database_settings(self) -> None:
        validate_settings(self.settings)

    def test_rejects_password_mismatch(self) -> None:
        self.settings["DATABASE_URL"] = (
            "postgresql://litellm:different-value@postgres:5432/litellm"
        )
        with self.assertRaisesRegex(ValueError, "password does not match"):
            validate_settings(self.settings)

    def test_rejects_example_placeholder(self) -> None:
        self.settings["POSTGRES_PASSWORD"] = "replace-me"
        self.settings["DATABASE_URL"] = (
            "postgresql://litellm:replace-me@postgres:5432/litellm"
        )
        with self.assertRaisesRegex(ValueError, "example placeholder"):
            validate_settings(self.settings)

    def test_rejects_non_compose_database_host(self) -> None:
        self.settings["DATABASE_URL"] = (
            "postgresql://litellm:local-test-secret@localhost:5432/litellm"
        )
        with self.assertRaisesRegex(ValueError, "Compose service name"):
            validate_settings(self.settings)


if __name__ == "__main__":
    unittest.main()
