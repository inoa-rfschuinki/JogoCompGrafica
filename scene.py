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
    WALL_H    = 5     # altura das paredes de limite
    TREE_COLLIDE_MASK = BitMask32.bit(1)
    COLLECTIBLE_COLLIDE_MASK = BitMask32.bit(2)

    def __init__(self, render: NodePath, loader):
        self.render = render
        self.loader = loader
        self.root   = render.attachNewNode("scene_root")

        self._build_ground()
        self._build_boundary_walls()
        self._build_decorations()
        self._build_sky()

    GROUND_DEPTH = 20   # espessura da laje (para não ver o céu abaixo)

    # ── Chão ─────────────────────────────────────────────────────
    def _build_ground(self):
        """
        Laje sólida: uma caixa espessa para que o FOV da câmera nunca
        mostre o vazio abaixo do terreno.
        """
        d = self.GROUND_DEPTH
        ground_geom = _make_box(self.MAP_SIZE, self.MAP_SIZE, d)
        ground_np   = _attach_geom(self.root, ground_geom, "ground")
        # Mover para baixo metade da espessura para que o topo fique em z=0
        ground_np.setPos(0, 0, -d / 2)
        _set_material(
            ground_np,
            diffuse=Vec4(0.30, 0.55, 0.25, 1),   # verde grama
            ambient_factor=0.4,
            specular=Vec4(0.05, 0.05, 0.05, 1),
            shininess=5
        )

    # ── Paredes limite ────────────────────────────────────────────────────
    def _build_boundary_walls(self):
        half = self.MAP_SIZE / 2
        h    = self.WALL_H
        thick = 1.0

        wall_configs = [
            # (pos_x, pos_y, pos_z, largura, profundidade, altura)
            ( 0,  half, h/2,  self.MAP_SIZE, thick, h),   # Norte
            ( 0, -half, h/2,  self.MAP_SIZE, thick, h),   # Sul
            ( half,  0, h/2,  thick, self.MAP_SIZE, h),   # Leste
            (-half,  0, h/2,  thick, self.MAP_SIZE, h),   # Oeste
        ]

        wall_color = Vec4(0.55, 0.40, 0.25, 1)   # marrom terra
        for i, (px, py, pz, w, d, hh) in enumerate(wall_configs):
            g  = _make_box(w, d, hh)
            np = _attach_geom(self.root, g, f"wall_{i}")
            np.setPos(px, py, pz)
            _set_material(np, wall_color, ambient_factor=0.3, shininess=8)

    # ── Decorações: árvores simples e plataformas ─────────────────────────
    def _build_decorations(self):
        tree_positions = [
            ( 5, 30), (-5, 30), (30,  5), (30, -5),
            (-30, 8), (-30,-8), (8, -30), (-8,-30),
            (18, 18), (-18, 18), (18,-18), (-18,-18),
            (38, 0), (-38, 0), (0, 38), (0,-38),
        ]
        for i, (x, y) in enumerate(tree_positions):
            self._build_tree(x, y, i)

        platform_positions = [
            (12, 0, 0.3), (-12, 0, 0.3),
            (0, 12, 0.3), (0, -12, 0.3),
            (22, 22, 0.3), (-22, 22, 0.3),
        ]
        for i, (x, y, z) in enumerate(platform_positions):
            self._build_platform(x, y, z, i)

    def _build_tree(self, x: float, y: float, idx: int):
        """Árvore simples: tronco (caixa) + copa (cubo verde)."""
        trunk_geom = _make_box(0.5, 0.5, 3.0)
        trunk_np   = _attach_geom(self.root, trunk_geom, f"trunk_{idx}")
        trunk_np.setPos(x, y, 1.5)
        _set_material(trunk_np, Vec4(0.4, 0.25, 0.1, 1), shininess=5)

        canopy_geom = _make_box(2.2, 2.2, 2.2)
        canopy_np   = _attach_geom(self.root, canopy_geom, f"canopy_{idx}")
        canopy_np.setPos(x, y, 4.1)
        _set_material(canopy_np, Vec4(0.15, 0.6, 0.15, 1), ambient_factor=0.35,
                      shininess=5)
        
        # Colisor da árvore (tronco + copa)
        col = CollisionNode(f"tree_col_{idx}")
        # Caixa centrada no meio da árvore, cobrindo tronco e copa
        col.addSolid(CollisionBox(Point3(0, 0, 2.6), 1.2, 1.2, 2.6))
        col.setFromCollideMask(BitMask32.allOff())
        col.setIntoCollideMask(self.TREE_COLLIDE_MASK)
        col_np = self.root.attachNewNode(col)
        col_np.setPos(x, y, 0)

    def _build_platform(self, x: float, y: float, z: float, idx: int):
        """Plataforma baixa como referência visual no mapa."""
        geom = _make_box(3.0, 3.0, 0.3)
        np   = _attach_geom(self.root, geom, f"platform_{idx}")
        np.setPos(x, y, z)
        _set_material(np, Vec4(0.6, 0.5, 0.35, 1), shininess=15)

    # ── Céu (caixa invertida enorme) ──────────────────────────────────────
    def _build_sky(self):
        """
        Cria um cubo muito grande com faces internas visíveis simulando o céu.
        A câmera fica sempre dentro dele.
        Nota: setColor() deve ser chamado DEPOIS de setLightOff() para que a
        cor seja usada diretamente pelo pipeline, sem influência de luzes.
        """
        size = 400
        geom = _make_box(size, size, size)
        sky_np = _attach_geom(self.root, geom, "skybox")
        # Descemos o skybox para cobrir o vazio abaixo do terreno
        sky_np.setPos(0, 0, size / 2 - 60)
        # Inverter face culling para ver de dentro
        sky_np.setTwoSided(True)
        # Desabilitar iluminação para manter cor constante
        sky_np.setLightOff()
        # Definir cor DEPOIS de setLightOff — pipeline usa setColor diretamente
        sky_np.setColor(0.40, 0.65, 0.90, 1)   # azul céu
        # Renderizar antes da cena (bin de fundo)
        sky_np.setBin("background", 0)
        sky_np.setDepthWrite(False)

    def destroy(self):
        """Remove toda a cena do grafo de cena."""
        self.root.removeNode()
