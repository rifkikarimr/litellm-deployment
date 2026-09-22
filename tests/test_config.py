from pathlib import Path
import unittest

import yaml
import litellm


ROOT = Path(__file__).resolve().parents[1]


class ConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
        cls.models = {
            item["model_name"]: item for item in cls.config["model_list"]
        }

    def test_client_aliases_are_provider_agnostic(self) -> None:
        self.assertEqual(
            set(self.models), {"general-chat", "openai-direct", "gemini-direct"}
        )

    def test_provider_credentials_are_environment_references(self) -> None:
        self.assertEqual(
            self.models["general-chat"]["litellm_params"]["api_key"],
            "os.environ/OPENAI_API_KEY",
        )
        self.assertEqual(
            self.models["gemini-direct"]["litellm_params"]["api_key"],
            "os.environ/GEMINI_API_KEY",
        )

    def test_database_and_master_key_are_environment_references(self) -> None:
        settings = self.config["general_settings"]
        self.assertEqual(settings["database_url"], "os.environ/DATABASE_URL")
        self.assertEqual(settings["master_key"], "os.environ/LITELLM_MASTER_KEY")

    def test_non_transient_errors_fail_fast(self) -> None:
        policy = self.config["router_settings"]["retry_policy"]
        self.assertEqual(policy["AuthenticationErrorRetries"], 0)
        self.assertEqual(policy["BadRequestErrorRetries"], 0)
        self.assertEqual(policy["ContentPolicyViolationErrorRetries"], 0)

    def test_only_gemini_drops_deprecated_sampling_fields(self) -> None:
        self.assertNotIn(
            "additional_drop_params",
            self.models["general-chat"]["litellm_params"],
        )
        self.assertEqual(
            self.models["gemini-direct"]["litellm_params"]["additional_drop_params"],
            ["temperature", "top_p", "top_k"],
        )

    def test_example_models_exist_in_pinned_litellm_registry(self) -> None:
        for model in ("openai/gpt-5.6-luna", "gemini/gemini-3.7-flash"):
            info = litellm.get_model_info(model)
            self.assertGreater(info["max_input_tokens"], 0)


if __name__ == "__main__":
    unittest.main()
