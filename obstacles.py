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


def _make_disc(radius: float, segments: int = 20) -> Geom:
    """Disco plano no plano XY, centrado na origem (triângulos em leque)."""
    fmt = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData("disc", fmt, Geom.UHStatic)
    vdata.setNumRows(segments + 1)
    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")

    vertex.addData3(0, 0, 0)
    normal.addData3(0, 0, 1)
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        vertex.addData3(radius * math.cos(angle), radius * math.sin(angle), 0)
        normal.addData3(0, 0, 1)

    tris = GeomTriangles(Geom.UHStatic)
    for i in range(segments):
        tris.addVertices(0, i + 1, (i + 1) % segments + 1)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


class Puddle:
    COOLDOWN     = 2.0
    TIME_PENALTY = 5

    def __init__(self, parent: NodePath, position: Vec3, index: int):
        self._cooldown_timer = 0.0
        self._ripple_phase   = random.uniform(0, 2 * math.pi)

        self.root = parent.attachNewNode(f"obstacle_{index}")
        self.root.setPos(position)

        # Cada poça tem forma oval única
        sx = random.uniform(0.9, 1.4)
        sy = random.uniform(0.7, 1.1)
        self._base_sx = sx
        self._base_sy = sy

        # Camada externa — borda azul clara
        outer_node = GeomNode(f"puddle_outer_{index}")
        outer_node.addGeom(_make_disc(1.5, 20))
        self._outer_np = self.root.attachNewNode(outer_node)
        self._outer_np.setScale(sx, sy, 1)
        outer_mat = Material()
        outer_mat.setDiffuse(Vec4(0.30, 0.62, 0.92, 1))
        outer_mat.setAmbient(Vec4(0.12, 0.25, 0.40, 1))
        outer_mat.setSpecular(Vec4(0.95, 0.98, 1.0, 1))
        outer_mat.setShininess(110)
        self._outer_np.setMaterial(outer_mat, 1)

        # Camada interna — centro azul escuro (profundidade)
        inner_node = GeomNode(f"puddle_inner_{index}")
        inner_node.addGeom(_make_disc(0.85, 16))
        self._inner_np = self.root.attachNewNode(inner_node)
        self._inner_np.setPos(0, 0, 0.005)
        self._inner_np.setScale(sx * 0.85, sy * 0.85, 1)
        inner_mat = Material()
        inner_mat.setDiffuse(Vec4(0.12, 0.38, 0.72, 1))
        inner_mat.setAmbient(Vec4(0.05, 0.15, 0.30, 1))
        inner_mat.setSpecular(Vec4(1.0, 1.0, 1.0, 1))
        inner_mat.setShininess(160)
        self._inner_np.setMaterial(inner_mat, 1)

        # Colisão — esfera pequena correspondendo ao disco interno visível.
        # Usa OBSTACLE_COLLIDE_MASK (bit 3) separado de coletáveis (bit 2),
        # o que permite usar uma sphere específica no player com raio menor.
        col_node = CollisionNode("obstacle_sphere")
        col_node.addSolid(CollisionSphere(0, 0, 0, 0.7))
        col_node.setFromCollideMask(BitMask32.allOff())
        col_node.setIntoCollideMask(Scene.OBSTACLE_COLLIDE_MASK)
        self.col_np = self.root.attachNewNode(col_node)
        self.col_np.setTag('oid', str(index))

    def update(self, dt: float):
        if self._cooldown_timer > 0:
            self._cooldown_timer = max(0.0, self._cooldown_timer - dt)

        # Ripple: oscilação de escala e cor simulando movimento da água
        self._ripple_phase = (self._ripple_phase + dt * 1.2) % (2 * math.pi)
        ripple = math.sin(self._ripple_phase)
        f_out = 1.0 + 0.03 * ripple
        f_in  = 1.0 + 0.02 * math.sin(self._ripple_phase + 0.8)
        self._outer_np.setScale(self._base_sx * f_out, self._base_sy * f_out, 1)
        self._inner_np.setScale(self._base_sx * 0.85 * f_in, self._base_sy * 0.85 * f_in, 1)
        t = (ripple + 1) * 0.5   # remapeia [-1,1] → [0,1]
        self._inner_np.setColorScale(1.0, 1.0 + 0.15 * t, 1.0 + 0.10 * t, 1)

    def try_trigger(self) -> int:
        """Retorna TIME_PENALTY se o cooldown expirou, senão 0."""
        if self._cooldown_timer <= 0:
            self._cooldown_timer = self.COOLDOWN
            return self.TIME_PENALTY
        return 0

    def remove(self):
        self.root.removeNode()


class ObstacleManager:
    # Posicionadas em passagens naturais entre os coletáveis
    SPAWN_POSITIONS = [
        ( 5,  5), (-5, -5), (12, -8), (-12,  8),
        ( 0, 28), (28,  0), (-28,  0), ( 0, -28),
    ]

    def __init__(self, render: NodePath):
        self._items: dict[str, Puddle] = {}
        for i, (x, y) in enumerate(self.SPAWN_POSITIONS):
            item = Puddle(render, Vec3(x, y, 0.02), i)
            self._items[str(i)] = item

    def update(self, dt: float):
        for item in self._items.values():
            item.update(dt)

    def try_penalty(self, into_np: NodePath) -> int:
        """Retorna segundos de penalidade, ou 0 se cooldown ativo."""
        oid = into_np.getTag('oid')
        if oid and oid in self._items:
            return self._items[oid].try_trigger()
        return 0

    def destroy(self):
        for item in self._items.values():
            item.remove()
        self._items.clear()
