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

from scene import Scene, _make_sphere, _make_cylinder, _attach_geom


class Player:
    """
    Controlador de personagem em terceira pessoa.

    A câmera orbita ao redor do personagem — heading (pivot.H) determina
    a direção do personagem e do olhar; cam_pitch controla a elevação da câmera.
    """

    COLLISION_RADIUS = 1.2

    # ── Câmera de órbita ──────────────────────────────────────────────────
    # Distância aumentada (~+45%) para o personagem ocupar menos tela e
    # dar mais campo de visão do cenário.
    CAM_DIST      = 8.0    # distância da câmera ao personagem
    CAM_LOOK_AT_Z = 1.25   # ponto focal no personagem (altura do torso)
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
    # Corpo anatômico (smooth shading com esferas, elipsoides e cilindros)
    # ────────────────────────────────────────────────────────────────────────
    def _build_body(self):
        """
        Constrói um humanoide articulado com primitivas suaves.

        Geometria base — todas as esferas têm raio 1.0 e são escaladas
        para virar elipsoides (custo de geração ínfimo, melhor reuso).
        Os cilindros são gerados sob medida (raios pequenos).

        Hierarquia de nós (pivot-local):
          pivot
          ├─ pelvis, torso, neck, head, hair  (estáticos)
          ├─ shoulder_l → upper_arm_l, elbow_l, forearm_l, hand_l
          ├─ shoulder_r → upper_arm_r, elbow_r, forearm_r, hand_r
          ├─ hip_l → thigh_l, knee_l, shin_l, foot_l
          └─ hip_r → thigh_r, knee_r, shin_r, foot_r

        Alturas aproximadas (chão = 0):
          pés      0.00 – 0.10
          shins    0.10 – 0.55
          thighs   0.55 – 0.95
          pelvis   0.85 – 1.05
          torso    1.05 – 1.55
          neck     1.55 – 1.65
          head     1.65 – 1.95
          hair     1.78 – 2.00
        """
        def _bmat(diffuse: Vec4, shininess: float = 14,
                  spec: float = 0.10) -> Material:
            m = Material()
            m.setDiffuse(diffuse)
            m.setAmbient(Vec4(diffuse[0] * 0.40,
                              diffuse[1] * 0.40,
                              diffuse[2] * 0.40, 1))
            m.setSpecular(Vec4(spec, spec, spec, 1))
            m.setShininess(shininess)
            return m

        SKIN  = Vec4(0.92, 0.76, 0.62, 1)
        SKIN2 = Vec4(0.86, 0.70, 0.56, 1)   # tom levemente mais escuro p/ mãos/rosto
        SHIRT = Vec4(0.16, 0.34, 0.64, 1)
        SHIRT_TRIM = Vec4(0.92, 0.95, 1.00, 1)  # detalhe colarinho/punhos
        PANTS = Vec4(0.18, 0.22, 0.42, 1)
        BELT  = Vec4(0.10, 0.07, 0.05, 1)
        BUCKLE= Vec4(0.95, 0.78, 0.18, 1)
        SHOE  = Vec4(0.18, 0.12, 0.08, 1)
        HAIR  = Vec4(0.22, 0.14, 0.08, 1)

        skin_mat   = _bmat(SKIN,  18, 0.18)
        skin2_mat  = _bmat(SKIN2, 16, 0.14)
        shirt_mat  = _bmat(SHIRT, 12, 0.10)
        trim_mat   = _bmat(SHIRT_TRIM, 14, 0.18)
        pants_mat  = _bmat(PANTS, 10, 0.08)
        belt_mat   = _bmat(BELT,  20, 0.20)
        buckle_mat = _bmat(BUCKLE,80, 0.55)
        shoe_mat   = _bmat(SHOE,  28, 0.30)
        hair_mat   = _bmat(HAIR,   8, 0.06)

        # Geometrias compartilhadas (1 vez cada — reusadas por nó).
        sphere_geom    = _make_sphere(1.0, slices=20, stacks=14)
        joint_geom     = _make_sphere(1.0, slices=12, stacks=8)

        def add_ellipsoid(parent, sx, sy, sz, pos, mat, name):
            n = _attach_geom(parent, sphere_geom, name)
            n.setScale(sx, sy, sz)
            n.setPos(*pos)
            n.setMaterial(mat, 1)
            return n

        def add_joint(parent, radius, pos, mat, name, flat: float = 0.55):
            """
            Esfera achatada que cobre o cap do cilindro do membro.
            `flat` < 1.0 espreme a junta no eixo Z para evitar bolas
            grandes nas articulações (cotovelos/joelhos/ombros).
            """
            n = _attach_geom(parent, joint_geom, name)
            n.setScale(radius, radius, radius * flat)
            n.setPos(*pos)
            n.setMaterial(mat, 1)
            return n

        def add_limb(parent, radius, length, pos, mat, name, slices=12):
            """Cilindro vertical orientado para baixo (centro no meio do segmento)."""
            geom = _make_cylinder(radius, length, slices=slices)
            n = _attach_geom(parent, geom, name)
            n.setPos(*pos)
            n.setMaterial(mat, 1)
            return n

        # ── Pelve / quadril ──────────────────────────────────────────────
        add_ellipsoid(self.pivot, 0.30, 0.20, 0.16, (0, 0, 0.96), pants_mat, "pelvis")

        # ── Cinto + fivela (separa torso/calça) ─────────────────────────
        add_ellipsoid(self.pivot, 0.31, 0.21, 0.035, (0, 0, 1.10), belt_mat, "belt")
        add_ellipsoid(self.pivot, 0.045, 0.022, 0.035, (0, 0.21, 1.10),
                      buckle_mat, "belt_buckle")

        # ── Torso (peito mais largo, cintura mais estreita) ─────────────
        add_ellipsoid(self.pivot, 0.34, 0.20, 0.28, (0, 0, 1.30), shirt_mat, "torso")
        # Reforço de ombro/costas — esfera achatada no topo do torso.
        add_ellipsoid(self.pivot, 0.36, 0.18, 0.10, (0, 0, 1.52), shirt_mat, "shoulder_pad")
        # Colarinho em "V" (detalhe claro à frente do pescoço).
        add_ellipsoid(self.pivot, 0.10, 0.05, 0.06, (0, 0.16, 1.55),
                      trim_mat, "collar")

        # ── Pescoço ──────────────────────────────────────────────────────
        add_limb(self.pivot, 0.07, 0.10, (0, 0, 1.60), skin_mat, "neck", slices=14)

        # ── Cabeça ───────────────────────────────────────────────────────
        add_ellipsoid(self.pivot, 0.18, 0.20, 0.22, (0, 0, 1.83), skin2_mat, "head")

        # ── Cabelo (calota arredondada cobrindo o topo da cabeça) ───────
        hair_top = add_ellipsoid(self.pivot, 0.20, 0.22, 0.13,
                                 (0, -0.01, 1.93), hair_mat, "hair_top")
        # Franja levemente à frente.
        add_ellipsoid(self.pivot, 0.18, 0.06, 0.07,
                      (0, 0.16, 1.86), hair_mat, "hair_bangs")
        # Laterais do cabelo (cobrem a parte de trás da cabeça/orelhas).
        add_ellipsoid(self.pivot, 0.20, 0.20, 0.10,
                      (0, -0.04, 1.80), hair_mat, "hair_back")

        # ── Olhos (esclera branca + pupila escura) ─────────────────
        EYE_WHITE = Vec4(0.96, 0.96, 0.93, 1)
        EYE       = Vec4(0.05, 0.05, 0.05, 1)
        eye_white_mat = _bmat(EYE_WHITE, 30, 0.25)
        eye_mat   = _bmat(EYE, 50, 0.40)
        # Esclera (branco do olho)
        add_ellipsoid(self.pivot, 0.038, 0.020, 0.040,
                      (-0.07, 0.180, 1.86), eye_white_mat, "eye_w_l")
        add_ellipsoid(self.pivot, 0.038, 0.020, 0.040,
                      ( 0.07, 0.180, 1.86), eye_white_mat, "eye_w_r")
        # Pupila/íris
        add_ellipsoid(self.pivot, 0.022, 0.022, 0.026,
                      (-0.07, 0.193, 1.86), eye_mat, "eye_l")
        add_ellipsoid(self.pivot, 0.022, 0.022, 0.026,
                      ( 0.07, 0.193, 1.86), eye_mat, "eye_r")
        # Brilho especular (pequeno ponto branco na pupila)
        spark_mat = _bmat(Vec4(1, 1, 1, 1), 90, 0.6)
        add_ellipsoid(self.pivot, 0.008, 0.008, 0.010,
                      (-0.063, 0.205, 1.872), spark_mat, "spark_l")
        add_ellipsoid(self.pivot, 0.008, 0.008, 0.010,
                      ( 0.077, 0.205, 1.872), spark_mat, "spark_r")

        # Sobrancelhas (caixinhas finas escuras)
        brow_mat = _bmat(Vec4(0.18, 0.10, 0.05, 1), 5, 0.05)
        for sx in (-0.07, 0.07):
            n = _attach_geom(self.pivot,
                             _make_sphere(1.0, slices=10, stacks=6),
                             f"brow_{sx}")
            n.setScale(0.045, 0.012, 0.014)
            n.setPos(sx, 0.190, 1.905)
            n.setMaterial(brow_mat, 1)

        # Nariz pequeno (esfera achatada, tom de pele mais escuro)
        add_ellipsoid(self.pivot, 0.022, 0.040, 0.022,
                      (0, 0.205, 1.825), skin2_mat, "nose")

        # Boca — linha curta (caixinha vermelha bem fina)
        mouth_mat = _bmat(Vec4(0.65, 0.18, 0.20, 1), 12, 0.10)
        mouth = _attach_geom(self.pivot,
                             _make_sphere(1.0, slices=10, stacks=6),
                             "mouth")
        mouth.setScale(0.055, 0.018, 0.012)
        mouth.setPos(0, 0.198, 1.770)
        mouth.setMaterial(mouth_mat, 1)

        # Orelhas
        for sx in (-0.18, 0.18):
            add_ellipsoid(self.pivot, 0.022, 0.045, 0.060,
                          (sx, 0.02, 1.835), skin2_mat, f"ear_{sx}")

        # ── Braços ───────────────────────────────────────────────────────
        # Pivot no ombro (topo), para que a rotação P balance todo o membro.
        SHOULDER_Z = 1.50
        SHOULDER_X = 0.30

        def build_arm(side_sign, name_suffix):
            shoulder = self.pivot.attachNewNode(f"shoulder_{name_suffix}")
            shoulder.setPos(side_sign * SHOULDER_X, 0, SHOULDER_Z)

            # Ombro arredondado (deltóide) — esfera achatada na lateral.
            add_joint(shoulder, 0.085, (0, 0, 0), shirt_mat,
                      f"deltoid_{name_suffix}", flat=0.85)
            # Braço (do ombro até cotovelo, ~0.36 de comprimento).
            add_limb(shoulder, 0.080, 0.36, (0, 0, -0.18),
                     shirt_mat, f"upper_arm_{name_suffix}")
            # Cotovelo — disco fino, mesmo raio do braço.
            add_joint(shoulder, 0.075, (0, 0, -0.36), skin_mat,
                      f"elbow_{name_suffix}", flat=0.55)
            # Antebraço (pele exposta — manga curta).
            add_limb(shoulder, 0.070, 0.34, (0, 0, -0.53),
                     skin_mat, f"forearm_{name_suffix}")
            # Pulso + mão.
            add_joint(shoulder, 0.065, (0, 0, -0.70), skin_mat,
                      f"wrist_{name_suffix}", flat=0.55)
            add_ellipsoid(shoulder, 0.07, 0.05, 0.10,
                          (0, 0, -0.81), skin2_mat,
                          f"hand_{name_suffix}")
            # Polegar (esferinha lateral)
            add_ellipsoid(shoulder, 0.025, 0.030, 0.040,
                          (side_sign * 0.05, 0.02, -0.79), skin2_mat,
                          f"thumb_{name_suffix}")
            return shoulder

        self._shoulder_l = build_arm(-1, "l")
        self._shoulder_r = build_arm(+1, "r")

        # ── Pernas ───────────────────────────────────────────────────────
        HIP_Z = 0.92
        HIP_X = 0.13

        def build_leg(side_sign, name_suffix):
            hip = self.pivot.attachNewNode(f"hip_{name_suffix}")
            hip.setPos(side_sign * HIP_X, 0, HIP_Z)

            # Coxa (cilindro grosso).
            add_limb(hip, 0.110, 0.42, (0, 0, -0.21),
                     pants_mat, f"thigh_{name_suffix}")
            # Joelho — disco fino que apenas suaviza a junta.
            add_joint(hip, 0.105, (0, 0, -0.42), pants_mat,
                      f"knee_{name_suffix}", flat=0.55)
            # Canela.
            add_limb(hip, 0.095, 0.40, (0, 0, -0.62),
                     pants_mat, f"shin_{name_suffix}")
            # Tornozelo + sapato com sola e biqueira distintas
            add_joint(hip, 0.085, (0, 0, -0.83), shoe_mat,
                      f"ankle_{name_suffix}", flat=0.50)
            # Sola larga (achatada)
            add_ellipsoid(hip, 0.105, 0.21, 0.035,
                          (0, 0.07, -0.905), shoe_mat,
                          f"sole_{name_suffix}")
            # Biqueira arredondada (parte da frente do sapato)
            add_ellipsoid(hip, 0.090, 0.10, 0.060,
                          (0, 0.16, -0.880), shoe_mat,
                          f"toe_{name_suffix}")
            # Calcanhar levemente saliente
            add_ellipsoid(hip, 0.085, 0.06, 0.055,
                          (0, -0.04, -0.880), shoe_mat,
                          f"heel_{name_suffix}")
            return hip

        self._hip_l = build_leg(-1, "l")
        self._hip_r = build_leg(+1, "r")

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
