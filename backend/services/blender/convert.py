"""GLB → FBX / USDZ converter, executed INSIDE Blender's own bundled Python via:

    blender --background --factory-startup --python-exit-code 1 \
            --python convert.py -- <in.glb> <spec.json>

`spec.json` (written by backend/services/mesh_export.py) selects which formats to
export and with what per-target orientation/scale:

    {
      "fbx": {"path": "/…/out.fbx",  "kwargs": {export_scene.fbx kwargs}},
      "usd": {"path": "/…/out.usdz", "kwargs": {wm.usd_export kwargs}}
    }

Only the keys present are exported (one Blender import serves both). This file is
NOT imported by the ArtSmoker venv — Blender runs it in its own Python, which is why
`import bpy` here is correct and required.

Contract with the caller:
  * exit 0 + "ARTSMOKER_CONVERT_OK" on stdout → success
  * any non-zero exit (+ "ARTSMOKER_CONVERT_ERROR: …" on stderr) → failure
"""
import json
import sys


def _args_after_dashdash():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def main():
    args = _args_after_dashdash()
    if len(args) < 2:
        print("ARTSMOKER_CONVERT_ERROR: expected <in.glb> <spec.json>", file=sys.stderr)
        sys.exit(2)
    src, spec_path = args[0], args[1]
    try:
        with open(spec_path) as fh:
            spec = json.load(fh)
    except Exception as e:  # noqa: BLE001
        print(f"ARTSMOKER_CONVERT_ERROR: cannot read spec: {e}", file=sys.stderr)
        sys.exit(2)

    import bpy
    import addon_utils

    # Built-in glTF importer + FBX exporter (idempotent; USD export is core, no add-on).
    for addon in ("io_scene_gltf2", "io_scene_fbx"):
        try:
            addon_utils.enable(addon, default_set=False, persistent=False)
        except Exception as e:  # noqa: BLE001
            print(f"ARTSMOKER_CONVERT_ERROR: cannot enable {addon}: {e}", file=sys.stderr)
            sys.exit(3)

    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    except Exception as e:  # noqa: BLE001
        print(f"ARTSMOKER_CONVERT_ERROR: cannot reset scene: {e}", file=sys.stderr)
        sys.exit(3)

    try:
        bpy.ops.import_scene.gltf(filepath=src)
    except Exception as e:  # noqa: BLE001
        print(f"ARTSMOKER_CONVERT_ERROR: glTF import failed: {e}", file=sys.stderr)
        sys.exit(4)

    # FBX (textures embedded → single self-contained file).
    fbx = spec.get("fbx")
    if fbx:
        try:
            bpy.ops.export_scene.fbx(filepath=fbx["path"], **fbx.get("kwargs", {}))
        except Exception as e:  # noqa: BLE001
            print(f"ARTSMOKER_CONVERT_ERROR: FBX export failed: {e}", file=sys.stderr)
            sys.exit(5)

    # USD — exported as .usdz (packaged) so textures travel in one file.
    usd = spec.get("usd")
    if usd:
        try:
            bpy.ops.wm.usd_export(filepath=usd["path"], **usd.get("kwargs", {}))
        except Exception as e:  # noqa: BLE001
            print(f"ARTSMOKER_CONVERT_ERROR: USD export failed: {e}", file=sys.stderr)
            sys.exit(6)

    print("ARTSMOKER_CONVERT_OK")


if __name__ == "__main__":
    main()
