import math
import random
from panda3d.core import (
    GeomVertexFormat, GeomVertexData, GeomVertexWriter,
    Geom, GeomTriangles, GeomNode,
    CollisionNode, CollisionSphere,
    BitMask32, Vec3, NodePath, Texture
)
from scene import Scene


def _make_mud_blob(seed: int, segments: int = 24) -> Geom:
    """Blob orgânico com forma irregular para a poça de lama.
    Combina frequências senoidais para criar contorno natural e único por seed."""
    rng = random.Random(seed)
    fmt = GeomVertexFormat.getV3n3t2()
    vdata = GeomVertexData("mud_blob", fmt, Geom.UHStatic)
    vdata.setNumRows(segments + 1)
    vertex   = GeomVertexWriter(vdata, "vertex")
    normal_w = GeomVertexWriter(vdata, "normal")
    texcoord = GeomVertexWriter(vdata, "texcoord")

    # Fases aleatórias para cada frequência — cada poça tem forma diferente
    ph = [rng.uniform(0, math.tau) for _ in range(4)]

    radii = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        r = (1.0
             + 0.22 * math.sin(a * 2 + ph[0])
             + 0.14 * math.sin(a * 3 + ph[1])
             + 0.08 * math.sin(a * 5 + ph[2])
             + 0.05 * math.sin(a * 7 + ph[3])
             + rng.uniform(-0.04, 0.04))
        radii.append(max(0.55, min(1.35, r)))

    max_r = max(radii)

    vertex.addData3(0, 0, 0)
    normal_w.addData3(0, 0, 1)
    texcoord.addData2(0.5, 0.5)

    for i, r in enumerate(radii):
        a  = 2 * math.pi * i / segments
        cx = math.cos(a) * r
        cy = math.sin(a) * r
        vertex.addData3(cx, cy, 0)
        normal_w.addData3(0, 0, 1)
        texcoord.addData2(0.5 + 0.5 * cx / max_r,
                          0.5 + 0.5 * cy / max_r)

    tris = GeomTriangles(Geom.UHStatic)
    for i in range(segments):
        tris.addVertices(0, i + 1, (i + 1) % segments + 1)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


def _make_disc(radius: float, segments: int = 10) -> Geom:
    """Disco simples sem UV — usado nas bolhas."""
    fmt = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData("disc", fmt, Geom.UHStatic)
    vdata.setNumRows(segments + 1)
    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    vertex.addData3(0, 0, 0)
    normal.addData3(0, 0, 1)
    for i in range(segments):
        a = 2 * math.pi * i / segments
        vertex.addData3(radius * math.cos(a), radius * math.sin(a), 0)
        normal.addData3(0, 0, 1)
    tris = GeomTriangles(Geom.UHStatic)
    for i in range(segments):
        tris.addVertices(0, i + 1, (i + 1) % segments + 1)
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


def _make_mud_texture() -> Texture:
    """Textura de lama: marrom escuro no centro (encharcado) → mais claro nas bordas.
    NOTA: bytes armazenados como (B, G, R, A) porque o Panda3D interpreta FRgba8
    na ordem BGRA internamente — inverter R↔B corrige a cor exibida."""
    size = 128
    rng  = random.Random(53)
    data = bytearray()

    for y in range(size):
        for x in range(size):
            ux   = x / size - 0.5
            uy   = y / size - 0.5
            dist = math.sqrt(ux * ux + uy * uy)   # 0 = centro, ~0.5 = canto

            # Gradiente radial: centro escuro (molhado) → borda clara (seco)
            edge = max(0.0, (dist - 0.18) / 0.32)

            # Manchas orgânicas
            w1    = math.sin(x * 0.038 + y * 0.028) * math.cos(x * 0.019 - y * 0.044)
            w2    = math.sin(x * 0.075 - y * 0.060 + 1.1) * 0.5
            patch = (w1 + w2) / 1.5

            t = max(0.0, min(1.0, 0.5 + 0.28 * patch + 0.22 * edge))

            r_val = int(50  + t * 85)   # [50, 135]  vermelho dominante → marrom
            g_val = int(28  + t * 52)   # [28,  80]  verde secundário
            b_val = int(7   + t * 20)   # [7,   27]  azul mínimo

            noise = rng.randint(-10, 10)
            r_val = max(36, min(148, r_val + noise))
            g_val = max(18, min(92,  g_val + noise // 2))
            b_val = max(4,  min(40,  b_val + noise // 4))

            # Armazena como (B, G, R, A) para compensar a interpretação BGRA do Panda3D
            data.extend((b_val, g_val, r_val, 255))

    tex = Texture("mud_tex")
    tex.setup2dTexture(size, size, Texture.TUnsignedByte, Texture.FRgba8)
    tex.setRamImage(bytes(data))
    tex.setWrapU(Texture.WMClamp)
    tex.setWrapV(Texture.WMClamp)
    tex.setMinfilter(Texture.FTLinearMipmapLinear)
    tex.setMagfilter(Texture.FTLinear)
    return tex


class Puddle:
    COOLDOWN     = 2.0
    TIME_PENALTY = 5

    _mud_texture: Texture | None = None

    @classmethod
    def _get_mud_texture(cls) -> Texture:
        if cls._mud_texture is None:
            cls._mud_texture = _make_mud_texture()
        return cls._mud_texture

    def __init__(self, parent: NodePath, position: Vec3, index: int):
        self._cooldown_timer = 0.0
        rng = random.Random(index * 31 + 7)
        self._phases = [rng.uniform(0, 2 * math.pi) for _ in range(3)]

        self.root = parent.attachNewNode(f"obstacle_{index}")
        self.root.setPos(position)

        sx = rng.uniform(0.9, 1.4)
        sy = rng.uniform(0.7, 1.1)
        self._base_sx = sx
        self._base_sy = sy

        Z = 0.04

        # Blob de lama com forma orgânica irregular + textura
        mud_node = GeomNode(f"puddle_{index}")
        mud_node.addGeom(_make_mud_blob(seed=index * 7 + 3))
        self._mud_np = self.root.attachNewNode(mud_node)
        self._mud_np.setPos(0, 0, Z)
        self._mud_np.setScale(sx * 1.5, sy * 1.5, 1)
        self._mud_np.setTexture(self._get_mud_texture(), 1)
        self._mud_np.setLightOff()

        # Bolhas de lama
        bubble_offsets = [
            (rng.uniform(-0.28, 0.28), rng.uniform(-0.18, 0.18)),
            (rng.uniform(-0.18, 0.18), rng.uniform(-0.28, 0.28)),
            (rng.uniform(-0.10, 0.10), rng.uniform(-0.10, 0.10)),
        ]
        self._bubbles: list[NodePath] = []
        for bi, (bx, by) in enumerate(bubble_offsets):
            bn = GeomNode(f"bubble_{index}_{bi}")
            bn.addGeom(_make_disc(0.10))
            bnp = self.root.attachNewNode(bn)
            bnp.setPos(sx * bx, sy * by, Z + 0.002)
            bnp.setColor(0.42, 0.28, 0.10, 1)
            bnp.setLightOff()
            self._bubbles.append(bnp)

        # Colisão
        col_node = CollisionNode("obstacle_sphere")
        col_node.addSolid(CollisionSphere(0, 0, 0, 0.7))
        col_node.setFromCollideMask(BitMask32.allOff())
        col_node.setIntoCollideMask(Scene.OBSTACLE_COLLIDE_MASK)
        self.col_np = self.root.attachNewNode(col_node)
        self.col_np.setTag('oid', str(index))

    def update(self, dt: float):
        if self._cooldown_timer > 0:
            self._cooldown_timer = max(0.0, self._cooldown_timer - dt)

        speeds = [0.65, 1.00, 0.50]
        for i in range(3):
            self._phases[i] = (self._phases[i] + dt * speeds[i]) % (2 * math.pi)

        for bi, bnp in enumerate(self._bubbles):
            t = (math.sin(self._phases[bi]) + 1) * 0.5
            scale = 0.015 + 0.10 * t
            bnp.setScale(self._base_sx * scale, self._base_sy * scale * 0.80, 1)

    def try_trigger(self) -> int:
        if self._cooldown_timer <= 0:
            self._cooldown_timer = self.COOLDOWN
            return self.TIME_PENALTY
        return 0

    def remove(self):
        self.root.removeNode()


class ObstacleManager:
    SPAWN_POSITIONS = [
        ( 5,  5), (-5, -5), (12, -8), (-12,  8),
        ( 0, 28), (28,  0), (-28,  0), ( 0, -28),
    ]

    def __init__(self, render: NodePath):
        self._items: dict[str, Puddle] = {}
        for i, (x, y) in enumerate(self.SPAWN_POSITIONS):
            item = Puddle(render, Vec3(x, y, 0.0), i)
            self._items[str(i)] = item

    def update(self, dt: float):
        for item in self._items.values():
            item.update(dt)

    def try_penalty(self, into_np: NodePath) -> int:
        oid = into_np.getTag('oid')
        if oid and oid in self._items:
            return self._items[oid].try_trigger()
        return 0

    def destroy(self):
        for item in self._items.values():
            item.remove()
        self._items.clear()
