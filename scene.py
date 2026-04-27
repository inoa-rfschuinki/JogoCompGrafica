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
    CollisionNode, CollisionBox, Point3, BitMask32,
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


def _attach_geom(parent: NodePath, geom: Geom, name: str) -> NodePath:
    node = GeomNode(name)
    node.addGeom(geom)
    return parent.attachNewNode(node)


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
    TREE_COLLIDE_MASK = BitMask32.bit(1)
    COLLECTIBLE_COLLIDE_MASK = BitMask32.bit(2)

    def __init__(self, render: NodePath, loader):
        self.render = render
        self.loader = loader
        self.root   = render.attachNewNode("scene_root")
        random.seed(42)   # cena determinista

        self._build_ground()
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
        # Camada principal — grama clara
        ground_geom = _make_box(self.MAP_SIZE, self.MAP_SIZE, d)
        ground_np   = _attach_geom(self.root, ground_geom, "ground")
        ground_np.setPos(0, 0, -d / 2)
        _set_material(
            ground_np,
            diffuse=Vec4(0.25, 0.52, 0.20, 1),
            ambient_factor=0.45,
            specular=Vec4(0.04, 0.06, 0.04, 1),
            shininess=4
        )

        # Camada de sub-solo visível nas bordas (terra escura)
        sub_geom = _make_box(self.MAP_SIZE + 2, self.MAP_SIZE + 2, d * 0.5)
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
    def _build_boundary_walls(self):
        half  = self.MAP_SIZE / 2
        h     = self.WALL_H
        thick = 2.0
        parapet_h = 1.2   # altura do parapeito no topo

        wall_configs = [
            # (pos_x, pos_y, pos_z, largura, profundidade, altura)
            ( 0,  half, h/2,  self.MAP_SIZE + thick*2, thick, h),   # Norte
            ( 0, -half, h/2,  self.MAP_SIZE + thick*2, thick, h),   # Sul
            ( half,  0, h/2,  thick, self.MAP_SIZE, h),             # Leste
            (-half,  0, h/2,  thick, self.MAP_SIZE, h),             # Oeste
        ]

        wall_color = Vec4(0.50, 0.38, 0.25, 1)   # pedra arenito
        for i, (px, py, pz, w, d, hh) in enumerate(wall_configs):
            # Corpo principal
            g  = _make_box(w, d, hh)
            np = _attach_geom(self.root, g, f"wall_{i}")
            np.setPos(px, py, pz)
            _set_material(np, wall_color, ambient_factor=0.3,
                          specular=Vec4(0.1, 0.08, 0.06, 1), shininess=12)

            # Faixa escura na base (rodapé)
            base_g  = _make_box(w, d + 0.2, 0.4)
            base_np = _attach_geom(self.root, base_g, f"wall_base_{i}")
            base_np.setPos(px, py, 0.2)
            _set_material(base_np, Vec4(0.35, 0.26, 0.18, 1), ambient_factor=0.25, shininess=8)

            # Parapeito no topo (ameias)
            top_g  = _make_box(w, d + 0.3, parapet_h)
            top_np = _attach_geom(self.root, top_g, f"wall_top_{i}")
            top_np.setPos(px, py, hh * 2 - parapet_h / 2 + 0.05)
            _set_material(top_np, Vec4(0.42, 0.32, 0.21, 1), ambient_factor=0.3, shininess=10)

    # ── Decorações: árvores simples e plataformas ─────────────────────────
    def _build_decorations(self):
        tree_positions = [
            ( 5, 30), (-5, 30), (30,  5), (30, -5),
            (-30, 8), (-30,-8), (8, -30), (-8,-30),
            (18, 18), (-18, 18), (18,-18), (-18,-18),
            (38, 0), (-38, 0), (0, 38), (0,-38),
            (25, 38), (-25, 38), (38, 25), (-38, 25),
            (25,-38), (-25,-38), (38,-25), (-38,-25),
        ]
        for i, (x, y) in enumerate(tree_positions):
            scale = random.uniform(0.8, 1.4)
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
        """Árvore com tronco cilíndrico e copa cônica em 3 camadas."""
        trunk_h  = 3.5 * scale
        trunk_r  = 0.28 * scale

        # Tronco cilíndrico
        trunk_geom = _make_cylinder(trunk_r, trunk_h, slices=10)
        trunk_np   = _attach_geom(self.root, trunk_geom, f"trunk_{idx}")
        trunk_np.setPos(x, y, trunk_h / 2)
        _set_material(trunk_np,
                      Vec4(0.38 + random.uniform(-0.05, 0.05),
                           0.24 + random.uniform(-0.03, 0.03),
                           0.10, 1),
                      ambient_factor=0.25, shininess=4)

        # Copa — 3 cones empilhados (diminuindo para cima)
        cone_configs = [
            # (raio, altura, z_base, cor_verde)
            (2.0 * scale, 2.8 * scale, trunk_h - 0.3 * scale, Vec4(0.13, 0.55, 0.12, 1)),
            (1.5 * scale, 2.4 * scale, trunk_h + 1.6 * scale, Vec4(0.16, 0.62, 0.14, 1)),
            (1.0 * scale, 2.0 * scale, trunk_h + 3.2 * scale, Vec4(0.20, 0.68, 0.17, 1)),
        ]
        for ci, (cr, ch, cz, ccolor) in enumerate(cone_configs):
            cone_geom = _make_cone(cr, ch, slices=10)
            cone_np   = _attach_geom(self.root, cone_geom, f"canopy_{idx}_{ci}")
            cone_np.setPos(x, y, cz)
            _set_material(cone_np, ccolor, ambient_factor=0.30,
                          specular=Vec4(0.05, 0.12, 0.05, 1), shininess=6)

        # Colisor da árvore (tronco + copa)
        col = CollisionNode(f"tree_col_{idx}")
        col.addSolid(CollisionBox(Point3(0, 0, trunk_h * 0.5 + 1.5 * scale), 1.1 * scale, 1.1 * scale, trunk_h * 0.5 + 1.5 * scale))
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
            ( 6, -18, 0.3,  1.0, 0.8, 0.5),
            (-8,  22, 0.25, 0.7, 0.6, 0.4),
            (27,  12, 0.4,  1.4, 1.0, 0.7),
            (-24,-20, 0.3,  0.9, 0.7, 0.5),
            (15, -10, 0.2,  0.6, 0.5, 0.35),
            (-16, 14, 0.35, 1.2, 0.9, 0.6),
            (35, -10, 0.3,  1.0, 0.8, 0.5),
            (-35,  5, 0.25, 0.8, 0.7, 0.45),
            ( 10, 40, 0.4,  1.3, 1.0, 0.65),
            (-12,-40, 0.3,  1.0, 0.8, 0.5),
        ]
        for i, (rx, ry, rz, rw, rd, rh) in enumerate(rock_configs):
            g  = _make_box(rw, rd, rh)
            np = _attach_geom(self.root, g, f"rock_{i}")
            np.setPos(rx, ry, rz)
            np.setH(rng.uniform(0, 360))
            gray = rng.uniform(0.38, 0.55)
            _set_material(np, Vec4(gray, gray * 0.97, gray * 0.94, 1),
                          ambient_factor=0.3,
                          specular=Vec4(0.15, 0.15, 0.14, 1), shininess=15)

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
