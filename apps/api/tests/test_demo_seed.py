import json
from pathlib import Path

from sic_api.modules.demo.seed import DemoSeedConfig, _display_name


ROOT = Path(__file__).resolve().parents[3]


def test_demo_configuration_is_exact_and_shared_with_web() -> None:
    seed_payload = json.loads((ROOT / "seeds" / "demo-data.json").read_text(encoding="utf-8"))
    web_payload = json.loads((ROOT / "apps" / "web" / "src" / "data" / "demo-data.json").read_text(encoding="utf-8"))
    config = DemoSeedConfig.model_validate(seed_payload)

    assert web_payload == seed_payload
    assert config.providers_per_service == 3
    assert 1392 * config.providers_per_service == 4176


def test_all_demo_provider_names_are_distinct() -> None:
    config = DemoSeedConfig.model_validate_json((ROOT / "seeds" / "demo-data.json").read_text(encoding="utf-8"))
    names = {_display_name(config, ordinal) for ordinal in range(4176)}
    assert len(names) == 4176
