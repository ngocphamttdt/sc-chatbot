import re
import unittest
from pathlib import Path
from unittest.mock import patch

from app.admin import configs
from app.core.agent import SUPPORTED_PLACEHOLDERS, _render_custom_prompt
from app.tenancy import TenantContext


TENANT = TenantContext(
    tenant_id="spa-1",
    name="Sen Spa",
    industry="spa",
    root=Path("."),
)
SEED_DIR = Path(__file__).resolve().parents[1] / "seed"


class PromptConfigTests(unittest.TestCase):
    @patch.object(configs, "get_db")
    def test_seed_prompt_is_inserted_active_without_overwriting(self, get_db):
        configs.seed_prompt_if_missing(
            TENANT,
            "Prompt mặc định",
            "  Nội dung prompt  ",
        )

        query, update = get_db.return_value.system_prompts.update_one.call_args.args
        prompt = update["$setOnInsert"]
        self.assertEqual(query, {"tenant_id": TENANT.tenant_id})
        self.assertEqual(prompt["tenant_id"], TENANT.tenant_id)
        self.assertEqual(prompt["name"], "Prompt mặc định")
        self.assertEqual(prompt["content"], "Nội dung prompt")
        self.assertTrue(prompt["is_active"])
        get_db.return_value.system_prompts.update_one.assert_called_once_with(
            query,
            update,
            upsert=True,
        )

    def test_custom_prompt_renders_only_supported_placeholders(self):
        result = _render_custom_prompt(
            "Trợ lý của {tenant_name}, ngành {industry}; giữ {other}.",
            TENANT,
        )

        self.assertEqual(
            result,
            "Trợ lý của Sen Spa, ngành spa; giữ {other}.",
        )

    def test_seed_prompts_use_only_supported_placeholders(self):
        for prompt_file in (
            SEED_DIR / "beauty" / "system_prompt.md",
            SEED_DIR / "travel" / "system_prompt.md",
        ):
            with self.subTest(prompt_file=prompt_file):
                content = prompt_file.read_text(encoding="utf-8")
                placeholders = set(re.findall(r"\{([^{}]+)\}", content))
                self.assertTrue(content.strip())
                self.assertLessEqual(placeholders, SUPPORTED_PLACEHOLDERS)


if __name__ == "__main__":
    unittest.main()
