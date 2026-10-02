from pathlib import Path

import streamlit.components.v1 as components

BASE = Path(__file__).parent / "components"
_concept = components.declare_component("signalstory_concept", path=str(BASE / "concept"))
_scene = components.declare_component("signalstory_scene", path=str(BASE / "scene"))
_hero = components.declare_component("signalstory_hero", path=str(BASE / "hero"))
_profile = components.declare_component("signalstory_profile", path=str(BASE / "profile"))


def show(concept):
    component = _concept if concept["renderer"] == "promql" else _scene
    return component(
        animation=concept["animation"],
        level=concept["id"],
        title=concept["title"],
        key="scene-" + concept["id"],
        default=None,
    )


def hero():
    return _hero(key="signalstory-world", default=None)


def browser_profile(token, reset=False):
    return _profile(token=token, reset=reset, key="signalstory-profile", default=None)
