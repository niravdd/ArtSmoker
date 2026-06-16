import numpy as np
import open3d as o3d
import pymeshlab
import torch
import trimesh

try:
    from pymeshlab import Percentage
except (ImportError, AttributeError):
    try:
        from pymeshlab import PercentageValue as Percentage
    except (ImportError, AttributeError):
        Percentage = lambda x: x


### Mesh Utils ###
##### read mesh
def read_mesh_from_path(mesh_path):
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(mesh_path)
    return ms


def mesh_to_meshlab(vertices, faces):
    mesh = pymeshlab.Mesh(vertex_matrix=vertices, face_matrix=faces)
    ms = pymeshlab.MeshSet()
    ms.add_mesh(mesh)
    return ms


def meshlab_to_mesh(ms):
    m = ms.current_mesh()
    return m.vertex_matrix(), m.face_matrix(), m.vertex_normal_matrix()


##### decimation
def decimate_quadric_edge_collapse_with_texture(
    ms, targetfacenum=None, preservenormal=True, verbose=False
):
    # targetfacenum: int, Target number of faces.
    # preservenormal: bool, Preserve the normals of the original mesh.
    if verbose:
        print("Starting decimation ...  ")
    m = ms.current_mesh()
    if targetfacenum is None:
        targetfacenum = int(m.face_number() * 0.5)
    if verbose:
        print("... Initial face number is %d ... " % m.face_number())
    ms.meshing_decimation_quadric_edge_collapse_with_texture(
        targetfacenum=targetfacenum, preservenormal=preservenormal
    )
    if verbose:
        print("... Decimated face number is %d ... " % m.face_number())
        print("Decimation done!\n ")


def decimate_quadric_edge_collapse(
    ms, targetfacenum=None, preservenormal=True, verbose=False
):
    # targetfacenum: int, Target number of faces.
    # preservenormal: bool, Preserve the normals of the original mesh.
    if verbose:
        print("Starting decimation ...  ")
    m = ms.current_mesh()
    if targetfacenum is None:
        targetfacenum = int(m.face_number() * 0.5)
    if verbose:
        print("... Initial face number is %d ... " % m.face_number())
    ms.meshing_decimation_quadric_edge_collapse(
        targetfacenum=targetfacenum, preservenormal=preservenormal
    )
    if verbose:
        print("... Decimated face number is %d ... " % m.face_number())
        print("Decimation done!\n ")


##### vertex merge
def merge_close_vertices(ms, threshold=0.0001, verbose=False):
    # threshold: float, Merge together all the vertices that are nearer than the specified threshold.
    if verbose:
        print("Starting merge vertices ...  ")
    m = ms.current_mesh()
    if verbose:
        print("... Initial vertex number is %d ... " % m.vertex_number())
    ms.meshing_merge_close_vertices(threshold=Percentage(threshold * 100))
    if verbose:
        print("... Merged vertex number is %d ... " % m.vertex_number())
        print("Merge vertices done!\n ")


##### Island Removal
def remove_isolated_pieces(ms, mincomponentsize=25, diameter=None, verbose=False):
    # mincomponentsize: Delete isolated connected components composed by a limited number of triangles
    # diameter: Delete isolated connected components whose diameter is smaller than the specified constant
    if verbose:
        print("Starting remove isolated pieces ...  ")
    m = ms.current_mesh()
    if verbose:
        print("... Initial face number is %d ... " % m.face_number())
    if diameter is None:
        ms.meshing_remove_connected_component_by_face_number(
            mincomponentsize=mincomponentsize, removeunref=True
        )
    else:
        ms.meshing_remove_connected_component_by_diameter(
            mincomponentdiag=Percentage(diameter), removeunref=True
        )
    if verbose:
        print("... Isolated removed face number is %d ... " % m.face_number())
        print("Remove isolated pieces done!\n ")


##### hole filling
def fix_hole(ms, maxholesize=30, verbose=False):
    # maxholesize: int, Maximum size of the hole to be filled.
    if verbose:
        print("Starting fix holes ...  ")
    m = ms.current_mesh()
    if verbose:
        print("... Initial face number is %d ... " % m.face_number())
    if hasattr(ms, 'meshing_close_holes'):
        ms.meshing_close_holes(maxholesize=maxholesize)
    elif hasattr(ms, 'close_holes'):
        ms.close_holes(maxholesize=maxholesize)
    else:
        pass
    if verbose:
        print("... Fixed hole face number is %d ... " % m.face_number())
        print("Fix holes done!\n ")


##### repair non manifold edges
def repair_non_manifold(ms, verbose=False):
    if verbose:
        print("Starting repair non manifold edges ...  ")
    m = ms.current_mesh()
    if verbose:
        print("... Initial face number is %d ... " % m.face_number())
    ms.meshing_repair_non_manifold_edges()
    ms.meshing_repair_non_manifold_vertices(vertdispratio=0.1)
    ms.meshing_remove_duplicate_faces()
    if verbose:
        print("... Fixed non manifold edges face number is %d ... " % m.face_number())
        print("Repair non manifold edges done!\n ")


##### laplacian_smooth
def laplacian_smooth(ms, stepsmoothnum=3, verbose=False):
    # stepsmoothnum: int, Number of smoothing steps to be performed
    if verbose:
        print("Starting laplacian smooth ...  ")
    m = ms.current_mesh()
    ms.apply_coord_laplacian_smoothing(stepsmoothnum=stepsmoothnum)
    if verbose:
        print("Laplacian smooth done!\n ")


##### taubin_smooth
def taubin_smooth(ms, stepsmoothnum=3, verbose=False):
    if verbose:
        print("Starting Taubin smooth ...  ")
    m = ms.current_mesh()
    ms.apply_coord_taubin_smoothing(stepsmoothnum=stepsmoothnum)
    if verbose:
        print("Taubin smooth done!\n ")


##### compute_normal
def compute_normal(ms, weightmode="Simple Average", verbose=False):
    if verbose:
        print("Starting compute_normal_per_vertex ...  ")
    m = ms.current_mesh()
    ms.compute_normal_per_vertex(weightmode=weightmode)
    if verbose:
        print("compute_normal_per_vertex done!\n ")


### Pre-process Mesh ###
def process_mesh(
    vertices,
    faces,
    threshold=0.0001,
    mincomponentRatio=0.02,
    targetfacenum=50000,
    maxholesize=30,
    stepsmoothnum=10,
    verbose=False,
):
    ms = mesh_to_meshlab(vertices, faces)

    ### Vertex Merge
    merge_close_vertices(ms, threshold=threshold, verbose=verbose)

    ### Island Removal
    faces = ms.current_mesh().face_matrix()
    remove_isolated_pieces(
        ms, mincomponentsize=int(len(faces) * mincomponentRatio), verbose=verbose
    )

    ### Hole Filling
    repair_non_manifold(ms)  # repair before fix hole
    fix_hole(ms, maxholesize=maxholesize, verbose=verbose)

    ### Taubin Smoothing
    taubin_smooth(ms, stepsmoothnum=stepsmoothnum, verbose=verbose)

    vertices, faces, _ = meshlab_to_mesh(ms)
    if faces.shape[0] > targetfacenum:
        device = o3d.core.Device("CPU:0")
        dtype_f = o3d.core.float32
        dtype_i = o3d.core.int64
        mesh = o3d.t.geometry.TriangleMesh(device)
        mesh.vertex.positions = o3d.core.Tensor(
            vertices.astype(np.float32), dtype_f, device
        )
        mesh.triangle.indices = o3d.core.Tensor(faces.astype(np.int64), dtype_i, device)
        simplified_mesh = mesh.simplify_quadric_decimation(
            target_reduction=1.0 - float(targetfacenum) / faces.shape[0]
        )
        ms.clear()
        vertices = simplified_mesh.vertex.positions.numpy()
        faces = simplified_mesh.triangle.indices.numpy()
        mesh = pymeshlab.Mesh(vertex_matrix=vertices, face_matrix=faces)
        ms.add_mesh(mesh)

    ### Mesh Simplification/Decimation
    # decimate_quadric_edge_collapse(ms, targetfacenum=targetfacenum, verbose=verbose)
    taubin_smooth(ms, stepsmoothnum=stepsmoothnum, verbose=verbose)
    repair_non_manifold(ms, verbose=verbose)
    compute_normal(ms, verbose=verbose)
    return meshlab_to_mesh(ms)


### UV Un-Warp ###
def uv_parameterize_uvatlas(
    vertices,
    faces,
    size=1024,
    gutter=2.5,
    max_stretch=0.1666666716337204,
    parallel_partitions=16,
    nthreads=0,
):
    # ARTSMOKER: xatlas-first UV unwrap. Open3D's compute_uvatlas (Microsoft
    # UVAtlas) raises an internal RuntimeError (ComputeUVAtlasPartition) on large/
    # complex marching-cubes meshes (observed on full ~1M-face TripoSG meshes),
    # which fails the whole texture bake. xatlas (MIT — same commercial-safe tier
    # as MVPainter/Open3D, NOT a Hunyuan dependency) robustly unwraps the full
    # mesh (proven on 1M faces). Try xatlas first, fall back to UVAtlas so the
    # MV-Adapter path (which already worked via UVAtlas on its decimated mesh) is
    # unchanged if xatlas is somehow unavailable.
    #
    # CONTRACT: must return per-face-corner UVs as (#F, 3, 2) — caller does
    # .reshape(-1,2) → (#F*3, 2) and pairs it with t_tex_idx = arange(#F*3).
    try:
        import xatlas as _xatlas
        # parametrize returns: vmapping (#xverts,), indices (#F,3) into the
        # xatlas vertex set, uvs (#xverts, 2). Gather per-corner UVs in ORIGINAL
        # face order so corner (f,i) lands at output[f, i] — matching t_tex_idx.
        _vmap, _indices, _uvs = _xatlas.parametrize(
            vertices.astype(np.float32), faces.astype(np.uint32)
        )
        if _indices.shape[0] != faces.shape[0]:
            # xatlas should preserve face count/order (it only duplicates verts
            # along UV seams, never adds/removes faces). If it didn't, the
            # per-face mapping below would be wrong — bail to UVAtlas.
            raise RuntimeError(
                "xatlas changed face count (%d→%d); falling back"
                % (faces.shape[0], _indices.shape[0])
            )
        # uvs indexed by xatlas vertex; _indices[f,i] is the xatlas vert for
        # corner i of face f → per-corner UV = _uvs[_indices]. Shape (#F, 3, 2).
        face_uvs = _uvs[_indices].astype(np.float32)
        return face_uvs
    except Exception as _xe:
        try:
            import logging as _lg
            _lg.getLogger("artsmoker").warning(
                "xatlas UV unwrap failed (%s) — falling back to Open3D UVAtlas", _xe)
        except Exception:
            pass

    device = o3d.core.Device("CPU:0")
    dtype_f = o3d.core.float32
    dtype_i = o3d.core.int64

    mesh = o3d.t.geometry.TriangleMesh(device)

    mesh.vertex.positions = o3d.core.Tensor(
        vertices.astype(np.float32), dtype_f, device
    )
    mesh.triangle.indices = o3d.core.Tensor(faces.astype(np.int64), dtype_i, device)

    mesh.compute_uvatlas(
        size=size,
        gutter=gutter,
        max_stretch=max_stretch,
        parallel_partitions=parallel_partitions,
        nthreads=nthreads,
    )

    return mesh.triangle.texture_uvs.numpy()  # (#F, 3, 2)


### Pack All ###
def _repair_mesh_trimesh(mesh, targetfacenum=50000):
    """Fallback manifold repair using trimesh when pymeshlab is unavailable.

    CRITICAL: this also DECIMATES to targetfacenum (matching pymeshlab's
    process_mesh targetfacenum=50000). When pymeshlab's plugins fail to load
    (e.g. missing libOpenGL on a headless container), the texture pipeline's
    built-in decimation is otherwise skipped, so the FULL high-poly mesh (up to
    1M faces) flows into UV parameterization + the voxel grid. That spikes
    memory non-deterministically and silently kills the worker in Phase 3
    (observed: crash right after 'final grids shape = [1024,1024,1024]').
    Texture quality is unaffected — the texture pipeline was designed to bake
    onto a ~50K-face mesh (the 4096² UV atlas holds the detail), and the user's
    high-poly geometry from Phase 1 is a separate output. Decimating here makes
    Phase 3 stable and deterministic.
    """
    mesh.merge_vertices()
    mask = mesh.nondegenerate_faces()
    mesh.update_faces(mask)
    unique = mesh.unique_faces()
    mesh.update_faces(unique)
    mesh.remove_unreferenced_vertices()
    trimesh.repair.fix_winding(mesh)
    trimesh.repair.fix_normals(mesh)
    trimesh.repair.fill_holes(mesh)
    # Decimate to keep Phase 3 (Open3D compute_uvatlas + voxel grid + Poisson)
    # within memory. IMPORTANT: trimesh.simplify_quadric_decimation needs the
    # 'fast_simplification' package, which is NOT installed on the container —
    # it raises ModuleNotFoundError and silently no-ops, letting the full ~1M
    # face mesh reach Open3D's compute_uvatlas (parallel_partitions scales up
    # and OOM-kills the worker). Use Open3D's tensor-mesh decimation instead
    # (o3d is always available here — the pipeline uses it throughout).
    n = len(mesh.faces)
    if targetfacenum and n > targetfacenum:
        try:
            o3m = o3d.t.geometry.TriangleMesh(o3d.core.Device("CPU:0"))
            o3m.vertex.positions = o3d.core.Tensor(
                np.asarray(mesh.vertices, dtype=np.float32), o3d.core.float32, o3d.core.Device("CPU:0")
            )
            o3m.triangle.indices = o3d.core.Tensor(
                np.asarray(mesh.faces, dtype=np.int64), o3d.core.int64, o3d.core.Device("CPU:0")
            )
            simp = o3m.simplify_quadric_decimation(
                target_reduction=1.0 - float(targetfacenum) / n
            )
            v = simp.vertex.positions.numpy()
            f = simp.triangle.indices.numpy()
            mesh = trimesh.Trimesh(vertices=v, faces=f, process=False)
            trimesh.repair.fix_normals(mesh)
        except Exception as _e:
            import logging
            logging.getLogger("artsmoker").warning(
                "Open3D decimation failed (%s) — Phase 3 runs on full mesh, may OOM", _e
            )
    return mesh


def process_raw(mesh_path, save_path, preprocess=True, device="cpu"):
    scene = trimesh.load(mesh_path, force="mesh", process=False)
    if isinstance(scene, trimesh.Trimesh):
        mesh = scene
    elif isinstance(scene, trimesh.scene.Scene):
        mesh = trimesh.Trimesh()
        for obj in scene.geometry.values():
            mesh = trimesh.util.concatenate([mesh, obj])
    else:
        raise ValueError(f"Unknown mesh type at {mesh_path}.")

    vertices = mesh.vertices
    faces = mesh.faces

    if preprocess:
        if pymeshlab is not None:
            try:
                v_pos, t_pos_idx, normals = process_mesh(
                    vertices=vertices,
                    faces=faces,
                    mincomponentRatio=0.02,
                    targetfacenum=50000,
                    maxholesize=100,
                    stepsmoothnum=10,
                    verbose=False,
                )
            except Exception as _e:
                import logging
                logging.getLogger("artsmoker").warning("pymeshlab process_mesh failed (%s), using trimesh fallback", _e)
                mesh = _repair_mesh_trimesh(mesh)
                v_pos, t_pos_idx, normals = mesh.vertices, mesh.faces, mesh.vertex_normals
        else:
            mesh = _repair_mesh_trimesh(mesh)
            v_pos, t_pos_idx, normals = mesh.vertices, mesh.faces, mesh.vertex_normals
    else:
        v_pos, t_pos_idx, normals = vertices, faces, mesh.vertex_normals

    v_tex_np = (
        uv_parameterize_uvatlas(v_pos, t_pos_idx).reshape(-1, 2).astype(np.float32)
    )

    v_pos = torch.from_numpy(v_pos).to(device=device, dtype=torch.float32)
    t_pos_idx = torch.from_numpy(t_pos_idx).to(device=device, dtype=torch.long)
    v_tex = torch.from_numpy(v_tex_np).to(device=device, dtype=torch.float32)
    normals = torch.from_numpy(normals).to(device=device, dtype=torch.float32)
    assert v_tex.shape[0] == t_pos_idx.shape[0] * 3
    t_tex_idx = torch.arange(
        t_pos_idx.shape[0] * 3,
        device=device,
        dtype=torch.long,
    ).reshape(-1, 3)
    # uv, index = torch.unique(v_tex, dim=0, return_inverse=True) # 这样实现是2毫秒
    # super efficient de-duplication
    v_tex_u_uint32 = v_tex_np[..., 0].view(np.uint32)
    v_tex_v_uint32 = v_tex_np[..., 1].view(np.uint32)
    v_hashed = (v_tex_u_uint32.astype(np.uint64) << 32) | v_tex_v_uint32
    v_hashed = torch.from_numpy(v_hashed.view(np.int64)).to(v_pos.device)

    t_pos_idx_f3 = torch.arange(
        t_pos_idx.shape[0] * 3, device=t_pos_idx.device, dtype=torch.long
    ).reshape(-1, 3)
    v_pos_f3 = v_pos[t_pos_idx].reshape(-1, 3)
    normals_f3 = normals[t_pos_idx].reshape(-1, 3)

    v_hashed_dedup, inverse_indices = torch.unique(v_hashed, return_inverse=True)
    dedup_size, full_size = v_hashed_dedup.shape[0], inverse_indices.shape[0]
    indices = torch.scatter_reduce(
        torch.full(
            [dedup_size],
            fill_value=full_size,
            device=inverse_indices.device,
            dtype=torch.long,
        ),
        index=inverse_indices,
        src=torch.arange(full_size, device=inverse_indices.device, dtype=torch.int64),
        dim=0,
        reduce="amin",
    )
    v_tex = v_tex[indices]
    t_tex_idx = inverse_indices.reshape(-1, 3)

    v_pos = v_pos_f3[indices]
    normals = normals_f3[indices]

    normals = normals.to(dtype=torch.float32, device=device)

    # either flip uv or flip texture
    # here we flip uv
    uv_to_save = v_tex.clone()
    uv_to_save[:, 1] = 1.0 - uv_to_save[:, 1]

    visual = trimesh.visual.TextureVisuals(uv=uv_to_save.cpu().numpy())
    tmesh = trimesh.Trimesh(
        vertices=v_pos.cpu().numpy(),
        faces=t_tex_idx.cpu().numpy(),
        vertex_normals=normals.cpu().numpy(),
        visual=visual,
        process=False,
    )
    tmesh.export(save_path)
