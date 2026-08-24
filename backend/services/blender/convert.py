"""GLB -> FBX converter, executed INSIDE Blender's own bundled Python via:

    blender --background --factory-startup --python-exit-code 1 \
            --python convert.py -- <in.glb> <out.fbx>

This script is NOT imported by the ArtSmoker backend/venv — Blender ships its own
Python (e.g. 3.11), and this file is handed to it as a `--python` argument. That is
why `import bpy` here is correct and required (bpy only exists inside Blender). The
"never import bpy in our process" rule (GPL + ABI reasons) applies to the backend
venv, NOT to a script Blender runs in its own interpreter.

Contract with the caller (backend/services/mesh_export.py):
  * exit 0 + "ARTSMOKER_CONVERT_OK" on stdout  -> success
  * any non-zero exit (+ "ARTSMOKER_CONVERT_ERROR: ..." on stderr) -> failure

Keep this stdlib-only (plus bpy/addon_utils); it must run under Blender's Python,
not ours, so no backend imports and no third-party deps.
"""
import sys


def _args_after_dashdash():
    """Return the args passed after the `--` separator (Blender's convention)."""
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def main():
    args = _args_after_dashdash()
    if len(args) < 2:
        print("ARTSMOKER_CONVERT_ERROR: expected <in.glb> <out.fbx>", file=sys.stderr)
        sys.exit(2)
    src, dst = args[0], args[1]

    import bpy
    import addon_utils

    # Enable the built-in glTF importer + FBX exporter (idempotent; both ship with
    # Blender >= 2.8). default_set=False so we don't mutate the user's saved prefs.
    for addon in ("io_scene_gltf2", "io_scene_fbx"):
        try:
            addon_utils.enable(addon, default_set=False, persistent=False)
        except Exception as e:  # noqa: BLE001 - report the exact add-on failure
            print(f"ARTSMOKER_CONVERT_ERROR: cannot enable {addon}: {e}", file=sys.stderr)
            sys.exit(3)

    # Start from a genuinely empty scene (belt-and-suspenders with --factory-startup)
    # so nothing from a default cube/camera/light leaks into the export.
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    except Exception as e:  # noqa: BLE001
        print(f"ARTSMOKER_CONVERT_ERROR: cannot reset scene: {e}", file=sys.stderr)
        sys.exit(3)

    # Import the source GLB.
    try:
        bpy.ops.import_scene.gltf(filepath=src)
    except Exception as e:  # noqa: BLE001
        print(f"ARTSMOKER_CONVERT_ERROR: glTF import failed: {e}", file=sys.stderr)
        sys.exit(4)

    # Export FBX. path_mode='COPY' + embed_textures=True packs the textures INTO the
    # .fbx so the single file is self-contained. Base color + normal + UVs + geometry
    # survive; metallic/roughness must be re-hooked up on engine import (an FBX format
    # limitation, not a bug — artists re-wire materials on import).
    try:
        bpy.ops.export_scene.fbx(
            filepath=dst,
            path_mode='COPY',
            embed_textures=True,
            use_selection=False,      # export the whole imported scene
            bake_space_transform=False,
        )
    except Exception as e:  # noqa: BLE001
        print(f"ARTSMOKER_CONVERT_ERROR: FBX export failed: {e}", file=sys.stderr)
        sys.exit(5)

    print("ARTSMOKER_CONVERT_OK")


if __name__ == "__main__":
    main()
