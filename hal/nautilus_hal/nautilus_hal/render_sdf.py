"""Render the Nautilus glider SDF from a Jinja2 template + HydrodynamicsSpec.

`render_sdf` is the launch-time hook that decides whether a sampled
parameter sweep is in play. If `hydro is None` it returns the canonical
SDF path unchanged — no template read, no temp file, no behaviour
change for everyday runs. If `hydro` is a `HydrodynamicsSpec`, it
renders `model.sdf.jinja` with that spec into a temp file and returns
the temp path; the launch passes that path to the Gazebo spawner.

Sampling strategy is *not* this module's concern: any orchestrator that
generates `HydrodynamicsSpec` instances (Latin Hypercube, Sobol,
Monte Carlo, hand-picked corner cases) plugs in the same way. We just
render one spec at a time.

The `sdf_num` Jinja filter formats integer-valued floats without a
trailing `.0` (so `-108.0` renders as `-108`, matching the canonical
SDF byte-for-byte). The Tier 3 parity test locks this in: rendering
`model.sdf.jinja` with `HydrodynamicsSpec()` defaults must equal the
canonical `model.sdf`.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

import jinja2

from py_pkg.scenarios.spec.rig import HydrodynamicsSpec


def _sdf_num(v: float) -> str:
    """Format a float for an SDF leaf the same way Gazebo's SDF authors do.

    Integer-valued floats drop the decimal point (`-108.0` -> `-108`),
    everything else uses Python's default `str(float)` which keeps the
    natural precision of the source values in `HydrodynamicsSpec`.
    """
    f = float(v)
    if f == int(f):
        return str(int(f))
    return str(f)


def _render(hydro: HydrodynamicsSpec, template_path: str | Path) -> str:
    env = jinja2.Environment(
        autoescape=False,
        keep_trailing_newline=True,
        # Defaults raise on missing keys; we want any typo in the template
        # to fail loudly rather than silently produce an empty XML leaf.
        undefined=jinja2.StrictUndefined,
    )
    env.filters["sdf_num"] = _sdf_num
    template = env.from_string(Path(template_path).read_text())
    return template.render(**hydro.model_dump())


def render_sdf(
    hydro: Optional[HydrodynamicsSpec],
    template_path: str | Path,
    canonical_path: str | Path,
) -> str:
    """Return a path to the SDF the spawner should load.

    When `hydro is None`, returns `canonical_path` verbatim — the launch
    is bit-identical to the pre-templating flow. When `hydro` is set,
    renders `template_path` and writes the result to a NamedTemporaryFile
    (kept on disk; the OS cleans `/tmp` between boots), returning the
    temp path. The temp file's basename embeds `nautilus_sdf_` so a
    `ls /tmp` after a sim crash is self-explanatory.
    """
    if hydro is None:
        return str(canonical_path)

    rendered = _render(hydro, template_path)
    fd = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".sdf",
        prefix="nautilus_sdf_",
        delete=False,
    )
    try:
        fd.write(rendered)
    finally:
        fd.close()
    return fd.name


def description_file_for_scenario(scenario_path: str | Path) -> str:
    """Launch-side convenience: resolve the SDF path for a scenario YAML.

    Reads `rig.hydrodynamics` from `scenario_path`. If the block is
    absent (i.e. `None`), returns the canonical
    `<dave_robot_models>/description/glider_nautilus/model.sdf` —
    no render, no temp file. If present, renders
    `model.sdf.jinja` from the same dir with those values and returns
    the temp file path.

    Called from each HAL sim launch (trim/sawtooth/surface) inside an
    OpaqueFunction; the resulting path is forwarded to
    `dave_robot.launch.py` as `description_file:=...`. A sampling
    orchestrator drops one YAML per sweep point and the launch picks
    it up the same way every other scenario flows.
    """
    # ament_index_python isn't on the path until the workspace is
    # sourced; the unit parity test imports `render_sdf` directly (not
    # this helper) so the deferred import keeps that test cheap.
    from ament_index_python.packages import get_package_share_directory

    from py_pkg.scenarios.loader import load_scenario

    share = Path(get_package_share_directory("dave_robot_models"))
    model_dir = share / "description" / "glider_nautilus"
    template = model_dir / "model.sdf.jinja"
    canonical = model_dir / "model.sdf"

    scenario = load_scenario(scenario_path)
    return render_sdf(scenario.rig.hydrodynamics, template, canonical)
