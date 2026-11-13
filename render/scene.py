"""The letter he didn't finish": a golden hamster fell asleep writing to the judge.

A lined sheet on a warm desk reads "dear judge, / you are doing / so gre" and the last word runs off into a long,
sleepy crayon line that ends at the blue crayon still under his paw. A yellow sticky note in another hand
explains: "he means great. he worked on it all day. please don't wake him."

Everything is built here from primitives, metaballs, curves and text objects with Windows' handwriting fonts:
no external assets. Run headless with Blender 5.x:

    blender -b --factory-startup -P render/scene.py -- --out art/entry.png --res 1024 --samples 256
"""

import argparse
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector


# ------------------------------------------------------------------------------------------------ arguments
def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="art/entry.png")
    p.add_argument("--res", type=int, default=1024)
    p.add_argument("--samples", type=int, default=256)
    p.add_argument("--fur", type=float, default=1.0, help="fur density factor (lower for quick previews)")
    return p.parse_args(argv)


ARGS = parse_args()
FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
random.seed(7)


# ------------------------------------------------------------------------------------------------ helpers
def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def node(nt, kind, loc=(0, 0), **inputs):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def principled_of(mat):
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def new_material(name, color, rough=0.5, sss=0.0, sheen=0.0, coat=0.0, bump=0.0, bump_scale=60.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = principled_of(mat)
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    if sss:
        bsdf.inputs["Subsurface Weight"].default_value = sss
        bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.4, 0.25)
        bsdf.inputs["Subsurface Scale"].default_value = 0.04
    if sheen:
        bsdf.inputs["Sheen Weight"].default_value = sheen
        bsdf.inputs["Sheen Roughness"].default_value = 0.4
    if coat:
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = 0.05
    if bump:
        tc = node(nt, "ShaderNodeTexCoord", (-900, -300))
        noise = node(nt, "ShaderNodeTexNoise", (-700, -300), Scale=bump_scale, Detail=6.0, Roughness=0.6)
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
        b = node(nt, "ShaderNodeBump", (-400, -300), Strength=bump, Distance=0.02)
        nt.links.new(noise.outputs["Fac"], b.inputs["Height"])
        nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def crayon_material(name, color, grain=140.0, gaps=0.42):
    """Waxy crayon stroke: the colour with paper showing through in a fine grain (alpha from noise)."""
    mat = new_material(name, color, rough=0.55)
    nt = mat.node_tree
    bsdf = principled_of(mat)
    tc = node(nt, "ShaderNodeTexCoord", (-1000, 200))
    noise = node(nt, "ShaderNodeTexNoise", (-800, 200), Scale=grain, Detail=8.0, Roughness=0.75)
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-550, 200)
    ramp.color_ramp.elements[0].position = gaps
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = gaps + 0.12
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Alpha"])
    return mat


def hair_material(name, top, under, split_z, muzzle=None):
    """Principled Hair BSDF coloured by height: golden back fading to a white belly (object space)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = node(nt, "ShaderNodeOutputMaterial", (400, 0))
    h = nt.nodes.new("ShaderNodeBsdfHairPrincipled")
    h.location = (100, 0)
    h.parametrization = "COLOR"
    h.inputs["Roughness"].default_value = 0.38
    h.inputs["Radial Roughness"].default_value = 0.45
    h.inputs["Coat"].default_value = 0.0
    tc = node(nt, "ShaderNodeTexCoord", (-1200, 0))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1000, 0))
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    mr = node(nt, "ShaderNodeMapRange", (-800, 0))
    mr.interpolation_type = "SMOOTHERSTEP"
    mr.inputs["From Min"].default_value = split_z - 0.06
    mr.inputs["From Max"].default_value = split_z + 0.06
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    fac = mr.outputs["Result"]
    if muzzle is not None:
        c, r = muzzle
        d = node(nt, "ShaderNodeVectorMath", (-1000, -250))
        d.operation = "DISTANCE"
        d.inputs[1].default_value = c
        nt.links.new(tc.outputs["Object"], d.inputs[0])
        m2 = node(nt, "ShaderNodeMapRange", (-800, -250))
        m2.interpolation_type = "SMOOTHERSTEP"
        m2.inputs["From Min"].default_value = r * 0.6
        m2.inputs["From Max"].default_value = r
        nt.links.new(d.outputs["Value"], m2.inputs["Value"])
        mn = node(nt, "ShaderNodeMath", (-600, -100))
        mn.operation = "MINIMUM"
        nt.links.new(fac, mn.inputs[0])
        nt.links.new(m2.outputs["Result"], mn.inputs[1])
        fac = mn.outputs["Value"]
    # a little per-strand variation keeps the coat from looking like a plush toy
    info = node(nt, "ShaderNodeHairInfo", (-800, 300))
    jitter = node(nt, "ShaderNodeMath", (-600, 300))
    jitter.operation = "MULTIPLY_ADD"
    jitter.inputs[1].default_value = 0.25
    jitter.inputs[2].default_value = 0.85
    nt.links.new(info.outputs["Random"], jitter.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.location = (-400, 0)
    mix.inputs["A"].default_value = (*under, 1)
    mix.inputs["B"].default_value = (*top, 1)
    nt.links.new(fac, mix.inputs["Factor"])
    shade = nt.nodes.new("ShaderNodeMix")
    shade.data_type = "RGBA"
    shade.blend_type = "MULTIPLY"
    shade.location = (-150, 0)
    shade.inputs["Factor"].default_value = 1.0
    nt.links.new(mix.outputs["Result"], shade.inputs["A"])
    comb = node(nt, "ShaderNodeCombineColor", (-400, 300))
    for k in ("Red", "Green", "Blue"):
        nt.links.new(jitter.outputs["Value"], comb.inputs[k])
    nt.links.new(comb.outputs["Color"], shade.inputs["B"])
    nt.links.new(shade.outputs["Result"], h.inputs["Color"])
    nt.links.new(h.outputs[0], out.inputs["Surface"])
    return mat


def sphere(name, loc, scale, mat, rot=(0, 0, 0), segs=48):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=segs // 2, radius=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o


def ellipsoid(center, radii, rot=None):
    """A metaball ellipsoid element whose surface (threshold 0.6) sits at about the given radii."""
    k = 1.0 / 0.67
    return (center, 1.0, (radii[0] * k, radii[1] * k, radii[2] * k), rot)


def metaball_mesh(name, elements, mat, resolution=0.02):
    mb = bpy.data.metaballs.new(name)
    mb.resolution = resolution
    mb.render_resolution = resolution
    mb.threshold = 0.6
    for co, r, size, rot in elements:
        e = mb.elements.new()
        e.type = "ELLIPSOID"
        e.co = co
        e.radius = r
        e.size_x, e.size_y, e.size_z = size
        if rot is not None:
            e.rotation = rot
    obj = link(bpy.data.objects.new(name + "Meta", mb))
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    bpy.data.objects.remove(obj)
    out = link(bpy.data.objects.new(name, mesh))
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.materials.append(mat)
    return out


def add_fur(obj, mat, length, count, children, keep_out, seed, radius=0.0028):
    """Particle fur, thinned to nothing around the face features listed in keep_out [(local centre, radius)]."""
    vg = obj.vertex_groups.new(name="fur")
    for v in obj.data.vertices:
        w = 1.0
        for c, r in keep_out:
            t = ((v.co - Vector(c)).length - r) / (r * 0.7)
            w = min(w, max(0.0, min(1.0, t)))
        vg.add([v.index], w, "REPLACE")
    obj.data.materials.append(mat)
    obj.modifiers.new("Fur", "PARTICLE_SYSTEM")
    ps = obj.particle_systems[-1]
    ps.seed = seed
    ps.vertex_group_density = "fur"
    ps.vertex_group_length = "fur"
    st = ps.settings
    st.type = "HAIR"
    st.count = int(count * ARGS.fur)
    st.emit_from = "FACE"
    st.use_even_distribution = True
    st.material_slot = mat.name
    st.render_type = "PATH"
    st.render_step = 4
    st.display_step = 2
    st.child_type = "INTERPOLATED"
    st.rendered_child_count = children
    st.child_percent = 2
    st.child_radius = 0.03
    st.clump_factor = 0.2
    st.roughness_1 = 0.004
    st.roughness_1_size = 1.0
    st.roughness_endpoint = 0.008
    st.roughness_2 = 0.006
    st.factor_random = 0.002
    st.use_hair_bspline = True
    st.root_radius = 1.0
    st.tip_radius = 0.0
    st.radius_scale = radius
    st.hair_length = length  # last: other settings reset it


def local_hit(obj, origin, direction):
    """Ray-cast in obj's local space; returns (point, normal) in local space."""
    ok, loc, nor, _ = obj.ray_cast(Vector(origin), Vector(direction).normalized())
    if not ok:
        raise RuntimeError(f"no hit on {obj.name} from {origin}")
    return loc, nor


def curve_object(name, points, depth, mat, flat=None, smooth=True):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = depth
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    if smooth:
        sp = cu.splines.new("NURBS")
        sp.points.add(len(points) - 1)
        for i, p in enumerate(points):
            sp.points[i].co = (*p, 1)
        sp.use_endpoint_u = True
        sp.order_u = 4
        sp.resolution_u = 12
    else:
        sp = cu.splines.new("POLY")
        sp.points.add(len(points) - 1)
        for i, p in enumerate(points):
            sp.points[i].co = (*p, 1)
    o = link(bpy.data.objects.new(name, cu))
    o.data.materials.append(mat)
    return o


def text_object(name, body, font_file, size, loc, mat, rot_z=0.0, spacing=1.0):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.font = bpy.data.fonts.load(os.path.join(FONT_DIR, font_file))
    cu.size = size
    cu.space_line = spacing
    cu.resolution_u = 6
    o = link(bpy.data.objects.new(name, cu))
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    o.data.materials.append(mat)
    return o


def text_width(obj):
    bpy.context.view_layer.update()
    return obj.dimensions.x


# ------------------------------------------------------------------------------------------------ scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

M_DESK = new_material("Desk", (0.33, 0.17, 0.08), rough=0.45)
M_PAPER = new_material("Paper", (0.93, 0.91, 0.86), rough=0.85, bump=0.03, bump_scale=400)
M_STICKY = new_material("Sticky", (0.98, 0.83, 0.25), rough=0.8, bump=0.02, bump_scale=300)
M_BLUE = crayon_material("BlueCrayon", (0.015, 0.06, 0.42), gaps=0.28)
M_PENCIL = crayon_material("Pencil", (0.012, 0.012, 0.018), grain=260.0, gaps=0.08)
M_RED_LINE = new_material("Margin", (0.85, 0.25, 0.25), rough=0.8)
M_PINK = new_material("PawPink", (0.95, 0.55, 0.55), rough=0.45, sss=0.35)
M_EAR = new_material("Ear", (0.88, 0.48, 0.42), rough=0.5, sss=0.5, sheen=0.4)
M_NOSE = new_material("Nose", (0.85, 0.42, 0.45), rough=0.3, sss=0.3, coat=0.4)
M_LID = new_material("Lid", (0.06, 0.03, 0.02), rough=0.4)
M_SKIN = new_material("Skin", (0.80, 0.52, 0.30), rough=0.6, sss=0.3)
M_WAX_BLUE = new_material("WaxBlue", (0.05, 0.18, 0.72), rough=0.35, coat=0.2)
M_WRAP_BLUE = new_material("WrapBlue", (0.03, 0.10, 0.45), rough=0.7)
M_WAX_RED = new_material("WaxRed", (0.75, 0.06, 0.05), rough=0.35, coat=0.2)
M_WAX_GREEN = new_material("WaxGreen", (0.08, 0.45, 0.12), rough=0.35, coat=0.2)
M_WRAP_LABEL = new_material("Label", (0.9, 0.85, 0.7), rough=0.7)
M_FUR = hair_material("Fur", top=(0.62, 0.30, 0.09), under=(0.92, 0.86, 0.78), split_z=0.17,
                      muzzle=((0.0, -0.52, 0.17), 0.2))

# --- desk: wood grain from a stretched wave texture
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -0.002))
desk = bpy.context.active_object
desk.data.materials.append(M_DESK)
nt = M_DESK.node_tree
tc = node(nt, "ShaderNodeTexCoord", (-1200, 0))
mp = node(nt, "ShaderNodeMapping", (-1000, 0))
mp.inputs["Scale"].default_value = (0.12, 2.5, 1.0)
nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
wave = node(nt, "ShaderNodeTexNoise", (-800, 0), Scale=2.0, Detail=10.0, Roughness=0.6)
nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.location = (-550, 0)
ramp.color_ramp.elements[0].position = 0.3
ramp.color_ramp.elements[1].position = 0.7
ramp.color_ramp.elements[0].color = (0.22, 0.10, 0.04, 1)
ramp.color_ramp.elements[1].color = (0.36, 0.18, 0.08, 1)
nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], principled_of(M_DESK).inputs["Base Color"])

# --- the letter: a lined sheet, a touch rotated
PAPER_ROT = math.radians(-3.0)
PAPER_W, PAPER_H = 3.5, 4.4
bpy.ops.mesh.primitive_plane_add(size=1, location=(0.0, 0.15, 0.0), rotation=(0, 0, PAPER_ROT))
paper = bpy.context.active_object
paper.scale = (PAPER_W, PAPER_H, 1)
paper.data.materials.append(M_PAPER)
# ruled lines: blue stripes along object-space Y, a red margin
nt = M_PAPER.node_tree
tc = node(nt, "ShaderNodeTexCoord", (-1400, 300))
sep = node(nt, "ShaderNodeSeparateXYZ", (-1200, 300))
nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
RULE = 0.52 / PAPER_H  # object-space spacing of the rules (sheet is scaled)
yy = node(nt, "ShaderNodeMath", (-1000, 300))
yy.operation = "WRAP"
yy.inputs[1].default_value = 0.0
yy.inputs[2].default_value = RULE
nt.links.new(sep.outputs["Y"], yy.inputs[0])
rule = node(nt, "ShaderNodeMapRange", (-800, 300))
rule.inputs["From Min"].default_value = 0.0
rule.inputs["From Max"].default_value = 0.012 / PAPER_H
rule.inputs["To Min"].default_value = 1.0
rule.inputs["To Max"].default_value = 0.0
nt.links.new(yy.outputs["Value"], rule.inputs["Value"])
top_cut = node(nt, "ShaderNodeMath", (-800, 100))
top_cut.operation = "LESS_THAN"
top_cut.inputs[1].default_value = 0.36
nt.links.new(sep.outputs["Y"], top_cut.inputs[0])
rule_m = node(nt, "ShaderNodeMath", (-600, 300))
rule_m.operation = "MULTIPLY"
nt.links.new(rule.outputs["Result"], rule_m.inputs[0])
nt.links.new(top_cut.outputs["Value"], rule_m.inputs[1])
mix = nt.nodes.new("ShaderNodeMix")
mix.data_type = "RGBA"
mix.location = (-400, 300)
mix.inputs["A"].default_value = (0.93, 0.91, 0.86, 1)
mix.inputs["B"].default_value = (0.45, 0.62, 0.85, 1)
nt.links.new(rule_m.outputs["Value"], mix.inputs["Factor"])
margin = node(nt, "ShaderNodeMapRange", (-800, 500))
margin.interpolation_type = "LINEAR"
xm = node(nt, "ShaderNodeMath", (-1000, 500))
xm.operation = "ABSOLUTE"
xs = node(nt, "ShaderNodeMath", (-1100, 500))
xs.operation = "ADD"
xs.inputs[1].default_value = 0.5 - 0.42 / PAPER_W
nt.links.new(sep.outputs["X"], xs.inputs[0])
nt.links.new(xs.outputs["Value"], xm.inputs[0])
margin.inputs["From Min"].default_value = 0.0
margin.inputs["From Max"].default_value = 0.007 / PAPER_W * 2
margin.inputs["To Min"].default_value = 1.0
margin.inputs["To Max"].default_value = 0.0
nt.links.new(xm.outputs["Value"], margin.inputs["Value"])
mix2 = nt.nodes.new("ShaderNodeMix")
mix2.data_type = "RGBA"
mix2.location = (-200, 300)
mix2.inputs["B"].default_value = (0.85, 0.3, 0.3, 1)
nt.links.new(mix.outputs["Result"], mix2.inputs["A"])
nt.links.new(margin.outputs["Result"], mix2.inputs["Factor"])
nt.links.new(mix2.outputs["Result"], principled_of(M_PAPER).inputs["Base Color"])


def on_paper(x, y, z=0.0015):
    """A point given in the sheet's own (unscaled) frame, x right and y up, mapped to the world."""
    c, s = math.cos(PAPER_ROT), math.sin(PAPER_ROT)
    return Vector((paper.location.x + c * x - s * y, paper.location.y + s * x + c * y, z))


# the sheet's rules sit at multiples of 0.52 from its centre; write on them
def rule_y(k):
    return k * 0.52 - paper.location.y * 0 + 0.0


LEFT = -PAPER_W / 2 + 0.55
L1 = text_object("Line1", "dear judge,", "Inkfree.ttf", 0.52, on_paper(LEFT, rule_y(3) + 0.03), M_BLUE, PAPER_ROT)
L2 = text_object("Line2", "you are doing", "Inkfree.ttf", 0.46, on_paper(LEFT, rule_y(2) + 0.03), M_BLUE, PAPER_ROT)
L3 = text_object("Line3", "so gre", "Inkfree.ttf", 0.46, on_paper(LEFT, rule_y(1) + 0.03), M_BLUE, PAPER_ROT)
for t in (L1, L2, L3):
    t.data.extrude = 0.0
    t.data.offset = 0.008  # a hair bolder, the way a crayon writes

# --- the hamster (local frame: face toward -Y, belly on the paper)
HAM_LOC = on_paper(0.62, -1.2, 0.0)
HAM_SCALE = 1.6
HAM_ROT = math.radians(-18.0)
ham = metaball_mesh("Hamster", [
    ellipsoid((0.0, 0.20, 0.25), (0.40, 0.46, 0.27)),          # body, a round loaf
    ellipsoid((0.0, 0.40, 0.21), (0.37, 0.30, 0.22)),          # rump
    ellipsoid((0.0, -0.22, 0.24), (0.34, 0.31, 0.26)),         # head, big and resting low (asleep)
    ellipsoid((-0.2, -0.32, 0.16), (0.17, 0.17, 0.15)),        # cheek pouch L
    ellipsoid((0.2, -0.32, 0.16), (0.17, 0.17, 0.15)),         # cheek pouch R
    ellipsoid((0.0, -0.45, 0.17), (0.12, 0.12, 0.11)),         # muzzle
    ellipsoid((0.33, 0.50, 0.07), (0.12, 0.17, 0.07)),         # hind foot peeking out
], M_SKIN, resolution=0.015)
ham.location = HAM_LOC
ham.rotation_euler = (0, 0, HAM_ROT)
ham.scale = (HAM_SCALE,) * 3
bpy.context.view_layer.update()

# The face is laid out on the head as the camera sees it: rays along the camera's view direction (in the
# hamster's frame), offset across the screen by (u right, v up) from the head's centre.
CAM_TILT = math.radians(40)
VIEW = Matrix.Rotation(-HAM_ROT, 3, "Z") @ Vector((0.0, math.sin(CAM_TILT), -math.cos(CAM_TILT)))
RIGHT = VIEW.cross(Vector((0, 0, 1))).normalized()
UP = RIGHT.cross(VIEW).normalized()
HEAD_C = Vector((0.0, -0.30, 0.20))


def face_hit(u, v):
    return local_hit(ham, HEAD_C + RIGHT * u + UP * v - VIEW * 3.0, VIEW)


nose_p, nose_n = face_hit(0.0, -0.035)
EYE_U, EYE_V = 0.135, 0.085
eyes = [face_hit(side * EYE_U, EYE_V) for side in (-1, 1)]
keep = [(nose_p, 0.06)] + [(p, 0.075) for p, _ in eyes]


def child(o):
    o.parent = ham
    return o


nose = child(sphere("Nose", nose_p + nose_n * 0.004, (0.034, 0.03, 0.024), M_NOSE))
for i, side in enumerate((-1, 1)):
    # a sleepy closed eye: a soft downward curve, like a smile
    pts = []
    for k in range(11):
        t = k / 10
        u = side * EYE_U + (t - 0.5) * 0.12
        v = EYE_V - 0.026 * math.sin(math.pi * t)
        q, nn = face_hit(u, v)
        pts.append(tuple(q + nn * 0.006))
    child(curve_object(f"Lid{i}", pts, 0.011, M_LID))
# a tiny contented mouth under the nose
mouth = []
for k in range(13):
    t = k / 12
    u = (t - 0.5) * 0.08
    v = -0.075 - 0.012 * math.sin(2 * math.pi * t) ** 2
    q, nn = face_hit(u, v)
    mouth.append(tuple(q + nn * 0.005))
child(curve_object("Mouth", mouth, 0.006, M_LID))
keep.append((face_hit(0.0, -0.075)[0], 0.05))
# ears: round and pink, up on the head
for side in (-1, 1):
    child(sphere(f"Ear{side}", (side * 0.21, -0.12, 0.43), (0.10, 0.035, 0.095), M_EAR,
                 rot=(math.radians(-20), side * math.radians(25), 0)))
# front paws, tucked by the chin, curled round the crayon
for side in (-1, 1):
    child(sphere(f"Paw{side}", (side * 0.12, -0.50, 0.035), (0.055, 0.075, 0.032), M_PINK))
    for f in range(3):
        child(sphere(f"Toe{side}{f}", (side * (0.09 + f * 0.028), -0.57, 0.03), (0.016, 0.02, 0.016), M_PINK,
                     segs=16))
child(sphere("HindPad", (0.36, 0.66, 0.05), (0.05, 0.03, 0.04), M_PINK))


def crayon(name, start, direction, length, wax, wrap, parent=None):
    """A wax crayon lying on its side: a hexagon-ish rod, a paper wrapper with a label band, a cone tip."""
    d = Vector(direction).normalized()
    rot = d.to_track_quat("Z", "Y").to_euler()
    r = 0.045
    tip_len = 0.09
    body_len = length - tip_len
    mid = Vector(start) + d * (tip_len + body_len / 2)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r, depth=body_len, location=mid, rotation=rot)
    body = bpy.context.active_object
    body.name = name
    body.data.materials.append(wax)
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r * 1.06, depth=body_len * 0.72,
                                        location=mid + d * body_len * 0.12, rotation=rot)
    w = bpy.context.active_object
    w.data.materials.append(wrap)
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r * 1.075, depth=body_len * 0.22,
                                        location=mid + d * body_len * 0.12, rotation=rot)
    lb = bpy.context.active_object
    lb.data.materials.append(M_WRAP_LABEL)
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=r, radius2=r * 0.25, depth=tip_len,
                                    location=Vector(start) + d * tip_len / 2,
                                    rotation=(-d).to_track_quat("Z", "Y").to_euler())
    tip = bpy.context.active_object
    tip.data.materials.append(wax)
    bpy.ops.object.shade_smooth()
    parts = [body, w, lb, tip]
    if parent is not None:
        for p in parts:
            mw = p.matrix_world.copy()
            p.parent = parent
            p.matrix_parent_inverse = parent.matrix_world.inverted()
    return parts


# the blue crayon, still in his paws, its tip toward the end of the line
CRAYON_TIP_LOCAL = Vector((-0.34, -0.60, 0.045))
crayon_dir_local = Vector((1.0, 0.18, 0.0))
c_start = ham.matrix_world @ CRAYON_TIP_LOCAL
c_dir = ham.matrix_world.to_3x3() @ crayon_dir_local
crayon("Crayon", c_start, c_dir, 0.62, M_WAX_BLUE, M_WRAP_BLUE)
tip_world = Vector((c_start.x, c_start.y, 0.0015))

# other crayons on the desk
crayon("RedCrayon", on_paper(2.15, -1.6, 0.045), (0.3, 1.0, 0), 0.62, M_WAX_RED,
       new_material("WrapRed", (0.45, 0.03, 0.03), rough=0.7))
crayon("GreenCrayon", on_paper(2.0, -2.35, 0.045), (1.0, 0.25, 0), 0.62, M_WAX_GREEN,
       new_material("WrapGreen", (0.03, 0.25, 0.06), rough=0.7))

# fur
add_fur(ham, M_FUR, length=0.055, count=60000, children=8, keep_out=keep, seed=3)

# --- the sleepy line: from the end of "gre" down to the crayon tip, wandering and slowing
w3 = text_width(L3)
start = on_paper(LEFT + w3 + 0.04, rule_y(1) + 0.16)
pts = []
N = 60
for i in range(N + 1):
    t = i / N
    base = start.lerp(tip_world, t)
    # a slow sideways wobble that settles, plus one loop where the paw slipped
    perp = Vector((-(tip_world - start).y, (tip_world - start).x, 0)).normalized()
    wob = 0.16 * math.sin(t * math.pi * 3.2) * (1 - t) ** 0.8
    p = base + perp * wob
    p.z = 0.0015
    pts.append(tuple(p))
scribble = curve_object("Scribble", pts, 0.016, M_BLUE)
scribble.scale = (1, 1, 0.12)

# --- the sticky note, in another hand
NOTE_LOC = on_paper(-1.02, -1.3, 0.002)
bpy.ops.mesh.primitive_plane_add(size=1.55, location=NOTE_LOC, rotation=(0, 0, math.radians(6)))
note = bpy.context.active_object
note.data.materials.append(M_STICKY)
nr = math.radians(6)
nc, ns = math.cos(nr), math.sin(nr)


def on_note(x, y, z=0.0035):
    return Vector((NOTE_LOC.x + nc * x - ns * y, NOTE_LOC.y + ns * x + nc * y, z))


note_text = text_object("NoteText", "he means great.\nhe worked on it\nall day. please\ndon't wake him.",
                        "segoepr.ttf", 0.205, on_note(-0.68, 0.48), M_PENCIL, nr, spacing=1.05)
note_text.data.offset = 0.005  # a soft felt-tip, bold enough to read small

# --- camera: from the front, looking down the desk
target = on_paper(0.05, -0.62, 0.0)
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 50
cam_data.dof.use_dof = True
cam_data.dof.aperture_fstop = 2.0
cam = link(bpy.data.objects.new("Cam", cam_data))
tilt = CAM_TILT
dist = 5.7
cam.location = target + Vector((0.0, -dist * math.sin(tilt), dist * math.cos(tilt)))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
focus = link(bpy.data.objects.new("Focus", None))
focus.location = HAM_LOC + Vector((0, 0, 0.2))
cam_data.dof.focus_object = focus
scene.camera = cam

# --- light: a warm desk lamp from the upper left, a soft cool fill, a dim warm room
lamp = bpy.data.lights.new("Lamp", "AREA")
lamp.energy = 900
lamp.size = 1.6
lamp.color = (1.0, 0.82, 0.6)
lo = link(bpy.data.objects.new("Lamp", lamp))
lo.location = (-3.2, 1.8, 4.2)
lo.rotation_euler = (lo.location - target).to_track_quat("Z", "Y").to_euler()
fill = bpy.data.lights.new("Fill", "AREA")
fill.energy = 220
fill.size = 5.0
fill.color = (0.85, 0.9, 1.0)
fo = link(bpy.data.objects.new("Fill", fill))
fo.location = (3.5, -4.0, 5.0)
fo.rotation_euler = (fo.location - target).to_track_quat("Z", "Y").to_euler()
world = bpy.data.worlds.new("World")
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.35, 0.25, 0.18, 1)
bg.inputs["Strength"].default_value = 0.35
scene.world = world

# --- render
scene.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = "GPU"
except Exception as exc:  # no GPU: render on the CPU
    print("GPU unavailable:", exc)
scene.cycles.samples = ARGS.samples
scene.cycles.use_denoising = True
scene.render.resolution_x = ARGS.res
scene.render.resolution_y = ARGS.res
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "AgX"
for look in ("AgX - Medium High Contrast", "AgX - Base Contrast"):
    try:
        scene.view_settings.look = look
        break
    except TypeError:
        pass
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.compression = 100
scene.render.filepath = os.path.abspath(ARGS.out)
bpy.ops.render.render(write_still=True)
print("wrote", scene.render.filepath)
