"""The shipped blueprints must actually import and produce a valid automation."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.yaml import load_yaml
import pytest

BLUEPRINTS = sorted(Path("blueprints/automation/zoneminder").glob("*.yaml"))

#: Values good enough to render each blueprint for validation.
SAMPLE_INPUTS = {
    "motion_notification": {
        "motion_sensor": "binary_sensor.driveway_motion",
        "camera": "camera.driveway",
        "notify_target": "notify.mobile_app_phone",
        "cooldown": 60,
    }
}


def test_blueprints_are_shipped() -> None:
    """A blueprint that is not in the repository cannot help anyone."""
    assert BLUEPRINTS, "no automation blueprints found"


@pytest.mark.parametrize("path", BLUEPRINTS, ids=lambda p: p.stem)
async def test_blueprint_metadata(hass: HomeAssistant, path: Path) -> None:
    """Each blueprint declares the metadata the UI needs."""
    data = await hass.async_add_executor_job(load_yaml, str(path))
    blueprint = Blueprint(
        data,
        expected_domain="automation",
        path=str(path),
        schema=AUTOMATION_BLUEPRINT_SCHEMA,
    )

    assert blueprint.name
    assert blueprint.metadata["description"]
    assert blueprint.metadata["source_url"].startswith("https://")


@pytest.mark.parametrize("path", BLUEPRINTS, ids=lambda p: p.stem)
async def test_blueprint_renders_a_valid_automation(
    hass: HomeAssistant, path: Path
) -> None:
    """Filling the inputs in produces something the automation schema accepts."""
    assert await async_setup_component(hass, "automation", {})

    from homeassistant.components.automation.config import PLATFORM_SCHEMA

    data = await hass.async_add_executor_job(load_yaml, str(path))
    blueprint = Blueprint(
        data,
        expected_domain="automation",
        path=str(path),
        schema=AUTOMATION_BLUEPRINT_SCHEMA,
    )

    inputs = SAMPLE_INPUTS[path.stem]
    assert set(inputs) <= set(blueprint.inputs)

    rendered = BlueprintInputs(
        blueprint,
        {"use_blueprint": {"path": path.name, "input": inputs}},
    ).async_substitute()

    validated = PLATFORM_SCHEMA(rendered)
    assert validated["triggers"]
    assert validated["actions"]
