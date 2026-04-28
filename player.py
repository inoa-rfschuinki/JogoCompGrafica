"""
player.py — Controlador do jogador em terceira pessoa (over-the-shoulder).

Conceitos de CG demonstrados:
  - Câmera orbitando o personagem (transformações câmera-objeto)
  - Hierarquia de nós para animação procedural (articulação de pernas/braços)
  - Controle de orientação via ângulos de Euler (heading / cam_pitch)
  - Leitura de dispositivos de entrada (teclado + mouse)
  - Nó de colisão esférico para detecção de contato
"""

import math

from panda3d.core import (
    CollisionNode, CollisionSphere,
    Vec4, BitMask32, Material, Point3
)

from scene import Scene, _make_box, _attach_geom


class Player:
    """
    Controlador de personagem em terceira pessoa.

    A câmera orbita ao redor do personagem — heading (pivot.H) determina
    a direção do personagem e do olhar; cam_pitch controla a elevação da câmera.
    """

    COLLISION_RADIUS = 1.2

    # ── Câmera de órbita ──────────────────────────────────────────────────
    CAM_DIST      = 5.5    # distância da câmera ao personagem
    CAM_LOOK_AT_Z = 1.1    # ponto focal no personagem (altura do torso)
    CAM_PITCH_MIN = -10    # limite superior (câmera quase no nível do chão)
    CAM_PITCH_MAX = 70     # limite inferior (câmera vista de cima)

    def __init__(self, base, camera, render, pusher):
        self.base   = base
        self.camera = camera
        self.render = render

        # ── Estado de orientação ─────────────────────────────────────────
        self.heading   = 0.0
        self.cam_pitch = 22.0   # ângulo de elevação inicial (levemente acima)

        # ── Parâmetros de movimento ──────────────────────────────────────
        self.speed      = 10.0
        self.turn_speed = 90.0
        self.mouse_sens = 25.0

        # ── Nó pivot (posição do personagem no mundo) ────────────────────
        self.pivot = render.attachNewNode("player_pivot")
        self.pivot.setPos(0, 0, 0)
        self.pivot.setH(self.heading)

        # ── Câmera filha do pivot — órbita em torno do personagem ────────
        self.camera.reparentTo(self.pivot)
        self.camera.clearTransform()
        self._update_camera()

        # ── Corpo do personagem + estado de animação ─────────────────────
        self._walk_phase = 0.0
        self._is_moving  = False
        self._build_body()

        # ── Colisão ──────────────────────────────────────────────────────
        tree_col = CollisionNode("player_tree_sphere")
        tree_col.addSolid(CollisionSphere(0, 0, 0, self.COLLISION_RADIUS))
        tree_col.setFromCollideMask(Scene.TREE_COLLIDE_MASK)
        tree_col.setIntoCollideMask(BitMask32.allOff())
        self.tree_col_np = self.pivot.attachNewNode(tree_col)

        collect_col = CollisionNode("player_collect_sphere")
        collect_col.addSolid(CollisionSphere(0, 0, 0, self.COLLISION_RADIUS))
        collect_col.setFromCollideMask(Scene.COLLECTIBLE_COLLIDE_MASK)
        collect_col.setIntoCollideMask(BitMask32.allOff())
        self.collect_col_np = self.pivot.attachNewNode(collect_col)

        # Sphere menor exclusiva para poças — evita falsos positivos.
        # Raio 0.4 + raio da poça 0.7 = distância de contato 1.1 unidades,
        # dentro do disco visual interno da poça.
        obstacle_col = CollisionNode("player_obstacle_sphere")
        obstacle_col.addSolid(CollisionSphere(0, 0, 0, 0.4))
        obstacle_col.setFromCollideMask(Scene.OBSTACLE_COLLIDE_MASK)
        obstacle_col.setIntoCollideMask(BitMask32.allOff())
        self.obstacle_col_np = self.pivot.attachNewNode(obstacle_col)

        base.cTrav.addCollider(self.tree_col_np, pusher)
        pusher.addCollider(self.tree_col_np, self.pivot)
        base.cTrav.addCollider(self.collect_col_np, base.collision_handler)
        base.cTrav.addCollider(self.obstacle_col_np, base.collision_handler)

        # ── Teclas ───────────────────────────────────────────────────────
        self._keys = {
            "w": False, "s": False,
            "a": False, "d": False,
            "arrow_left": False, "arrow_right": False,
        }
        self._register_keys(base)

    # ────────────────────────────────────────────────────────────────────────
    # Câmera de órbita
    # ────────────────────────────────────────────────────────────────────────
    def _update_camera(self):
        """
        Posiciona e orienta a câmera no espaço do pivot.

        cam_pitch = 0  → câmera ao nível do personagem
        cam_pitch > 0  → câmera acima, olhando para baixo

        Cálculo:  y = -dist·cos(pitch)   (atrás do personagem)
                  z = look_at_z + dist·sin(pitch)
        """
        rad  = math.radians(self.cam_pitch)
        cam_y = -self.CAM_DIST * math.cos(rad)
        cam_z =  self.CAM_LOOK_AT_Z + self.CAM_DIST * math.sin(rad)
        self.camera.setPos(0, cam_y, cam_z)
        # lookAt com Point3 usa o espaço do pai (pivot-local) — aponta ao torso
        self.camera.lookAt(Point3(0, 0, self.CAM_LOOK_AT_Z))

    # ────────────────────────────────────────────────────────────────────────
    # Corpo blocky estilo Minecraft (visível em 3ª pessoa)
    # ────────────────────────────────────────────────────────────────────────
    def _build_body(self):
        """
        Constrói o corpo articulado do personagem.

        Hierarquia de nós (pivot-local):
          pivot
          ├─ torso, head, hair          (estáticos)
          ├─ shoulder_l → arm_l, hand_l  (pivotam no ombro para balançar braços)
          ├─ shoulder_r → arm_r, hand_r
          ├─ hip_l → leg_l, shoe_l       (pivotam no quadril para caminhar)
          └─ hip_r → leg_r, shoe_r

        Alturas (em relação ao chão, z=0):
          shoes  0.00 – 0.12
          legs   0.12 – 0.84
          torso  0.84 – 1.54
          arms   0.84 – 1.54  (mesma faixa do torso)
          head   1.54 – 1.94
          hair   1.88 – 2.02
        """
        def _bmat(diffuse: Vec4, shininess: float = 10) -> Material:
            m = Material()
            m.setDiffuse(diffuse)
            m.setAmbient(Vec4(diffuse[0]*0.35, diffuse[1]*0.35,
                              diffuse[2]*0.35, 1))
            m.setSpecular(Vec4(0.12, 0.12, 0.12, 1))
            m.setShininess(shininess)
            return m

        SKIN  = Vec4(0.90, 0.75, 0.60, 1)
        SHIRT = Vec4(0.14, 0.32, 0.62, 1)
        PANTS = Vec4(0.18, 0.22, 0.48, 1)
        SHOE  = Vec4(0.22, 0.16, 0.10, 1)
        HAIR  = Vec4(0.30, 0.20, 0.10, 1)

        # ── Partes estáticas ──────────────────────────────────────────────
        np = _attach_geom(self.pivot, _make_box(0.60, 0.35, 0.70), "torso")
        np.setPos(0, 0, 1.19);  np.setMaterial(_bmat(SHIRT, 10), 1)

        np = _attach_geom(self.pivot, _make_box(0.50, 0.50, 0.40), "head")
        np.setPos(0, 0, 1.74);  np.setMaterial(_bmat(SKIN, 12), 1)

        np = _attach_geom(self.pivot, _make_box(0.54, 0.54, 0.14), "hair")
        np.setPos(0, 0, 1.95);  np.setMaterial(_bmat(HAIR, 8), 1)

        # ── Braços (pivot no ombro, topo do torso z=1.54) ────────────────
        SHOULDER_Z = 1.54

        self._shoulder_l = self.pivot.attachNewNode("shoulder_l")
        self._shoulder_l.setPos(-0.43, 0, SHOULDER_Z)
        np = _attach_geom(self._shoulder_l, _make_box(0.25, 0.25, 0.70), "arm_l")
        np.setPos(0, 0, -0.35);   np.setMaterial(_bmat(SHIRT, 10), 1)
        np = _attach_geom(self._shoulder_l, _make_box(0.25, 0.25, 0.22), "hand_l")
        np.setPos(0, 0, -0.81);   np.setMaterial(_bmat(SKIN, 12), 1)

        self._shoulder_r = self.pivot.attachNewNode("shoulder_r")
        self._shoulder_r.setPos(0.43, 0, SHOULDER_Z)
        np = _attach_geom(self._shoulder_r, _make_box(0.25, 0.25, 0.70), "arm_r")
        np.setPos(0, 0, -0.35);   np.setMaterial(_bmat(SHIRT, 10), 1)
        np = _attach_geom(self._shoulder_r, _make_box(0.25, 0.25, 0.22), "hand_r")
        np.setPos(0, 0, -0.81);   np.setMaterial(_bmat(SKIN, 12), 1)

        # ── Pernas (pivot no quadril, base do torso z=0.84) ──────────────
        HIP_Z = 0.84

        self._hip_l = self.pivot.attachNewNode("hip_l")
        self._hip_l.setPos(-0.16, 0, HIP_Z)
        np = _attach_geom(self._hip_l, _make_box(0.27, 0.27, 0.72), "leg_l")
        np.setPos(0, 0, -0.36);   np.setMaterial(_bmat(PANTS, 10), 1)
        np = _attach_geom(self._hip_l, _make_box(0.30, 0.38, 0.12), "shoe_l")
        np.setPos(0, 0.04, -0.78); np.setMaterial(_bmat(SHOE, 15), 1)

        self._hip_r = self.pivot.attachNewNode("hip_r")
        self._hip_r.setPos(0.16, 0, HIP_Z)
        np = _attach_geom(self._hip_r, _make_box(0.27, 0.27, 0.72), "leg_r")
        np.setPos(0, 0, -0.36);   np.setMaterial(_bmat(PANTS, 10), 1)
        np = _attach_geom(self._hip_r, _make_box(0.30, 0.38, 0.12), "shoe_r")
        np.setPos(0, 0.04, -0.78); np.setMaterial(_bmat(SHOE, 15), 1)

    # ────────────────────────────────────────────────────────────────────────
    # Animação procedural de caminhada
    # ────────────────────────────────────────────────────────────────────────
    def _animate_walk(self, dt: float):
        """
        Balanço procedural de pernas e braços sincronizado com o movimento.

        Usa uma fase senoidal para criar o ciclo de passada:
          - Pernas opostas: hip_l = +swing, hip_r = -swing
          - Braços opostos: shoulder_l = -swing*0.6, shoulder_r = +swing*0.6
        """
        if self._is_moving:
            self._walk_phase = (self._walk_phase + dt * 7.0) % (2 * math.pi)
            swing = math.sin(self._walk_phase) * 28   # ±28 graus
            self._hip_l.setP( swing)
            self._hip_r.setP(-swing)
            self._shoulder_l.setP(-swing * 0.55)
            self._shoulder_r.setP( swing * 0.55)
        else:
            # Retorna suavemente à posição neutra
            self._walk_phase = 0.0
            for node in (self._hip_l, self._hip_r,
                         self._shoulder_l, self._shoulder_r):
                cur = node.getP()
                node.setP(cur * 0.75 if abs(cur) > 0.5 else 0)

    # ────────────────────────────────────────────────────────────────────────
    # Registro de teclas
    # ────────────────────────────────────────────────────────────────────────
    def _register_keys(self, base):
        for key in self._keys:
            base.accept(key,         self._set_key, [key, True])
            base.accept(key + "-up", self._set_key, [key, False])

    def _set_key(self, key, value):
        self._keys[key] = value

    # ────────────────────────────────────────────────────────────────────────
    # Loop de atualização
    # ────────────────────────────────────────────────────────────────────────
    def update(self, dt: float):
        self._handle_rotation(dt)
        self._handle_mouse()
        self._handle_movement(dt)
        self._animate_walk(dt)

    def _handle_rotation(self, dt: float):
        delta = 0.0
        if self._keys["a"] or self._keys["arrow_left"]:
            delta += self.turn_speed * dt
        if self._keys["d"] or self._keys["arrow_right"]:
            delta -= self.turn_speed * dt
        if delta:
            self.heading = (self.heading + delta) % 360
            self.pivot.setH(self.heading)

    def _handle_mouse(self):
        """
        Rotação da câmera via center-warp do mouse.
          dx → gira o heading do personagem (pivot.H)
          dy → inclina a câmera de órbita (cam_pitch)
        """
        win = self.base.win
        cx  = win.getXSize() // 2
        cy  = win.getYSize() // 2

        md = win.getPointer(0)
        if not md.getInWindow():
            return

        dx = md.getX() - cx
        dy = md.getY() - cy

        if abs(dx) > 200 or abs(dy) > 200:
            win.movePointer(0, cx, cy)
            return

        if dx != 0 or dy != 0:
            win.movePointer(0, cx, cy)
            self.heading = (self.heading - dx * self.mouse_sens * 0.01) % 360
            self.cam_pitch = max(
                self.CAM_PITCH_MIN,
                min(self.CAM_PITCH_MAX,
                    self.cam_pitch + dy * self.mouse_sens * 0.01)
            )
            self.pivot.setH(self.heading)
            self._update_camera()

    def _handle_movement(self, dt: float):
        move = 0.0
        if self._keys["w"]:
            move += self.speed * dt
        if self._keys["s"]:
            move -= self.speed * dt

        self._is_moving = (move != 0.0)

        if move:
            rad = math.radians(self.heading)
            dx  = -math.sin(rad) * move
            dy  =  math.cos(rad) * move
            pos = self.pivot.getPos()
            self.pivot.setPos(
                max(-45, min(45, pos.x + dx)),
                max(-45, min(45, pos.y + dy)),
                pos.z
            )

    # ────────────────────────────────────────────────────────────────────────
    # Accessors / teardown
    # ────────────────────────────────────────────────────────────────────────
    def get_pos(self):
        return self.pivot.getPos()

    def destroy(self, camera, render):
        """Remove o pivot e devolve a câmera ao render."""
        camera.reparentTo(render)
        camera.clearTransform()
        self.pivot.removeNode()
