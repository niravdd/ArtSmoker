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

    # ── Optional prep ops (only what the user explicitly chose) ──────────────
    prep = spec.get("prep") or {}

    # Lightmap UV2: a second UV layer, smart-projected (validated headless).
    if prep.get("uv2"):
        try:
            for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
                if len(ob.data.uv_layers) >= 2:
                    continue  # already has a second channel
                bpy.context.view_layer.objects.active = ob
                lm = ob.data.uv_layers.new(name="Lightmap")
                ob.data.uv_layers.active = lm
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.uv.smart_project(island_margin=0.02)
                bpy.ops.object.mode_set(mode='OBJECT')
                # Restore the original UV set as the render-active one.
                ob.data.uv_layers.active = ob.data.uv_layers[0]
        except Exception as e:  # noqa: BLE001
            print(f"ARTSMOKER_CONVERT_ERROR: UV2 generation failed: {e}", file=sys.stderr)
            sys.exit(7)

    # LOD chain: decimated copies under a LodGroup empty (fbx_type custom prop →
    # the FBX exporter writes a real LodGroup node that Unreal auto-imports; the
    # _LOD0.._LOD3 names double as Unity's LOD Group naming convention).
    if prep.get("lod_ratios"):
        try:
            ratios = prep["lod_ratios"]
            for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
                group = bpy.data.objects.new(ob.name + "_LODGroup", None)
                group["fbx_type"] = "LodGroup"
                bpy.context.scene.collection.objects.link(group)
                base_name = ob.name
                for i, r in enumerate(ratios):
                    lod = ob.copy()
                    lod.data = ob.data.copy()
                    lod.name = f"{base_name}_LOD{i}"
                    bpy.context.scene.collection.objects.link(lod)
                    if r < 1.0:
                        mod = lod.modifiers.new("dec", "DECIMATE")
                        mod.ratio = r
                        bpy.context.view_layer.objects.active = lod
                        bpy.ops.object.modifier_apply(modifier="dec")
                    lod.parent = group
                # The original stays out of the export (LOD0 is its copy).
                bpy.data.objects.remove(ob, do_unlink=True)
        except Exception as e:  # noqa: BLE001
            print(f"ARTSMOKER_CONVERT_ERROR: LOD generation failed: {e}", file=sys.stderr)
            sys.exit(8)

    # Collision hulls: import the pre-computed, convention-named hulls GLB
    # (UCX_* for Unreal-style auto-import; -convcolonly suffixes for Godot).
    if prep.get("collision_glb"):
        try:
            bpy.ops.import_scene.gltf(filepath=prep["collision_glb"])
            # Hulls are proxies: no material/texture needed; leave names as-is.
        except Exception as e:  # noqa: BLE001
            print(f"ARTSMOKER_CONVERT_ERROR: collision import failed: {e}", file=sys.stderr)
            sys.exit(9)

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

    # Processed GLB (prep ops baked in; Y-up per glTF spec, textures embedded).
    glb = spec.get("glb")
    if glb:
        try:
            bpy.ops.export_scene.gltf(filepath=glb["path"], **glb.get("kwargs", {}))
        except Exception as e:  # noqa: BLE001
            print(f"ARTSMOKER_CONVERT_ERROR: GLB export failed: {e}", file=sys.stderr)
            sys.exit(10)

    print("ARTSMOKER_CONVERT_OK")


if __name__ == "__main__":
    main()
