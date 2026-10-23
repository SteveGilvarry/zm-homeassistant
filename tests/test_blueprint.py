"""The shipped blueprints must actually import and produce a valid automation."""

from __future__ import annotations

import asyncio
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
        "cameras": ["event.driveway_event"],
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


async def test_notification_blueprint_end_to_end(
    hass: HomeAssistant, setup_integration
) -> None:
    """Motion sends a picture; the end of the event adds the clip.

    This runs the shipped blueprint against the real event entity, including
    its very first event (from "unknown"), which a too-strict trigger dropped.
    """
    import shutil

    from homeassistant.core import ServiceCall, callback
    from homeassistant.helpers.dispatcher import async_dispatcher_send

    from custom_components.zoneminder.const import SIGNAL_MQTT_EVENT
    from custom_components.zoneminder.mqtt import ZoneMinderMQTTEvent

    target = Path(hass.config.path("blueprints/automation/zoneminder"))
    await hass.async_add_executor_job(
        lambda: (
            target.mkdir(parents=True, exist_ok=True),
            shutil.copy(BLUEPRINTS[0], target / BLUEPRINTS[0].name),
        )
    )

    sent: list[dict] = []

    @callback
    def _notify(call: ServiceCall) -> None:
        sent.append(dict(call.data))

    hass.services.async_register("notify", "phone", _notify)

    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "use_blueprint": {
                    "path": f"zoneminder/{BLUEPRINTS[0].name}",
                    "input": {
                        "cameras": ["event.back_door_event"],
                        "notify_target": "notify.phone",
                        "cooldown": 0,
                    },
                }
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get("event.back_door_event").state == "unknown"

    def _send(action: str) -> None:
        async_dispatcher_send(
            hass,
            SIGNAL_MQTT_EVENT.format(2),
            ZoneMinderMQTTEvent(monitor_id=2, event_id=298, action=action),
        )

    # The automation keeps running while it waits for the clip, so the test
    # can't wait for everything to finish between the two notices.
    _send("start")
    for _ in range(20):
        await asyncio.sleep(0)
    assert len(sent) == 1
    _send("end")
    await hass.async_block_till_done()

    assert len(sent) == 2
    assert sent[0]["message"].startswith("Motion at ")
    first, second = (s["data"] for s in sent)
    assert first["image"].startswith("/api/zoneminder/event/")
    assert first["tag"] == second["tag"] == "zoneminder-298"
    assert second["actions"][0]["uri"].endswith("/clip.mp4")
