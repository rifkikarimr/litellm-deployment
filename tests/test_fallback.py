import unittest

from litellm import Router


class FallbackTests(unittest.TestCase):
    def test_primary_failure_routes_to_gemini_group_without_network(self) -> None:
        router = Router(
            model_list=[
                {
                    "model_name": "general-chat",
                    "litellm_params": {
                        "model": "openai/gpt-5.6-luna",
                        "api_key": "unit-test-placeholder",
                    },
                },
                {
                    "model_name": "gemini-direct",
                    "litellm_params": {
                        "model": "gemini/gemini-3.7-flash",
                        "api_key": "unit-test-placeholder",
                        "mock_response": "served-by-gemini-fallback",
                    },
                },
            ],
            fallbacks=[{"general-chat": ["gemini-direct"]}],
            num_retries=0,
        )

        response = router.completion(
            model="general-chat",
            messages=[{"role": "user", "content": "test"}],
            mock_testing_fallbacks=True,
        )

        self.assertEqual(
            response.choices[0].message.content, "served-by-gemini-fallback"
        )


if __name__ == "__main__":
    unittest.main()
