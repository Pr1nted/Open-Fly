"""A fruit fly at a desk, playing Open Doctrines on the monitor.

Run with Blender 2.93+ in background mode:
    Blender -b --factory-startup --python scene/fly_at_computer.py -- \
        --screens out/screens --taps out/taps.json --out out/frames/ [--res 1280x720] [--samples 16]

--screens  a folder of screen_0001.png ... one per video frame (the monitor's picture)
--taps     JSON list, one int per video frame: 0 none, 1 left front leg taps, 2 right
"""
import argparse
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Euler, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--screens", required=True)
ap.add_argument("--taps", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--res", default="1280x720")
ap.add_argument("--samples", type=int, default=16)
ap.add_argument("--only", type=int, default=0, help="render just this frame (a preview still)")
ap.add_argument("--export-glb", default=None, help="write the scene as .glb for the web viewer instead of rendering")
ap.add_argument("--brain", default=None, help="folder of brain_0001.png ... for the hologram beside the fly")
ap.add_argument("--wall-map", default=None, help="an image of the world map, hung above the monitor in place of the poster")
args = ap.parse_args(argv)

taps = json.load(open(args.taps))
N = len(taps)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, N
scene.render.fps = 24
scene.render.engine = "BLENDER_EEVEE"
w, h = (int(v) for v in args.res.split("x"))
scene.render.resolution_x, scene.render.resolution_y = w, h
scene.eevee.taa_render_samples = args.samples
scene.eevee.use_gtao = True
scene.eevee.use_soft_shadows = True
scene.eevee.use_bloom = True
scene.eevee.bloom_intensity = 0.03
scene.view_settings.look = "Medium High Contrast"


# ── materials ────────────────────────────────────────────────────────────────
def principled(name, color, rough=0.5, metal=0.0, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular"].default_value = spec
    return m


def striped(name, a, b_col, bands=5.0, rough=0.35):
    """Abdomen bands along the object's local Z."""
    m = principled(name, a, rough)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = bands
    fr = nt.nodes.new("ShaderNodeMath"); fr.operation = "FRACT"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "EASE"
    ramp.color_ramp.elements[0].position = 0.55
    ramp.color_ramp.elements[0].color = (*a, 1)
    ramp.color_ramp.elements[1].position = 0.8
    ramp.color_ramp.elements[1].color = (*b_col, 1)
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mul.inputs[0])
    nt.links.new(mul.outputs[0], fr.inputs[0])
    nt.links.new(fr.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], nt.nodes["Principled BSDF"].inputs["Base Color"])
    return m


def compound_eye(name):
    """Red, glossy, with a Voronoi bump for the ommatidia."""
    m = principled(name, (0.3, 0.008, 0.006), rough=0.38, spec=0.45)
    nt = m.node_tree
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 70.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15
    bump.invert = True
    nt.links.new(vor.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])
    return m


def glass_wing(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.blend_method = "BLEND"
    m.shadow_method = "HASHED"
    m.show_transparent_back = False
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.75, 0.8, 0.85, 1)
    b.inputs["Roughness"].default_value = 0.15
    b.inputs["Alpha"].default_value = 0.28
    b.inputs["Specular"].default_value = 0.9
    return m


def emissive_screen(name, first_image, frames):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.6
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(first_image)
    img.source = "SEQUENCE"
    tex.image = img
    tex.image_user.frame_duration = frames
    tex.image_user.frame_start = 1
    tex.image_user.frame_offset = 0
    tex.image_user.use_auto_refresh = True
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


BODY = principled("body", (0.22, 0.12, 0.04), rough=0.4)
THORAX = principled("thorax", (0.17, 0.10, 0.04), rough=0.45)
ABD = striped("abdomen", (0.34, 0.2, 0.07), (0.035, 0.02, 0.012))
LEG = principled("leg", (0.05, 0.03, 0.015), rough=0.55)
EYE = compound_eye("eye")
WING = glass_wing("wing")
WOOD = principled("wood", (0.28, 0.16, 0.08), rough=0.6)
PLASTIC = principled("plastic", (0.03, 0.03, 0.035), rough=0.35)
KEYCAP = principled("keycap", (0.07, 0.07, 0.08), rough=0.5)
CHAIR = principled("chair", (0.05, 0.05, 0.06), rough=0.7)
FLOOR = principled("floor", (0.10, 0.09, 0.09), rough=0.8)
WALL = principled("wall", (0.07, 0.08, 0.11), rough=0.9)
POSTER = principled("poster", (0.35, 0.05, 0.05), rough=0.8)


# ── helpers ──────────────────────────────────────────────────────────────────
def link(ob, mat=None, parent=None):
    if mat:
        ob.data.materials.append(mat)
    if parent:
        bpy.context.view_layer.update()
        mw = ob.matrix_world.copy()
        ob.parent = parent
        ob.matrix_world = mw
    return ob


def box(name, loc, size, mat, parent=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    if bevel:
        bpy.ops.object.transform_apply(scale=True)
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    return link(ob, mat, parent)


def blob(name, loc, scale, mat, parent=None, rot=(0, 0, 0), seg=48):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale
    bpy.ops.object.shade_smooth()
    return link(ob, mat, parent)


def rod(name, a, b, r, mat, parent=None, r2=None):
    """A tapered cylinder from a to b whose ORIGIN is at a, so it rotates at its joint."""
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=r, radius2=r2 if r2 else r * 0.8,
                                    depth=d.length, location=(0, 0, d.length / 2))
    ob = bpy.context.object
    ob.name = name
    bpy.ops.object.transform_apply(location=True)       # origin to the base
    ob.location = a
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    bpy.ops.object.shade_smooth()
    # a ball at the joint hides the seam
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=r * 1.05, location=a)
    knob = bpy.context.object
    knob.name = name + "_joint"
    bpy.ops.object.shade_smooth()
    link(knob, mat, ob)
    return link(ob, mat, parent)


def chain(name, points, radii, mat, parent):
    """Leg segments, each parented to the one before it. Returns the segments."""
    segs, prev = [], parent
    for i in range(len(points) - 1):
        s = rod(f"{name}_{i}", points[i], points[i + 1], radii[i], mat, prev, r2=radii[i + 1])
        segs.append(s)
        prev = s
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=radii[-1] * 1.4, location=points[-1])
    foot = bpy.context.object
    foot.name = name + "_claw"
    link(foot, mat, prev)
    return segs


# ── the room ─────────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
link(bpy.context.object, FLOOR)
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 1.7, 3), rotation=(math.radians(90), 0, 0))
link(bpy.context.object, WALL)
if args.wall_map:
    # The live page hangs the whole world on the wall; a still should show the same room.
    box("wall_map_frame", (-0.45, 1.685, 1.98), (1.82, 0.03, 0.97), PLASTIC, bevel=0.006)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-0.45, 1.665, 1.98), rotation=(math.radians(90), 0, 0))
    wall_map = bpy.context.object
    wall_map.name = "wall_map"
    wall_map.scale = (1.72, 0.86, 1)
    wm = bpy.data.materials.new("wall_map")
    wm.use_nodes = True
    wn = wm.node_tree
    for nd in list(wn.nodes):
        wn.nodes.remove(nd)
    wem = wn.nodes.new("ShaderNodeEmission")
    wem.inputs["Strength"].default_value = 1.3
    wtex = wn.nodes.new("ShaderNodeTexImage")
    wtex.image = bpy.data.images.load(os.path.abspath(args.wall_map))
    wn.links.new(wtex.outputs["Color"], wem.inputs["Color"])
    wn.links.new(wem.outputs[0], wn.nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])
    wall_map.data.materials.append(wm)
else:
    box("poster", (-1.1, 1.68, 1.55), (0.5, 0.01, 0.7), POSTER)

# desk
box("desk_top", (0, 0.55, 0.74), (1.8, 0.85, 0.05), WOOD, bevel=0.01)
for sx in (-0.85, 0.85):
    for sy in (0.18, 0.92):
        box("desk_leg", (sx, sy, 0.36), (0.05, 0.05, 0.72), WOOD)

# monitor
box("mon_base", (0, 0.88, 0.775), (0.28, 0.18, 0.02), PLASTIC, bevel=0.005)
box("mon_neck", (0, 0.92, 0.9), (0.05, 0.03, 0.25), PLASTIC)
box("mon_bezel", (0, 0.9, 1.16), (0.92, 0.035, 0.54), PLASTIC, bevel=0.008)
frames_dir = os.path.abspath(args.screens)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.88, 1.16), rotation=(math.radians(90), 0, 0))
screen = bpy.context.object
screen.name = "screen"
screen.scale = (0.86, 0.48375, 1)
screen.data.materials.append(emissive_screen("screen", os.path.join(frames_dir, "screen_0001.png"), N))

# keyboard and mouse
box("kb", (0, 0.48, 0.775), (0.5, 0.17, 0.02), PLASTIC, bevel=0.004)
KEYS = []
for row in range(4):
    for col in range(14):
        k = box("key", (-0.225 + col * 0.0346, 0.43 + row * 0.034, 0.79), (0.028, 0.028, 0.012), KEYCAP)
        KEYS.append(k)
blob("mouse", (0.38, 0.47, 0.775), (0.035, 0.06, 0.02), PLASTIC)

# chair
box("chair_seat", (0, -0.02, 0.47), (0.56, 0.52, 0.08), CHAIR, bevel=0.03)
back = box("chair_back", (0, -0.49, 0.74), (0.52, 0.06, 0.4), CHAIR, bevel=0.03)
back.rotation_euler = (math.radians(-10), 0, 0)
bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.4, location=(0, -0.02, 0.23))
link(bpy.context.object, PLASTIC)
for i in range(5):
    a = i * 2 * math.pi / 5
    rod("chair_foot", (0, -0.02, 0.05), (0.3 * math.cos(a), -0.02 + 0.3 * math.sin(a), 0.04), 0.02, PLASTIC)

# lights: a screen glow, a warm lamp, a dim cool fill
bpy.ops.object.light_add(type="AREA", location=(0, 0.82, 1.16), rotation=(math.radians(-90), 0, 0))
glow = bpy.context.object
glow.data.size, glow.data.size_y = 0.86, 0.48
glow.data.shape = "RECTANGLE"
glow.data.energy = 25
glow.data.color = (0.75, 0.85, 1.0)
bpy.ops.object.light_add(type="POINT", location=(0.95, 0.75, 1.35))
lamp = bpy.context.object
lamp.data.energy = 45
lamp.data.color = (1.0, 0.72, 0.45)
lamp.data.shadow_soft_size = 0.2
bpy.ops.object.light_add(type="AREA", location=(-1.5, -1.2, 2.6))
fill = bpy.context.object
fill.data.energy = 140
fill.data.size = 2.5
fill.data.color = (0.6, 0.7, 1.0)
fill.rotation_euler = (math.radians(35), math.radians(-35), 0)
world = bpy.data.worlds.new("world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.01, 0.012, 0.02, 1)
scene.world = world


# ── the fly ──────────────────────────────────────────────────────────────────
bpy.ops.object.empty_add(location=(0, 0, 0))
fly = bpy.context.object
fly.name = "Fly"

abdomen = blob("abdomen", (0, -0.12, 0.72), (0.19, 0.21, 0.29), ABD, fly, rot=(math.radians(-25), 0, 0))
thorax = blob("thorax", (0, 0.03, 0.93), (0.16, 0.19, 0.19), THORAX, fly, rot=(math.radians(20), 0, 0))
# scutum bristles, a few, for texture
def surface_point(center, radii, rot_x_deg, direction):
    """A point ON an ellipsoid blob (and its outward normal), from a direction in its own frame."""
    d = Vector(direction).normalized()
    t = 1.0 / math.sqrt((d.x / radii[0]) ** 2 + (d.y / radii[1]) ** 2 + (d.z / radii[2]) ** 2)
    p = d * t
    n = Vector((p.x / radii[0] ** 2, p.y / radii[1] ** 2, p.z / radii[2] ** 2)).normalized()
    rot = Euler((math.radians(rot_x_deg), 0, 0)).to_matrix()
    return Vector(center) + rot @ p, rot @ n


THORAX_C, THORAX_R, THORAX_ROT = (0, 0.03, 0.93), (0.16, 0.19, 0.19), 20
ABD_C, ABD_R, ABD_ROT = (0, -0.12, 0.72), (0.19, 0.21, 0.29), -25
# Macrochaetae: rooted on the thorax's own surface, leaning back along it.
for sx in (-1, 1):
    for d in ((sx * 0.35, -0.25, 0.9), (sx * 0.28, -0.62, 0.72)):
        root, normal = surface_point(THORAX_C, THORAX_R, THORAX_ROT, d)
        tip = root + normal * 0.055 + Vector((0, -0.035, 0))
        rod("bristle", tuple(root - normal * 0.006), tuple(tip), 0.004, LEG, thorax)

bpy.ops.object.empty_add(location=(0, 0.16, 1.1))
neck = bpy.context.object
neck.name = "neck"
link(neck, None, thorax)
head = blob("head", (0, 0.22, 1.16), (0.15, 0.12, 0.13), BODY, neck)
for sx in (-1, 1):
    blob("eye", (sx * 0.115, 0.26, 1.18), (0.07, 0.075, 0.1), EYE, head, rot=(0, math.radians(sx * 12), 0))
    ant = rod("antenna", (sx * 0.035, 0.32, 1.2), (sx * 0.045, 0.35, 1.24), 0.016, BODY, head)
    rod("arista", (sx * 0.045, 0.35, 1.24), (sx * 0.075, 0.38, 1.3), 0.003, LEG, ant)
rod("proboscis", (0, 0.3, 1.08), (0, 0.34, 1.02), 0.022, BODY, head)
for i in range(3):   # ocelli
    blob("ocellus", (-0.015 + 0.015 * i, 0.2, 1.285 - 0.004 * (i % 2)), (0.008, 0.008, 0.008), EYE, head, seg=12)

WINGS = []


def wing_shell(name, side, parent):
    """A folded wing: a patch of a shell just outside the abdomen, so it lies ON the body.

    A flat ellipse cannot follow a round abdomen -- its ends stood off the body
    and read as wings hanging in the air. This cuts the wing's outline out of a
    sphere, then gives it the abdomen's own radii (a few percent larger), tilt
    and centre, so every point of it sits just above the abdomen's back.
    """
    bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=1, location=(0, 0, 0))
    ob = bpy.context.object
    ob.name = name
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    outside = [v for v in bm.verts
               if not (v.co.y < -0.05 and ((v.co.x - side * 0.30) / 0.36) ** 2 + ((v.co.z - 0.2) / 0.74) ** 2 <= 1.0)]
    bmesh.ops.delete(bm, geom=outside, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.scale = (ABD_R[0] * 1.06, ABD_R[1] * 1.09, ABD_R[2] * 1.05)
    ob.rotation_euler = (math.radians(ABD_ROT), 0, 0)
    ob.location = ABD_C
    bpy.ops.object.shade_smooth()
    return link(ob, WING, parent)


for sx in (-1, 1):
    hinge_at, _ = surface_point(THORAX_C, THORAX_R, THORAX_ROT, (sx * 0.3, -0.8, -0.2))
    bpy.ops.object.empty_add(location=tuple(hinge_at))
    hinge = bpy.context.object
    hinge.name = f"wing_hinge_{sx}"
    link(hinge, None, thorax)
    wing_shell("wing", sx, hinge)
    WINGS.append(hinge)
    hinge.rotation_mode = "XYZ"

# Legs. Front legs reach the keyboard, middle legs rest on the armless seat's edge,
# hind legs hang off the front of the seat like a person's.
TAP = {}
for sx in (-1, 1):
    front = chain(f"front_{sx}",
                  [(sx * 0.1, 0.13, 0.86), (sx * 0.22, 0.2, 0.76), (sx * 0.2, 0.36, 0.78),
                   (sx * 0.12, 0.45, 0.76), (sx * 0.08, 0.5, 0.742)],
                  [0.026, 0.02, 0.016, 0.011, 0.009], LEG, thorax)
    TAP[sx] = front[1]      # the tibia taps
    chain(f"mid_{sx}",
          [(sx * 0.13, 0.03, 0.8), (sx * 0.34, 0.08, 0.66), (sx * 0.38, 0.1, 0.52), (sx * 0.42, 0.12, 0.3),
           (sx * 0.44, 0.14, 0.22)],
          [0.025, 0.019, 0.014, 0.01, 0.008], LEG, thorax)
    chain(f"hind_{sx}",
          [(sx * 0.12, -0.06, 0.66), (sx * 0.2, 0.27, 0.56), (sx * 0.22, 0.34, 0.24), (sx * 0.23, 0.42, -0.03),
           (sx * 0.24, 0.5, -0.05)],
          [0.027, 0.021, 0.016, 0.011, 0.009], LEG, abdomen)

fly.location = (0, 0.0, 0.06)


# ── animation ────────────────────────────────────────────────────────────────
def key_rot(ob, frame, dx=0.0, dz=0.0, base=None):
    ob.rotation_mode = "QUATERNION"
    from mathutils import Euler
    q0 = base if base is not None else ob.rotation_quaternion.copy()
    ob.rotation_quaternion = q0 @ Euler((dx, 0, dz)).to_quaternion()
    ob.keyframe_insert("rotation_quaternion", frame=frame)
    ob.rotation_quaternion = q0


tap_base = {sx: TAP[sx].rotation_quaternion.copy() for sx in TAP}
for sx in TAP:
    key_rot(TAP[sx], 1, base=tap_base[sx])
for f, t in enumerate(taps, start=1):
    if t in (1, 2):
        sx = -1 if t == 1 else 1
        key_rot(TAP[sx], max(1, f - 1), base=tap_base[sx])
        key_rot(TAP[sx], f, dx=math.radians(14), base=tap_base[sx])
        key_rot(TAP[sx], f + 2, base=tap_base[sx])

# head: small noise on the neck, and the whole fly breathes
neck.rotation_mode = "XYZ"
neck.keyframe_insert("rotation_euler", frame=1)
for i, fc in enumerate(neck.animation_data.action.fcurves):
    mod = fc.modifiers.new("NOISE")
    mod.scale = 18 + 5 * i
    mod.strength = 0.08
    mod.phase = 3 * i
thorax.keyframe_insert("location", frame=1)
mod = thorax.animation_data.action.fcurves[2].modifiers.new("NOISE")
mod.scale = 30
mod.strength = 0.008

# camera: from the fly's side (eyes, legs on the keys) round to over its shoulder (the map)
bpy.ops.object.empty_add(location=(0, 0.55, 1.0))
target = bpy.context.object
bpy.ops.object.camera_add(location=(-1.75, 0.15, 1.25))
cam = bpy.context.object
cam.data.lens = 38
scene.camera = cam
tt = cam.constraints.new("TRACK_TO")
tt.target = target
tt.track_axis = "TRACK_NEGATIVE_Z"
tt.up_axis = "UP_Y"
if args.brain:
    # The brain on a pedestal to the fly's left: a billboard that always faces
    # the camera, carrying a brain that turns inside it.
    BX, BY, BZ = -1.15, 0.35, 1.3
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.26, depth=0.025, location=(BX, BY, 1.02))
    link(bpy.context.object, PLASTIC)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.035, depth=1.02, location=(BX, BY, 0.51))
    link(bpy.context.object, PLASTIC)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.26, minor_radius=0.004, location=(BX, BY, 1.035))
    ring = bpy.context.object
    ring_mat = bpy.data.materials.new("ring")
    ring_mat.use_nodes = True
    rn = ring_mat.node_tree
    for nd in list(rn.nodes):
        rn.nodes.remove(nd)
    rem = rn.nodes.new("ShaderNodeEmission")
    rem.inputs["Color"].default_value = (0.95, 0.68, 0.25, 1)
    rem.inputs["Strength"].default_value = 2.5
    rn.links.new(rem.outputs[0], rn.nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])
    ring.data.materials.append(ring_mat)

    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0), rotation=(math.radians(90), 0, 0))
    holo = bpy.context.object
    holo.name = "brain_hologram"
    holo.scale = (0.9, 0.50625, 1)
    bpy.ops.object.transform_apply(rotation=True, scale=True)
    holo.location = (BX, BY, BZ)
    hm = bpy.data.materials.new("brain_hologram")
    hm.use_nodes = True
    hm.blend_method = "BLEND"
    hm.shadow_method = "NONE"
    hn = hm.node_tree
    for nd in list(hn.nodes):
        hn.nodes.remove(nd)
    hout = hn.nodes.new("ShaderNodeOutputMaterial")
    hmix = hn.nodes.new("ShaderNodeMixShader")
    htr = hn.nodes.new("ShaderNodeBsdfTransparent")
    hem = hn.nodes.new("ShaderNodeEmission")
    hem.inputs["Strength"].default_value = 3.2
    htex = hn.nodes.new("ShaderNodeTexImage")
    himg = bpy.data.images.load(os.path.join(os.path.abspath(args.brain), "brain_0001.png"))
    himg.source = "SEQUENCE"
    htex.image = himg
    htex.image_user.frame_duration = N
    htex.image_user.frame_start = 1
    htex.image_user.use_auto_refresh = True
    hn.links.new(htex.outputs["Color"], hem.inputs["Color"])
    hn.links.new(htex.outputs["Alpha"], hmix.inputs["Fac"])
    hn.links.new(htr.outputs[0], hmix.inputs[1])
    hn.links.new(hem.outputs[0], hmix.inputs[2])
    hn.links.new(hmix.outputs[0], hout.inputs["Surface"])
    holo.data.materials.append(hm)
    bpy.ops.object.light_add(type="POINT", location=(BX, BY - 0.2, BZ))
    haze = bpy.context.object
    haze.data.energy = 12
    haze.data.color = (0.45, 0.8, 0.75)
    trk = holo.constraints.new("LOCKED_TRACK")
    trk.target = cam
    trk.track_axis = "TRACK_NEGATIVE_Y"
    trk.lock_axis = "LOCK_Z"

if args.brain:
    cam.data.lens = 32
path = [(1, (-2.0, -1.9, 1.75), (-0.6, 0.35, 1.2)),
        (int(N * 0.35), (-1.1, -1.95, 1.95), (-0.55, 0.4, 1.2)),
        (int(N * 0.72), (-0.1, -1.85, 2.0), (-0.45, 0.5, 1.18)),
        (N, (0.75, -0.7, 1.72), (0.0, 0.86, 1.12))]
for f, loc, tgt in path:
    cam.location = loc
    cam.keyframe_insert("location", frame=f)
    target.location = tgt
    target.keyframe_insert("location", frame=f)

if args.export_glb:
    # The web viewer plays the screen as a video and animates the legs itself,
    # so the image sequence and the keyframes stay behind.
    screen.data.materials.clear()
    screen.data.materials.append(principled("screen_placeholder", (0, 0, 0)))
    for ob in list(scene.objects):
        if ob.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(ob, do_unlink=True)
    scene.frame_set(1)
    bpy.ops.export_scene.gltf(filepath=os.path.abspath(args.export_glb), export_format=("GLTF_EMBEDDED" if args.export_glb.endswith(".gltf") else "GLB"),
                              export_apply=True, export_animations=False, export_yup=True,
                              export_cameras=False, export_lights=False)
    print("exported", args.export_glb)
    sys.exit(0)

os.makedirs(args.out, exist_ok=True)
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = os.path.join(os.path.abspath(args.out), "frame_")
if args.only:
    scene.frame_set(args.only)
    scene.render.filepath = os.path.join(os.path.abspath(args.out), f"still_{args.only:04d}.png")
    bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
