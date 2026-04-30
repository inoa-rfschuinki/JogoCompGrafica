"""
scene.py — Construção do cenário 3D.

Conceitos de CG demonstrados:
  - Geometria procedural (plano, colunas, paredes)
  - Malha de grade para o chão (GridMesh)
  - Coordenadas UV e mapeamento de textura procedural
  - Organização hierárquica do grafo de cena
  - Material Phong por objeto
"""

import math
import random
from panda3d.core import (
    GeomVertexFormat, GeomVertexData, GeomVertexWriter,
    Geom, GeomTriangles, GeomNode,
    NodePath, Vec4, Vec3, Material,
    AmbientLight,
    CollisionNode, CollisionBox, CollisionCapsule, Point3, BitMask32,
    Texture,
)


# ──────────────────────────────────────────────────────────────────────────────
# Primitivas procedurais
# ──────────────────────────────────────────────────────────────────────────────

def _make_plane(width: float, depth: float, divs: int = 1) -> Geom:
    """Plano XY centrado na origem, subdividido em divs×divs quads."""
    fmt   = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData("plane", fmt, Geom.UHStatic)

    n = divs + 1
    vdata.setNumRows(n * n)
    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")

    hw, hd = width / 2, depth / 2
    for row in range(n):
        for col in range(n):
            x = -hw + width * col / divs
            y = -hd + depth * row / divs
            vertex.addData3(x, y, 0)
            normal.addData3(0, 0, 1)

    tris = GeomTriangles(Geom.UHStatic)
    for row in range(divs):
        for col in range(divs):
            a = row * n + col
            b = a + 1
            c = a + n
            d = c + 1
            tris.addVertices(a, c, b)
            tris.addVertices(b, c, d)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


def _make_textured_plane(width: float, depth: float, divs: int = 1, uv_repeat: float = 1.0) -> Geom:
    """Plano XY centrado na origem com coordenadas UV repetidas."""
    fmt = GeomVertexFormat.getV3n3t2()
    vdata = GeomVertexData("textured_plane", fmt, Geom.UHStatic)

    n = divs + 1
    vdata.setNumRows(n * n)
    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    texcoord = GeomVertexWriter(vdata, "texcoord")

    hw, hd = width / 2, depth / 2
    for row in range(n):
        v = row / divs
        for col in range(n):
            u = col / divs
            x = -hw + width * u
            y = -hd + depth * v
            vertex.addData3(x, y, 0)
            normal.addData3(0, 0, 1)
            texcoord.addData2(u * uv_repeat, v * uv_repeat)

    tris = GeomTriangles(Geom.UHStatic)
    for row in range(divs):
        for col in range(divs):
            a = row * n + col
            b = a + 1
            c = a + n
            d = c + 1
            tris.addVertices(a, b, c)
            tris.addVertices(b, d, c)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


def _configure_repeating_texture(tex: Texture) -> Texture:
    tex.setWrapU(Texture.WMRepeat)
    tex.setWrapV(Texture.WMRepeat)
    tex.setMinfilter(Texture.FTLinearMipmapLinear)
    tex.setMagfilter(Texture.FTLinear)
    return tex


def _make_stone_texture(seed: int = 42) -> Texture:
    """Textura de pedra procedural: escala de cinza com veias e grão."""
    size = 128
    rng = random.Random(seed)
    data = bytearray()
    for y in range(size):
        for x in range(size):
            base = rng.randint(112, 158)
            vein = int(abs(math.sin(x * 0.31 + y * 0.17) *
                           math.cos(x * 0.11 - y * 0.27)) * 40)
            grain = rng.randint(-22, 22)
            lf = int(math.sin(x * 0.055) * math.cos(y * 0.07) * 22)
            v = max(70, min(212, base - vein + grain + lf))
            data.extend((v, int(v * 0.96), int(v * 0.92), 255))
    tex = Texture("proc_stone")
    tex.setup2dTexture(size, size, Texture.TUnsignedByte, Texture.FRgba8)
    tex.setRamImage(bytes(data))
    tex.setWrapU(Texture.WMRepeat)
    tex.setWrapV(Texture.WMRepeat)
    tex.setMinfilter(Texture.FTLinearMipmapLinear)
    tex.setMagfilter(Texture.FTLinear)
    return tex


def _make_grass_texture() -> Texture:
    """Textura grass_tile em memoria; evita depender de arquivos externos."""
    size = 128
    rng = random.Random(11)
    colors = [
        (26, 82, 20),
        (45, 128, 30),
        (66, 162, 42),
        (82, 190, 48),
        (18, 60, 16),
    ]
    data = bytearray()

    for y in range(size):
        for x in range(size):
            color_index = ((x // 5) + (y // 9) + rng.randrange(len(colors))) % len(colors)
            r, g, b = colors[color_index]
            blade = int((math.sin(x * 0.75 + y * 0.2) + math.sin(x * 0.12 - y * 0.48)) * 14)
            stripe = 38 if (x + y * 2) % 19 == 0 or (x * 3 - y) % 31 == 0 else 0
            noise = rng.randint(-18, 18)

            data.extend((
                max(0, min(255, r + noise // 3 + stripe // 5)),
                max(0, min(255, g + noise + blade + stripe)),
                max(0, min(255, b + noise // 4)),
                255,
            ))

    tex = Texture("procedural_grass_tile")
    tex.setup2dTexture(size, size, Texture.TUnsignedByte, Texture.FRgba8)
    tex.setRamImage(bytes(data))
    return _configure_repeating_texture(tex)


def _make_grass_tuft(blades: int = 5) -> Geom:
    """Pequeno tufo de grama feito com triangulos verticais simples."""
    fmt = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData("grass_tuft", fmt, Geom.UHStatic)
    vdata.setNumRows(blades * 3)
    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    tris = GeomTriangles(Geom.UHStatic)

    rng = random.Random(blades * 37)
    for i in range(blades):
        angle = (math.tau * i / blades) + rng.uniform(-0.18, 0.18)
        width = rng.uniform(0.10, 0.18)
        height = rng.uniform(0.55, 0.95)
        lean = rng.uniform(0.08, 0.18)

        dx = math.cos(angle)
        dy = math.sin(angle)
        sx = -dy * width
        sy = dx * width

        base_x = dx * rng.uniform(0.03, 0.12)
        base_y = dy * rng.uniform(0.03, 0.12)
        tip_x = base_x + dx * lean
        tip_y = base_y + dy * lean

        start = i * 3
        vertex.addData3(base_x - sx, base_y - sy, 0.02)
        vertex.addData3(base_x + sx, base_y + sy, 0.02)
        vertex.addData3(tip_x, tip_y, height)

        for _ in range(3):
            normal.addData3(-dx, -dy, 0.25)

        tris.addVertices(start, start + 1, start + 2)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


def _make_box(w: float, d: float, h: float) -> Geom:
    """Caixa com normais por face (6 faces × 2 triângulos)."""
    hw, hd, hh = w / 2, d / 2, h / 2
    fmt   = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData("box", fmt, Geom.UHStatic)
    vdata.setNumRows(24)
    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")

    faces = [
        ([(-hw,-hd, hh),(hw,-hd, hh),(hw, hd, hh),(-hw, hd, hh)], ( 0, 0, 1)),
        ([(-hw,-hd,-hh),(-hw, hd,-hh),(hw, hd,-hh),(hw,-hd,-hh)], ( 0, 0,-1)),
        ([(-hw,-hd,-hh),(-hw,-hd, hh),(-hw, hd, hh),(-hw, hd,-hh)], (-1, 0, 0)),
        ([(hw,-hd,-hh),(hw, hd,-hh),(hw, hd, hh),(hw,-hd, hh)],  ( 1, 0, 0)),
        ([(-hw, hd,-hh),(-hw, hd, hh),(hw, hd, hh),(hw, hd,-hh)], ( 0, 1, 0)),
        ([(-hw,-hd,-hh),(hw,-hd,-hh),(hw,-hd, hh),(-hw,-hd, hh)], ( 0,-1, 0)),
    ]
    for verts, n in faces:
        for v in verts:
            vertex.addData3(*v)
            normal.addData3(*n)

    tris = GeomTriangles(Geom.UHStatic)
    for f in range(6):
        b = f * 4
        tris.addVertices(b, b+1, b+2)
        tris.addVertices(b, b+2, b+3)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


def _make_rock(w: float, d: float, h: float, seed: int = 0) -> Geom:
    """
    Rocha procedural: elipsoide deformada com normais flat (facetada).
    Cada vértice recebe um fator de perturbação aleatório que distorce
    a superfície de maneira orgânica, e as normais são calculadas por
    triângulo (flat shading) para dar aparência angulosa de pedra.
    """
    rng = random.Random(seed)
    slices, stacks = 9, 7
    hw, hd, hh = w / 2, d / 2, h / 2

    # Perturbação radial independente por nó da grade
    perturb = [[rng.uniform(0.68, 1.25) for _ in range(slices)]
               for _ in range(stacks + 1)]
    pole_n = rng.uniform(0.82, 1.08)
    pole_s = rng.uniform(0.82, 1.08)

    def get_pt(st, sl):
        sl_w  = sl % slices
        phi   = math.pi * st / stacks
        theta = 2 * math.pi * sl_w / slices
        n = pole_n if st == 0 else (pole_s if st == stacks else perturb[st][sl_w])
        x = hw * math.sin(phi) * math.cos(theta) * n
        y = hd * math.sin(phi) * math.sin(theta) * n
        z = hh * math.cos(phi) * n
        return (x, y, z, sl_w / slices, st / stacks)

    tri_list = []
    for sl in range(slices):  # cap norte
        tri_list.append((get_pt(0, 0), get_pt(1, sl), get_pt(1, sl + 1)))
    for st in range(1, stacks - 1):
        for sl in range(slices):
            p00, p10 = get_pt(st, sl), get_pt(st + 1, sl)
            p01, p11 = get_pt(st, sl + 1), get_pt(st + 1, sl + 1)
            tri_list.append((p00, p10, p01))
            tri_list.append((p01, p10, p11))
    for sl in range(slices):  # cap sul
        tri_list.append((get_pt(stacks - 1, sl), get_pt(stacks, 0), get_pt(stacks - 1, sl + 1)))

    fmt   = GeomVertexFormat.getV3n3t2()
    vdata = GeomVertexData("rock", fmt, Geom.UHStatic)
    vdata.setNumRows(len(tri_list) * 3)
    vw = GeomVertexWriter(vdata, "vertex")
    nw = GeomVertexWriter(vdata, "normal")
    tw = GeomVertexWriter(vdata, "texcoord")
    tris = GeomTriangles(Geom.UHStatic)

    for i, (v0, v1, v2) in enumerate(tri_list):
        ax, ay, az = v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2]
        bx, by, bz = v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2]
        nx = ay*bz - az*by
        ny = az*bx - ax*bz
        nz = ax*by - ay*bx
        ln = math.sqrt(nx*nx + ny*ny + nz*nz)
        if ln > 1e-9:
            nx /= ln; ny /= ln; nz /= ln
        for (vx, vy, vz, vu, vv) in (v0, v1, v2):
            vw.addData3(vx, vy, vz)
            nw.addData3(nx, ny, nz)
            tw.addData2(vu, vv)
        b = i * 3
        tris.addVertices(b, b + 1, b + 2)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


def _attach_geom(parent: NodePath, geom: Geom, name: str) -> NodePath:
    node = GeomNode(name)
    node.addGeom(geom)
    return parent.attachNewNode(node)


def _make_sphere(radius: float, slices: int = 18, stacks: int = 12) -> Geom:
    """
    Esfera lisa (smooth shading) com normais por vértice.
    Útil para juntas anatômicas e cabeça do personagem.
    Pode ser escalada de forma não-uniforme para gerar elipsoides.
    """
    fmt   = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData("sphere", fmt, Geom.UHStatic)
    n_rows = (stacks + 1) * (slices + 1)
    vdata.setNumRows(n_rows)
    vw = GeomVertexWriter(vdata, "vertex")
    nw = GeomVertexWriter(vdata, "normal")

    for st in range(stacks + 1):
        phi  = math.pi * st / stacks
        sphi = math.sin(phi)
        cphi = math.cos(phi)
        for sl in range(slices + 1):
            theta = 2 * math.pi * sl / slices
            x = sphi * math.cos(theta)
            y = sphi * math.sin(theta)
            z = cphi
            vw.addData3(radius * x, radius * y, radius * z)
            nw.addData3(x, y, z)

    tris = GeomTriangles(Geom.UHStatic)
    row = slices + 1
    for st in range(stacks):
        for sl in range(slices):
            a = st * row + sl
            b = a + 1
            c = a + row
            d = c + 1
            tris.addVertices(a, c, b)
            tris.addVertices(b, c, d)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


def _make_mountain_peak(base_radius: float,
                        height: float,
                        seed: int = 0,
                        slices: int = 18,
                        stacks: int = 8,
                        snow_line: float = 0.62) -> Geom:
    """
    Pico de montanha procedural — cone deformado por ruído radial e
    cristas verticais, com normais flat (faceta rochosa) e cores por
    vértice fazendo gradiente rocha → neve no topo.
    """
    rng = random.Random(seed)

    # Ruído radial por (stack, slice) para silhueta orgânica.
    noise = [[rng.uniform(0.78, 1.22) for _ in range(slices + 1)]
             for _ in range(stacks + 1)]

    # Cristas dominantes — cosseno de N lóbulos com fase aleatória.
    ridge_count = rng.randint(4, 7)
    ridge_phase = rng.uniform(0, math.tau)
    for st in range(stacks + 1):
        z_ratio = st / stacks
        ridge_amp = 0.28 * (1 - z_ratio)
        for sl in range(slices + 1):
            ang = 2 * math.pi * sl / slices
            ridge = math.cos(ridge_count * ang + ridge_phase)
            noise[st][sl] *= (1.0 + ridge_amp * ridge)

    # Apex unificado — perfeitamente cônico no topo.
    for sl in range(slices + 1):
        noise[stacks][sl] = 0.0

    # Coleta dos vértices da grade (st, sl).
    pts = [[None] * (slices + 1) for _ in range(stacks + 1)]
    for st in range(stacks + 1):
        z_ratio = st / stacks
        prof = (1 - z_ratio) ** 1.35  # cone côncavo
        z_base = height * z_ratio
        for sl in range(slices + 1):
            ang = 2 * math.pi * sl / slices
            r   = base_radius * prof * noise[st][sl]
            zj  = rng.uniform(-0.05, 0.05) * height * (1 - z_ratio)
            pts[st][sl] = (r * math.cos(ang), r * math.sin(ang), z_base + zj)

    # Triangulação flat-shaded.
    tri_list = []
    for st in range(stacks):
        for sl in range(slices):
            a = pts[st][sl]
            b = pts[st][sl + 1]
            c = pts[st + 1][sl]
            d = pts[st + 1][sl + 1]
            tri_list.append((a, c, b))
            tri_list.append((b, c, d))

    rng2 = random.Random(seed * 3 + 1)
    rock_dark  = (0.30, 0.27, 0.24)
    rock_light = (0.56, 0.51, 0.46)
    snow       = (0.97, 0.97, 1.00)

    def color_for(z):
        h = max(0.0, min(1.0, z / height))
        if h < snow_line:
            t = h / snow_line
            r = rock_dark[0] * (1 - t) + rock_light[0] * t
            g = rock_dark[1] * (1 - t) + rock_light[1] * t
            b = rock_dark[2] * (1 - t) + rock_light[2] * t
        else:
            t = min(1.0, (h - snow_line) / max(1e-6, 1 - snow_line) * 1.4)
            r = rock_light[0] * (1 - t) + snow[0] * t
            g = rock_light[1] * (1 - t) + snow[1] * t
            b = rock_light[2] * (1 - t) + snow[2] * t
        v = rng2.uniform(-0.04, 0.04)
        return (max(0, min(1, r + v)),
                max(0, min(1, g + v)),
                max(0, min(1, b + v)),
                1.0)

    fmt   = GeomVertexFormat.getV3n3c4()
    vdata = GeomVertexData("mountain_peak", fmt, Geom.UHStatic)
    vdata.setNumRows(len(tri_list) * 3)
    vw = GeomVertexWriter(vdata, "vertex")
    nw = GeomVertexWriter(vdata, "normal")
    cw = GeomVertexWriter(vdata, "color")
    tris = GeomTriangles(Geom.UHStatic)

    for i, (v0, v1, v2) in enumerate(tri_list):
        ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
        bx, by, bz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
        nx = ay * bz - az * by
        ny = az * bx - ax * bz
        nz = ax * by - ay * bx
        ln = math.sqrt(nx * nx + ny * ny + nz * nz)
        if ln > 1e-9:
            nx /= ln; ny /= ln; nz /= ln
        for v in (v0, v1, v2):
            vw.addData3(*v)
            nw.addData3(nx, ny, nz)
            r, g, b, a = color_for(v[2])
            cw.addData4(r, g, b, a)
        b = i * 3
        tris.addVertices(b, b + 1, b + 2)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


def _make_cylinder(radius: float, height: float, slices: int = 12) -> Geom:
    """Cilindro vertical procedural com tampas, normais corretas."""
    fmt   = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData("cylinder", fmt, Geom.UHStatic)
    # lateral: slices*2 verts × 2 rings; tampas: slices+1 × 2
    vdata.setNumRows(slices * 2 + (slices + 1) * 2)
    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    tris   = GeomTriangles(Geom.UHStatic)

    hh = height / 2

    # Lateral
    for ring, z in enumerate([-hh, hh]):
        for i in range(slices):
            angle = 2 * math.pi * i / slices
            nx = math.cos(angle)
            ny = math.sin(angle)
            vertex.addData3(radius * nx, radius * ny, z)
            normal.addData3(nx, ny, 0)

    base_lat = 0
    for i in range(slices):
        a = base_lat + i
        b = base_lat + (i + 1) % slices
        c = a + slices
        d = b + slices
        tris.addVertices(a, c, b)
        tris.addVertices(b, c, d)

    # Tampa inferior
    base_bot = slices * 2
    center_bot = base_bot + slices
    for i in range(slices):
        angle = 2 * math.pi * i / slices
        vertex.addData3(radius * math.cos(angle), radius * math.sin(angle), -hh)
        normal.addData3(0, 0, -1)
    vertex.addData3(0, 0, -hh)
    normal.addData3(0, 0, -1)
    for i in range(slices):
        tris.addVertices(center_bot, base_bot + (i + 1) % slices, base_bot + i)

    # Tampa superior
    base_top = base_bot + slices + 1
    center_top = base_top + slices
    for i in range(slices):
        angle = 2 * math.pi * i / slices
        vertex.addData3(radius * math.cos(angle), radius * math.sin(angle), hh)
        normal.addData3(0, 0, 1)
    vertex.addData3(0, 0, hh)
    normal.addData3(0, 0, 1)
    for i in range(slices):
        tris.addVertices(center_top, base_top + i, base_top + (i + 1) % slices)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


def _make_cone(radius: float, height: float, slices: int = 12) -> Geom:
    """Cone procedural — usado para copa cônica das árvores."""
    fmt   = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData("cone", fmt, Geom.UHStatic)
    vdata.setNumRows(slices + 1 + slices + 1)
    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    tris   = GeomTriangles(Geom.UHStatic)

    slope  = radius / height
    # Lateral
    for i in range(slices):
        angle = 2 * math.pi * i / slices
        nx = math.cos(angle)
        ny = math.sin(angle)
        nz = slope / math.sqrt(1 + slope * slope)
        nl = math.sqrt(nx * nx + ny * ny)
        vertex.addData3(radius * nx, radius * ny, 0)
        normal.addData3(nx * (1 - nz), ny * (1 - nz), nz)
    apex_idx = slices
    vertex.addData3(0, 0, height)
    normal.addData3(0, 0, 1)

    for i in range(slices):
        tris.addVertices(i, apex_idx, (i + 1) % slices)

    # Base
    base_start = slices + 1
    for i in range(slices):
        angle = 2 * math.pi * i / slices
        vertex.addData3(radius * math.cos(angle), radius * math.sin(angle), 0)
        normal.addData3(0, 0, -1)
    center_base = base_start + slices
    vertex.addData3(0, 0, 0)
    normal.addData3(0, 0, -1)
    for i in range(slices):
        tris.addVertices(center_base, base_start + (i + 1) % slices, base_start + i)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


def _set_material(np: NodePath,
                  diffuse: Vec4,
                  ambient_factor: float = 0.3,
                  specular: Vec4 = None,
                  shininess: float = 20.0):
    mat = Material()
    mat.setDiffuse(diffuse)
    mat.setAmbient(Vec4(
        diffuse[0] * ambient_factor,
        diffuse[1] * ambient_factor,
        diffuse[2] * ambient_factor,
        1
    ))
    mat.setSpecular(specular if specular else Vec4(0.3, 0.3, 0.3, 1))
    mat.setShininess(shininess)
    np.setMaterial(mat, 1)


# ──────────────────────────────────────────────────────────────────────────────
# Cena
# ──────────────────────────────────────────────────────────────────────────────

class Scene:
    """
    Constrói o cenário: chão, paredes limite, árvores e plataformas decorativas.
    """

    MAP_SIZE  = 100   # lado do chão (centrado na origem)
    WALL_H    = 12    # altura das paredes de limite
    GRASS_UV_REPEAT = 64
    GRASS_TUFT_COUNT  = 600
    GRASS_BLADE_COUNT = 2200   # gramíneas pequenas espalhadas (folhas curtas)
    PEBBLE_COUNT = 70
    FLOWER_COUNT = 110
    TREE_COLLIDE_MASK        = BitMask32.bit(1)
    COLLECTIBLE_COLLIDE_MASK = BitMask32.bit(2)
    OBSTACLE_COLLIDE_MASK    = BitMask32.bit(3)

    def __init__(self, render: NodePath, loader):
        self.render = render
        self.loader = loader
        self.root   = render.attachNewNode("scene_root")
        random.seed(42)   # cena determinista

        self._build_ground()
        self._build_grass_tufts()
        self._build_grass_blades()
        self._build_flowers()
        self._build_pebbles()
        self._build_boundary_walls()
        self._build_decorations()
        self._build_rocks()
        self._build_sky()

    GROUND_DEPTH = 20   # espessura da laje (para não ver o céu abaixo)

    # ── Chão ─────────────────────────────────────────────────────
    def _build_ground(self):
        """
        Laje sólida: caixa espessa para que o FOV da câmera nunca
        mostre o vazio abaixo do terreno. Segundo plano mais escuro
        dá sensação de profundidade de solo.
        """
        d = self.GROUND_DEPTH
        # Estende o piso ALÉM do MAP_SIZE para que ele continue por
        # baixo da fileira interna de montanhas (que entra ~2m no mapa).
        # Sem isso, vê-se o "vão" entre a borda da grama e a base dos
        # picos.
        GROUND_OVER = 18
        ground_size = self.MAP_SIZE + GROUND_OVER * 2

        # Camada principal — grama clara
        ground_geom = _make_box(ground_size, ground_size, d)
        ground_np   = _attach_geom(self.root, ground_geom, "ground")
        ground_np.setPos(0, 0, -d / 2)
        _set_material(
            ground_np,
            diffuse=Vec4(0.25, 0.52, 0.20, 1),
            ambient_factor=0.45,
            specular=Vec4(0.04, 0.06, 0.04, 1),
            shininess=4
        )

        grass_geom = _make_textured_plane(
            ground_size,
            ground_size,
            divs=48,
            uv_repeat=self.GRASS_UV_REPEAT * (ground_size / self.MAP_SIZE)
        )
        grass_np = _attach_geom(self.root, grass_geom, "grass_surface")
        grass_np.setPos(0, 0, 0.02)
        grass_np.setTwoSided(True)
        grass_np.setTexture(_make_grass_texture(), 1)
        _set_material(
            grass_np,
            diffuse=Vec4(1.0, 1.0, 1.0, 1),
            ambient_factor=0.7,
            specular=Vec4(0.02, 0.04, 0.02, 1),
            shininess=2
        )

        # Camada de sub-solo visível nas bordas (terra escura)
        sub_geom = _make_box(ground_size + 2, ground_size + 2, d * 0.5)
        sub_np   = _attach_geom(self.root, sub_geom, "subsoil")
        sub_np.setPos(0, 0, -d * 0.75 - 0.1)
        _set_material(sub_np, Vec4(0.32, 0.22, 0.12, 1), ambient_factor=0.3, shininess=2)

        # Faixa de caminho de terra no centro (X)
        path_x = _make_box(self.MAP_SIZE, 4.0, 0.05)
        px_np  = _attach_geom(self.root, path_x, "path_x")
        px_np.setPos(0, 0, 0.01)
        _set_material(px_np, Vec4(0.55, 0.42, 0.28, 1), ambient_factor=0.35, shininess=3)

        # Faixa de caminho de terra no centro (Y)
        path_y = _make_box(4.0, self.MAP_SIZE, 0.05)
        py_np  = _attach_geom(self.root, path_y, "path_y")
        py_np.setPos(0, 0, 0.01)
        _set_material(py_np, Vec4(0.55, 0.42, 0.28, 1), ambient_factor=0.35, shininess=3)

    # ── Paredes limite ────────────────────────────────────────────────────
    def _build_grass_tufts(self):
        """Tufos discretos de grama, concentrados fora dos caminhos."""
        rng = random.Random(93)
        half = self.MAP_SIZE / 2 - 5

        for i in range(self.GRASS_TUFT_COUNT):
            for _ in range(80):
                x = rng.uniform(-half, half)
                y = rng.uniform(-half, half)
                on_path = abs(x) < 3.2 or abs(y) < 3.2
                too_close_to_center = abs(x) < 8 and abs(y) < 8
                if not on_path and not too_close_to_center:
                    break

            blades = rng.randint(4, 7)
            tuft_np = _attach_geom(self.root, _make_grass_tuft(blades), f"grass_tuft_{i}")
            tuft_np.setPos(x, y, 0.02)
            tuft_np.setH(rng.uniform(0, 360))
            tuft_np.setScale(rng.uniform(0.6, 2.8))
            tuft_np.setTwoSided(True)
            _set_material(
                tuft_np,
                Vec4(
                    rng.uniform(0.20, 0.34),
                    rng.uniform(0.48, 0.70),
                    rng.uniform(0.10, 0.18),
                    1
                ),
                ambient_factor=0.45,
                specular=Vec4(0.02, 0.04, 0.02, 1),
                shininess=2
            )

    def _build_grass_blades(self):
        """Camada extra de gramíneas baixas espalhadas pelo gramado.
        Cada "gramínea" é um tufinho com 2-3 folhas curtas e finas;
        elas são muito menores que `_build_grass_tufts` e cobrem até os
        caminhos para dar a sensação de gramado vivo. Usam um geom
        compartilhado para não pesar a cena.
        """
        rng = random.Random(7777)
        half = self.MAP_SIZE / 2 - 1

        # Geoms compartilhados — algumas variações para não repetir
        # exatamente o mesmo formato em todas as instâncias.
        blade_geoms = [_make_grass_tuft(blades=rng.randint(2, 3))
                       for _ in range(6)]

        # Nó pai único para reduzir overhead.
        parent = self.root.attachNewNode("micro_grass")

        for i in range(self.GRASS_BLADE_COUNT):
            x = rng.uniform(-half, half)
            y = rng.uniform(-half, half)
            # Não evita os caminhos: queremos cobertura completa.
            geom = blade_geoms[i % len(blade_geoms)]
            np_ = _attach_geom(parent, geom, f"blade_{i}")
            np_.setPos(x, y, 0.01)
            np_.setH(rng.uniform(0, 360))
            # Folhas BEM pequenas (~30% da escala dos tufos).
            np_.setScale(rng.uniform(0.18, 0.45))
            np_.setTwoSided(True)
            _set_material(
                np_,
                Vec4(
                    rng.uniform(0.18, 0.30),
                    rng.uniform(0.46, 0.72),
                    rng.uniform(0.10, 0.20),
                    1,
                ),
                ambient_factor=0.55,
                specular=Vec4(0.02, 0.04, 0.02, 1),
                shininess=2,
            )

    def _build_flowers(self):
        """Pequenas flores procedurais (mini disco colorido + miolo)."""
        rng = random.Random(2027)
        half = self.MAP_SIZE / 2 - 6

        # Paleta de pétalas
        palettes = [
            (Vec4(1.00, 0.92, 0.30, 1), Vec4(0.95, 0.55, 0.10, 1)),  # margarida
            (Vec4(0.95, 0.40, 0.55, 1), Vec4(1.00, 0.85, 0.30, 1)),  # rosa
            (Vec4(0.55, 0.30, 0.85, 1), Vec4(1.00, 0.95, 0.40, 1)),  # violeta
            (Vec4(0.95, 0.95, 0.95, 1), Vec4(1.00, 0.85, 0.20, 1)),  # branca
            (Vec4(1.00, 0.55, 0.20, 1), Vec4(0.95, 0.30, 0.10, 1)),  # laranja
        ]

        for i in range(self.FLOWER_COUNT):
            for _ in range(60):
                x = rng.uniform(-half, half)
                y = rng.uniform(-half, half)
                if abs(x) < 3.2 or abs(y) < 3.2:
                    continue
                if abs(x) < 7 and abs(y) < 7:
                    continue
                break
            else:
                continue

            petal_color, center_color = rng.choice(palettes)
            scale = rng.uniform(0.20, 0.40)
            ang   = rng.uniform(0, 360)

            # 5–7 pétalas (caixinhas finas dispostas em estrela)
            n_petals = rng.randint(5, 7)
            for k in range(n_petals):
                p_ang = (360 / n_petals) * k
                petal_g = _make_box(0.18, 0.40, 0.04)
                pn = _attach_geom(self.root, petal_g, f"petal_{i}_{k}")
                pn.setPos(x, y, 0.04)
                pn.setH(ang + p_ang)
                pn.setScale(scale)
                _set_material(pn, petal_color, ambient_factor=0.6,
                              specular=Vec4(0.05, 0.05, 0.05, 1), shininess=4)

            # Miolo (caixinha central)
            core_g = _make_box(0.18, 0.18, 0.06)
            cn = _attach_geom(self.root, core_g, f"flower_core_{i}")
            cn.setPos(x, y, 0.06)
            cn.setScale(scale)
            _set_material(cn, center_color, ambient_factor=0.6, shininess=8)

            # Caulezinho curto (apenas para os maiores)
            if scale > 0.30:
                stem_g = _make_box(0.04, 0.04, 0.18)
                sn = _attach_geom(self.root, stem_g, f"flower_stem_{i}")
                sn.setPos(x, y, 0.09 * scale)
                sn.setScale(scale)
                _set_material(sn, Vec4(0.18, 0.55, 0.20, 1),
                              ambient_factor=0.4, shininess=4)

    def _build_pebbles(self):
        """Pedrinhas pequenas dispersas pelo terreno (decorativas)."""
        rng = random.Random(2028)
        half = self.MAP_SIZE / 2 - 4

        for i in range(self.PEBBLE_COUNT):
            for _ in range(30):
                x = rng.uniform(-half, half)
                y = rng.uniform(-half, half)
                if abs(x) < 2.5 and abs(y) < 2.5:
                    continue
                break

            # Tamanho minúsculo para se assentar no piso
            w = rng.uniform(0.18, 0.55)
            d = rng.uniform(0.18, 0.55)
            h = rng.uniform(0.10, 0.28)

            geom = _make_rock(w, d, h, seed=i * 53 + 11)
            np = _attach_geom(self.root, geom, f"pebble_{i}")
            np.setPos(x, y, h * 0.45)
            np.setH(rng.uniform(0, 360))

            # Variação de cinza para parecer pedras de verdade
            shade = rng.uniform(0.42, 0.68)
            _set_material(
                np,
                Vec4(shade, shade * 0.95, shade * 0.88, 1),
                ambient_factor=0.35,
                specular=Vec4(0.10, 0.10, 0.10, 1),
                shininess=10,
            )

    def _build_boundary_walls(self):
        """
        Cordilheira procedural ao redor do mapa.
          - Fileira interna: picos baixos/médios próximos da arena (escala
            menor, tons mais escuros — sopés rochosos).
          - Fileira externa: picos altos com calotas de neve, formando o
            horizonte da cadeia montanhosa.

        Os picos têm largura sobreposta para que não haja "vão" entre eles
        e a aparência seja contínua. O bloqueio do jogador continua sendo
        aplicado pelo clamp ±45 em `Player._handle_movement`.
        """
        half = self.MAP_SIZE / 2
        rng  = random.Random(2026)

        # (offset_externo, faixa_altura, faixa_raio_base, snow_line)
        # Offset NEGATIVO = a fileira invade o gramado (sopé entra no
        # mapa). Isso garante continuidade visual sem "vão" entre o piso
        # e a base das montanhas.
        rows = [
            (-2.0,  ( 2.5,  5.0), (2.8, 4.5), 0.99),  # primeiros morros invadindo a grama
            ( 2.0,  ( 5.0,  9.0), (3.6, 5.4), 0.88),  # sopé com pouca neve
            ( 7.0,  ( 9.5, 15.0), (4.6, 7.0), 0.68),  # meio nevado
            (13.5,  (14.0, 23.0), (5.5, 8.8), 0.50),  # cume principal
            (21.0,  (21.0, 31.0), (6.5,10.0), 0.40),  # picos majestosos ao fundo
        ]

        peak_index = 0

        def place_side(axis: str, sign: int):
            """
            axis = 'x' → cordilheira corre ao longo do eixo X (lados N/S).
            axis = 'y' → corre ao longo do eixo Y (lados L/O).
            sign = ±1  → de qual lado do mapa.
            """
            nonlocal peak_index
            # Estende a faixa um pouco além das bordas para cobrir os cantos.
            t_start = -half - 18
            t_end   =  half + 18

            for row_offset, h_range, r_range, snow_line in rows:
                t = t_start
                while t < t_end:
                    base_r = rng.uniform(*r_range)
                    h      = rng.uniform(*h_range)
                    jitter = rng.uniform(-1.6, 1.6)

                    if axis == 'x':
                        x = t + rng.uniform(-1.0, 1.0)
                        y = sign * (half + row_offset + jitter)
                    else:
                        x = sign * (half + row_offset + jitter)
                        y = t + rng.uniform(-1.0, 1.0)

                    geom = _make_mountain_peak(
                        base_r, h,
                        seed=peak_index * 31 + 7,
                        slices=16, stacks=7,
                        snow_line=snow_line,
                    )
                    np = _attach_geom(self.root, geom,
                                      f"mountain_peak_{peak_index}")
                    # Afunda fortemente a base para se fundir com o
                    # terreno (evita o "vão" visível na junção).
                    np.setPos(x, y, -1.6)
                    np.setH(rng.uniform(0, 360))
                    np.setScale(rng.uniform(0.92, 1.10),
                                rng.uniform(0.92, 1.10),
                                rng.uniform(0.95, 1.15))
                    # Vertex colors são moduladas pelo material; usamos
                    # diffuse branco para preservar a paleta procedural.
                    _set_material(np, Vec4(1.0, 1.0, 1.0, 1),
                                  ambient_factor=0.42,
                                  specular=Vec4(0.05, 0.05, 0.07, 1),
                                  shininess=4)

                    # Avança o cursor com sobreposição maior (mais densa).
                    t += base_r * rng.uniform(0.85, 1.10)
                    peak_index += 1

        for sign in (+1, -1):
            place_side('x', sign)
            place_side('y', sign)

    # ── Decorações: árvores simples e plataformas ─────────────────────────
    def _build_decorations(self):
        tree_positions = [
            ( 5, 30), (-5, 30), (30,  5), (30, -5),
            (-30, 8), (-30,-8), (8, -30), (-8,-30),
            (18, 18), (-18, 18), (18,-18), (-18,-18),
            (38, 0), (-38, 0), (0, 38), (0,-38),
            (25, 38), (-25, 38), (38, 25), (-38, 25),
            (25,-38), (-25,-38), (38,-25), (-38,-25),
            # Bosques extras espalhados
            (12, 24), (-12, 24), (24, 12), (24, -12),
            (-24, 12), (-24, -12), (12, -24), (-12, -24),
            (32, 32), (-32, 32), (32, -32), (-32, -32),
            (5, 18), (-5, 18), (18, 5), (-18, 5),
        ]
        rng = random.Random(4242)
        for i, (x, y) in enumerate(tree_positions):
            scale = rng.uniform(0.75, 1.55)
            self._build_tree(x, y, i, scale)

        platform_positions = [
            (12, 0, 0.3), (-12, 0, 0.3),
            (0, 12, 0.3), (0, -12, 0.3),
            (22, 22, 0.3), (-22, 22, 0.3),
            (22,-22, 0.3), (-22,-22, 0.3),
        ]
        for i, (x, y, z) in enumerate(platform_positions):
            self._build_platform(x, y, z, i)

    def _build_tree(self, x: float, y: float, idx: int, scale: float = 1.0):
        """Árvore com tronco levemente cônico e copa de aglomerados de
        esferas (folhagem orgânica), inclinação e variação de cor."""
        rng = random.Random(idx * 311 + 17)

        trunk_h = (3.6 + rng.uniform(-0.4, 0.6)) * scale
        trunk_r = (0.30 + rng.uniform(-0.04, 0.05)) * scale

        # Inclinação aleatória pequena para parecer natural
        tilt_h = rng.uniform(-4, 4)
        tilt_p = rng.uniform(-2, 2)

        # Tronco principal — cilindro com leve sombreamento por seção
        trunk_geom = _make_cylinder(trunk_r, trunk_h, slices=12)
        trunk_np = _attach_geom(self.root, trunk_geom, f"trunk_{idx}")
        trunk_np.setPos(x, y, trunk_h / 2)
        trunk_np.setH(rng.uniform(0, 360))
        trunk_np.setHpr(tilt_h, tilt_p, 0)
        bark_r = 0.36 + rng.uniform(-0.05, 0.06)
        bark_g = 0.23 + rng.uniform(-0.04, 0.04)
        _set_material(trunk_np, Vec4(bark_r, bark_g, 0.10, 1),
                      ambient_factor=0.28,
                      specular=Vec4(0.05, 0.04, 0.02, 1), shininess=4)

        # Anel/raiz na base (disco achatado para esconder a junção do
        # cilindro com o solo).
        base_geom = _make_cylinder(trunk_r * 1.6, 0.18 * scale, slices=12)
        base_np = _attach_geom(self.root, base_geom, f"trunk_base_{idx}")
        base_np.setPos(x, y, 0.09 * scale)
        _set_material(base_np, Vec4(bark_r * 0.85, bark_g * 0.85, 0.08, 1),
                      ambient_factor=0.30, shininess=4)

        # Copa: aglomerado de 7-10 esferas dispostas em formato de coroa
        canopy_center_z = trunk_h + 0.6 * scale
        canopy_radius = 1.6 * scale
        leaf_palette = [
            Vec4(0.10, 0.42, 0.10, 1),
            Vec4(0.14, 0.55, 0.14, 1),
            Vec4(0.18, 0.62, 0.16, 1),
            Vec4(0.22, 0.70, 0.20, 1),
        ]
        n_clusters = rng.randint(8, 12)
        for c in range(n_clusters):
            ang = rng.uniform(0, 2 * math.pi)
            rad = rng.uniform(0.0, canopy_radius)
            zoff = rng.uniform(-0.6, 1.4) * scale
            cx_off = math.cos(ang) * rad
            cy_off = math.sin(ang) * rad
            r = rng.uniform(0.85, 1.40) * scale
            geom = _make_sphere(r, slices=12, stacks=8)
            np_ = _attach_geom(self.root, geom, f"canopy_{idx}_{c}")
            np_.setPos(x + cx_off, y + cy_off, canopy_center_z + zoff)
            color = leaf_palette[rng.randint(0, len(leaf_palette) - 1)]
            _set_material(np_, color,
                          ambient_factor=0.32,
                          specular=Vec4(0.08, 0.16, 0.08, 1), shininess=10)

        # Esfera central maior para preencher o miolo da copa
        core_geom = _make_sphere(canopy_radius * 1.05,
                                 slices=14, stacks=10)
        core_np = _attach_geom(self.root, core_geom, f"canopy_core_{idx}")
        core_np.setPos(x, y, canopy_center_z + 0.3 * scale)
        _set_material(core_np, leaf_palette[1],
                      ambient_factor=0.35,
                      specular=Vec4(0.05, 0.10, 0.05, 1), shininess=8)

        # Colisor da árvore — somente o TRONCO (cápsula vertical fina).
        # A copa não bloqueia o jogador, permitindo passar por baixo dela
        # sem encostar em uma "parede" invisível.
        col = CollisionNode(f"tree_col_{idx}")
        # CollisionCapsule(ax,ay,az, bx,by,bz, radius) — segmento vertical
        # do z=0 até o topo do tronco, com raio = trunk_r * 1.15 (folga
        # mínima para o tronco não atravessar visualmente o jogador).
        col.addSolid(CollisionCapsule(
            0, 0, 0.1,
            0, 0, trunk_h,
            trunk_r * 1.15,
        ))
        col.setFromCollideMask(BitMask32.allOff())
        col.setIntoCollideMask(self.TREE_COLLIDE_MASK)
        col_np = self.root.attachNewNode(col)
        col_np.setPos(x, y, 0)

    def _build_platform(self, x: float, y: float, z: float, idx: int):
        """Plataforma elevada com degrau e base."""
        # Base larga
        base_g  = _make_box(4.2, 4.2, 0.25)
        base_np = _attach_geom(self.root, base_g, f"plat_base_{idx}")
        base_np.setPos(x, y, z - 0.12)
        _set_material(base_np, Vec4(0.42, 0.36, 0.26, 1), ambient_factor=0.3,
                      specular=Vec4(0.08, 0.07, 0.05, 1), shininess=10)

        # Topo levemente diferente (pedra polida)
        top_g  = _make_box(3.0, 3.0, 0.18)
        top_np = _attach_geom(self.root, top_g, f"plat_top_{idx}")
        top_np.setPos(x, y, z + 0.05)
        _set_material(top_np, Vec4(0.68, 0.58, 0.45, 1), ambient_factor=0.35,
                      specular=Vec4(0.25, 0.20, 0.15, 1), shininess=30)

    def _build_rocks(self):
        """Rochas e pedras espalhadas para variar o terreno."""
        rng = random.Random(7)
        rock_configs = [
            # (x,    y,    w,   d,   h)
            ( 6, -18,  1.8, 1.4, 0.9),   # média
            (-8,  22,  0.9, 0.7, 0.45),  # pequena
            (27,  12,  1.6, 1.3, 0.85),  # média-pequena
            (-24,-20,  1.9, 1.5, 1.0),   # média
            (15, -10,  0.8, 0.7, 0.45),  # pequena
            (-16, 14,  1.5, 1.2, 0.8),   # média-pequena
            (35, -10,  1.7, 1.4, 0.9),   # média
            (-35,  5,  1.3, 1.0, 0.65),  # média-pequena
            ( 10, 40,  2.0, 1.6, 1.0),   # média
            (-12,-40,  1.8, 1.4, 0.9),   # média
            ( 20, -35, 0.7, 0.6, 0.4),   # pequena
            (-28,  30, 1.4, 1.1, 0.7),   # média-pequena
            ( 40,  20, 1.6, 1.2, 0.8),   # média-pequena
            (-18,  -8, 0.8, 0.7, 0.5),   # pequena
        ]
        stone_tex = _make_stone_texture()
        for i, (rx, ry, rw, rd, rh) in enumerate(rock_configs):
            g  = _make_rock(rw, rd, rh, seed=i * 17 + 3)
            np = _attach_geom(self.root, g, f"rock_{i}")
            np.setPos(rx, ry, rh / 2)
            np.setH(rng.uniform(0, 360))
            np.setTexture(stone_tex, 1)
            _set_material(np, Vec4(1.0, 1.0, 1.0, 1),
                          ambient_factor=0.32,
                          specular=Vec4(0.22, 0.22, 0.20, 1), shininess=22)

    # ── Céu (caixa invertida enorme) ──────────────────────────────────────
    def _build_sky(self):
        """
        Skybox em duas camadas:
          1. Cúpula alta — azul profundo (horizonte de cima)
          2. Faixa de horizonte — azul-névoa claro (simula gradiente)
        """
        size = 500
        geom = _make_box(size, size, size)
        sky_np = _attach_geom(self.root, geom, "skybox")
        sky_np.setPos(0, 0, size / 2 - 55)
        sky_np.setTwoSided(True)
        sky_np.setLightOff()
        sky_np.setColor(0.38, 0.62, 0.92, 1)   # azul céu profundo
        sky_np.setBin("background", 0)
        sky_np.setDepthWrite(False)

        # Faixa de horizonte (caixa mais larga e achatada, cor névoa)
        hor_size = size * 1.05
        hor_geom = _make_box(hor_size, hor_size, size * 0.22)
        hor_np   = _attach_geom(self.root, hor_geom, "sky_horizon")
        hor_np.setPos(0, 0, -size * 0.05)
        hor_np.setTwoSided(True)
        hor_np.setLightOff()
        hor_np.setColor(0.72, 0.86, 0.97, 1)   # azul-névoa claro no horizonte
        hor_np.setBin("background", 1)
        hor_np.setDepthWrite(False)

        # Sol — disco brilhante no horizonte
        sun_geom = _make_box(14, 14, 14)
        sun_np   = _attach_geom(self.root, sun_geom, "sun_disc")
        sun_np.setPos(-60, -120, 55)
        sun_np.setLightOff()
        sun_np.setColor(1.0, 0.97, 0.80, 1)
        sun_np.setBin("background", 2)
        sun_np.setDepthWrite(False)
        sun_np.setTwoSided(True)

        # Halo do sol (maior, mais transparente via cor)
        halo_geom = _make_box(32, 32, 32)
        halo_np   = _attach_geom(self.root, halo_geom, "sun_halo")
        halo_np.setPos(-60, -120, 55)
        halo_np.setLightOff()
        halo_np.setColor(1.0, 0.93, 0.70, 1)
        halo_np.setBin("background", 1)
        halo_np.setDepthWrite(False)
        halo_np.setTwoSided(True)

    def destroy(self):
        """Remove toda a cena do grafo de cena."""
        self.root.removeNode()
