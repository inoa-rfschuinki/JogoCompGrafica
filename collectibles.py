"""
collectibles.py — Sistema de objetos coletáveis.

Conceitos de CG demonstrados:
  - Criação procedural de geometria (GeomNode + GeomVertexData)
  - Transformações hierárquicas (nós pai/filho no grafo de cena)
  - Animação de rotação via Task (ângulo += velocidade_angular * dt)
  - Efeito de "bob" senoidal (translação periódica no eixo Z)
  - Colisão esférica (from/into masks) integrada ao CollisionTraverser
  - Material e cor por nó
"""

import math
import random
from panda3d.core import (
    GeomVertexFormat, GeomVertexData, GeomVertexWriter,
    Geom, GeomTriangles, GeomNode,
    CollisionNode, CollisionSphere,
    BitMask32, Vec4, Vec3, NodePath,
    Material
)

from scene import Scene


# ──────────────────────────────────────────────────────────────────────────────
# Funções de geometria procedural
# ──────────────────────────────────────────────────────────────────────────────

def _make_sphere_geom(radius: float = 0.5, stacks: int = 12, slices: int = 16) -> Geom:
    """
    Gera uma esfera UV triangulada proceduralmente.

    Parâmetros
    ----------
    radius : raio da esfera
    stacks : subdivisões verticais
    slices : subdivisões horizontais
    """
    fmt = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData("sphere", fmt, Geom.UHStatic)
    vdata.setNumRows((stacks + 1) * (slices + 1))

    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")

    # Gerar vértices
    for i in range(stacks + 1):
        phi = math.pi * i / stacks          # [0, π]
        for j in range(slices + 1):
            theta = 2 * math.pi * j / slices  # [0, 2π]
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.sin(phi) * math.sin(theta)
            z = radius * math.cos(phi)
            vertex.addData3(x, y, z)
            nx, ny, nz = x / radius, y / radius, z / radius
            normal.addData3(nx, ny, nz)

    # Gerar triângulos
    tris = GeomTriangles(Geom.UHStatic)
    for i in range(stacks):
        for j in range(slices):
            a = i * (slices + 1) + j
            b = a + 1
            c = a + (slices + 1)
            d = c + 1
            tris.addVertices(a, c, b)
            tris.addVertices(b, c, d)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


def _make_cube_geom(size: float = 0.6) -> Geom:
    """
    Gera um cubo com normais por face.
    """
    h = size / 2
    fmt = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData("cube", fmt, Geom.UHStatic)
    vdata.setNumRows(24)

    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")

    faces = [
        # 4 vértices + normal por face
        ([(-h,-h, h),(h,-h, h),(h, h, h),(-h, h, h)], ( 0, 0, 1)),  # topo
        ([(-h,-h,-h),(-h, h,-h),(h, h,-h),(h,-h,-h)], ( 0, 0,-1)),  # base
        ([(-h,-h,-h),(-h,-h, h),(-h, h, h),(-h, h,-h)], (-1, 0, 0)),  # esq
        ([(h,-h,-h),(h, h,-h),(h, h, h),(h,-h, h)],  ( 1, 0, 0)),  # dir
        ([(-h, h,-h),(-h, h, h),(h, h, h),(h, h,-h)], ( 0, 1, 0)),  # frente
        ([(-h,-h,-h),(h,-h,-h),(h,-h, h),(-h,-h, h)], ( 0,-1, 0)),  # trás
    ]

    for verts, n in faces:
        for v in verts:
            vertex.addData3(*v)
            normal.addData3(*n)

    tris = GeomTriangles(Geom.UHStatic)
    for f in range(6):
        base = f * 4
        tris.addVertices(base,     base + 1, base + 2)
        tris.addVertices(base,     base + 2, base + 3)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


# ──────────────────────────────────────────────────────────────────────────────
# Coletável individual
# ──────────────────────────────────────────────────────────────────────────────

# Paleta de cores para os coletáveis
COLORS = [
    Vec4(1.0, 0.85, 0.0, 1),   # ouro
    Vec4(0.0, 0.8,  1.0, 1),   # azul ciano
    Vec4(1.0, 0.3,  0.3, 1),   # vermelho
    Vec4(0.3, 1.0,  0.4, 1),   # verde
    Vec4(1.0, 0.5,  0.0, 1),   # laranja
    Vec4(0.8, 0.3,  1.0, 1),   # roxo
]

SHAPES = ["sphere", "cube"]


class Collectible:
    """
    Um único objeto coletável na cena.

    Possui:
      - Geometria procedural (esfera ou cubo)
      - Rotação contínua no eixo Y
      - Oscilação vertical senoidal (bob)
      - Esfera de colisão Panda3D
    """

    BOB_AMPLITUDE = 0.25   # amplitude da oscilação vertical
    BOB_SPEED     = 2.0    # velocidade da oscilação (rad/s)
    ROT_SPEED     = 90.0   # velocidade de rotação (graus/s)

    def __init__(self, parent: NodePath, position: Vec3,
                 shape: str = "sphere", color: Vec4 = None,
                 cTrav=None, collision_handler=None, index: int = 0):

        self.alive = True
        self._base_z = position.z
        self._bob_phase = random.uniform(0, 2 * math.pi)
        self._rot_angle = random.uniform(0, 360)

        # ── Nó raiz deste coletável ──────────────────────────────────────
        self.root = parent.attachNewNode(f"collectible_{index}")
        self.root.setPos(position)

        # ── Geometria ────────────────────────────────────────────────────
        if shape == "sphere":
            geom = _make_sphere_geom(radius=0.45)
        else:
            geom = _make_cube_geom(size=0.7)

        geom_node = GeomNode(f"collectible_geom_{index}")
        geom_node.addGeom(geom)
        self.geom_np = self.root.attachNewNode(geom_node)

        # ── Material / cor ───────────────────────────────────────────────
        col = color if color else random.choice(COLORS)
        mat = Material()
        mat.setDiffuse(col)
        mat.setAmbient(Vec4(col[0]*0.4, col[1]*0.4, col[2]*0.4, 1))
        mat.setSpecular(Vec4(0.8, 0.8, 0.8, 1))
        mat.setShininess(60)
        self.geom_np.setMaterial(mat, 1)

        # ── Colisão ──────────────────────────────────────────────────────
        # Todos usam o mesmo nome para o evento casar no accept()
        col_node = CollisionNode("collectible_sphere")
        col_node.addSolid(CollisionSphere(0, 0, 0, 0.8))
        col_node.setFromCollideMask(BitMask32.allOff())
        col_node.setIntoCollideMask(Scene.COLLECTIBLE_COLLIDE_MASK)
        self.col_np = self.root.attachNewNode(col_node)
        # Tag com índice único — lido via getTag() no evento de colisão
        self.col_np.setTag('cid', str(index))

    # ────────────────────────────────────────────────────────────────────────
    def update(self, dt: float, elapsed: float):
        """Anima rotação e oscilação vertical a cada frame."""
        if not self.alive:
            return

        # Rotação contínua no eixo Z
        self._rot_angle = (self._rot_angle + self.ROT_SPEED * dt) % 360
        self.geom_np.setH(self._rot_angle)

        # Bob senoidal
        bob = math.sin(elapsed * self.BOB_SPEED + self._bob_phase)
        self.root.setZ(self._base_z + bob * self.BOB_AMPLITUDE)

    def remove(self):
        """Remove o nó da cena."""
        self.alive = False
        self.root.removeNode()

    @property
    def col_node_path(self):
        return self.col_np

    @property
    def cid(self):
        return self.col_np.getTag('cid')


# ──────────────────────────────────────────────────────────────────────────────
# Gerenciador de coletáveis
# ──────────────────────────────────────────────────────────────────────────────

class CollectibleManager:
    """
    Cria, armazena e atualiza todos os coletáveis do nível.
    """

    # Posições fixas espalhadas pelo mapa (x, y) — 15 itens
    SPAWN_POSITIONS = [
        ( 10,  10), (-10,  10), ( 10, -10), (-10, -10),
        ( 20,   0), (-20,   0), (  0,  20), (  0, -20),
        ( 15,  25), (-15,  25), ( 15, -25), (-15, -25),
        ( 30,  15), (-30, -15), (  5,  35),
    ]

    def __init__(self, render, loader, cTrav, collision_handler):
        self._render   = render
        self._loader   = loader
        self._cTrav    = cTrav
        self._handler  = collision_handler
        self._elapsed  = 0.0

        self._items: dict[str, Collectible] = {}
        self._spawn_all()

    def _spawn_all(self):
        shapes = SHAPES * (len(self.SPAWN_POSITIONS) // len(SHAPES) + 1)
        colors = COLORS  * (len(self.SPAWN_POSITIONS) // len(COLORS)  + 1)

        for i, (x, y) in enumerate(self.SPAWN_POSITIONS):
            shape = shapes[i % len(SHAPES)]
            color = colors[i % len(COLORS)]
            pos   = Vec3(x, y, 1.0)

            item = Collectible(
                parent=self._render,
                position=pos,
                shape=shape,
                color=color,
                cTrav=self._cTrav,
                collision_handler=self._handler,
                index=i,
            )
            # Chaveado pela tag 'cid' — string do índice
            self._items[str(i)] = item

    def update(self, dt: float):
        self._elapsed += dt
        for item in self._items.values():
            item.update(dt, self._elapsed)

    def collect(self, into_np: NodePath) -> bool:
        """
        Tenta coletar o item associado ao NodePath de colisão.
        Usa a tag 'cid' gravada no nó para identificar o item.
        Retorna True se coletou com sucesso.
        """
        cid = into_np.getTag('cid')
        if cid and cid in self._items and self._items[cid].alive:
            self._items[cid].remove()
            return True
        return False

    def remaining(self) -> int:
        return sum(1 for item in self._items.values() if item.alive)

    def total(self) -> int:
        return len(self._items)

    def destroy(self):
        """Remove todos os coletaveis vivos da cena."""
        for item in self._items.values():
            if item.alive:
                item.remove()
        self._items.clear()
