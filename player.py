"""
player.py — Controlador do jogador em primeira pessoa.

Conceitos de CG demonstrados:
  - Transformações de câmera (translação e rotação)
  - Controle de orientação via ângulos de Euler (heading / pitch)
  - Leitura de dispositivos de entrada (teclado + mouse)
  - Nó de colisão esférico para detecção de contato
"""

from panda3d.core import (
    CollisionNode, CollisionSphere,
    Vec3, BitMask32
)

from scene import Scene


class Player:
    """
    Encapsula a câmera de primeira pessoa e o nó de colisão do jogador.

    Atributos públicos
    ------------------
    speed       : velocidade de translação (unidades/segundo)
    turn_speed  : velocidade de rotação horizontal (graus/segundo, teclado)
    mouse_sens  : sensibilidade do mouse
    heading     : ângulo horizontal atual (graus)
    pitch       : ângulo vertical atual (graus)
    """

    COLLISION_RADIUS = 1.2   # raio da esfera de colisão do jogador
    CAMERA_HEIGHT    = 1.7   # altura dos olhos em relação ao chão
    PITCH_LIMIT      = 80    # limite de inclinação vertical (graus)

    def __init__(self, base, camera, render, pusher):
        self.base   = base
        self.camera = camera
        self.render = render

        # ── Posição e orientação inicial ─────────────────────────────────
        self.heading = 0.0   # rotação horizontal (Y mundial)
        self.pitch   = 0.0   # inclinação vertical

        # ── Parâmetros de movimento ──────────────────────────────────────
        self.speed      = 10.0   # unidades por segundo
        self.turn_speed = 90.0   # graus por segundo (rotação por teclado)
        self.mouse_sens = 25.0   # sensibilidade do mouse

        # ── Nó pivot para separar heading (Y) e pitch (câmera) ──────────
        # O pivot gira apenas no eixo Z (heading);
        # a câmera filha inclina no eixo X (pitch).
        self.pivot = render.attachNewNode("player_pivot")
        self.pivot.setPos(0, 0, 0)

        # Reparentar câmera ao pivot e resetar sua transform por completo
        self.camera.reparentTo(self.pivot)
        self.camera.clearTransform()
        self.camera.setPos(0, 0, self.CAMERA_HEIGHT)
        # No Panda3D: H=heading, P=pitch, R=roll
        # HPR (0, 0, 0) = olhando ao longo do eixo Y positivo (para frente)
        self.camera.setHpr(0, 0, 0)
        # Aplicar heading e pitch iniciais ao pivot e câmera
        self.pivot.setH(self.heading)
        self.camera.setP(self.pitch)

        # ── Colisão ──────────────────────────────────────────────────────
        # Colisor para árvores (pusher)
        tree_col = CollisionNode("player_tree_sphere")
        tree_col.addSolid(CollisionSphere(0, 0, 0, self.COLLISION_RADIUS))
        tree_col.setFromCollideMask(Scene.TREE_COLLIDE_MASK)
        tree_col.setIntoCollideMask(BitMask32.allOff())
        self.tree_col_np = self.pivot.attachNewNode(tree_col)

        # Colisor para coletáveis (eventos)
        collect_col = CollisionNode("player_collect_sphere")
        collect_col.addSolid(CollisionSphere(0, 0, 0, self.COLLISION_RADIUS))
        collect_col.setFromCollideMask(Scene.COLLECTIBLE_COLLIDE_MASK)
        collect_col.setIntoCollideMask(BitMask32.allOff())
        self.collect_col_np = self.pivot.attachNewNode(collect_col)

        base.cTrav.addCollider(self.tree_col_np, pusher)
        pusher.addCollider(self.tree_col_np, self.pivot)

        base.cTrav.addCollider(self.collect_col_np, base.collision_handler)

        # ── Teclas pressionadas ──────────────────────────────────────────
        self._keys = {
            "w": False, "s": False,
            "a": False, "d": False,
            "arrow_left": False, "arrow_right": False,
        }
        self._register_keys(base)

    # ────────────────────────────────────────────────────────────────────────
    # Registro de teclas
    # ────────────────────────────────────────────────────────────────────────
    def _register_keys(self, base):
        for key in self._keys:
            base.accept(key,        self._set_key, [key, True])
            base.accept(key + "-up", self._set_key, [key, False])

    def _set_key(self, key, value):
        self._keys[key] = value

    # ────────────────────────────────────────────────────────────────────────
    # Atualização por frame
    # ────────────────────────────────────────────────────────────────────────
    def update(self, dt: float):
        """
        Chamado a cada frame pelo loop principal.
        Atualiza a posição e orientação do jogador com base nas entradas.
        """
        self._handle_rotation(dt)
        self._handle_mouse()
        self._handle_movement(dt)

    # ── Rotação horizontal (teclado A / D e setas) ───────────────────────
    def _handle_rotation(self, dt: float):
        delta = 0.0
        if self._keys["a"] or self._keys["arrow_left"]:
            delta += self.turn_speed * dt
        if self._keys["d"] or self._keys["arrow_right"]:
            delta -= self.turn_speed * dt

        if delta:
            self.heading = (self.heading + delta) % 360
            self.pivot.setH(self.heading)

    # ── Inclinação vertical (mouse) ───────────────────────────────────────
    def _handle_mouse(self):
        """
        Controle FPS via center-warp: lê posição atual do cursor, calcula
        delta em relação ao centro da janela e reposiciona o cursor no centro.
        Esta abordagem é compatível com todas as plataformas.
        """
        win = self.base.win
        cx = win.getXSize() // 2
        cy = win.getYSize() // 2

        md = win.getPointer(0)
        if not md.getInWindow():
            return

        dx = md.getX() - cx
        dy = md.getY() - cy

        # Ignorar saltos grandes (primeiro frame ou foco retornado)
        if abs(dx) > 200 or abs(dy) > 200:
            win.movePointer(0, cx, cy)
            return

        if dx != 0 or dy != 0:
            win.movePointer(0, cx, cy)
            self.heading -= dx * self.mouse_sens * 0.01
            self.pitch    = max(
                -self.PITCH_LIMIT,
                min(self.PITCH_LIMIT, self.pitch - dy * self.mouse_sens * 0.01)
            )
            self.pivot.setH(self.heading % 360)
            self.camera.setP(self.pitch)

    # ── Translação (W / S) ────────────────────────────────────────────────
    def _handle_movement(self, dt: float):
        move = 0.0
        if self._keys["w"]:
            move += self.speed * dt
        if self._keys["s"]:
            move -= self.speed * dt

        if move:
            import math
            rad = math.radians(self.heading)
            dx = -math.sin(rad) * move
            dy =  math.cos(rad) * move

            pos = self.pivot.getPos()
            # Limitar ao tamanho do mapa (±45 unidades)
            new_x = max(-45, min(45, pos.x + dx))
            new_y = max(-45, min(45, pos.y + dy))
            self.pivot.setPos(new_x, new_y, pos.z)

    # ────────────────────────────────────────────────────────────────────────
    # Accessors
    # ────────────────────────────────────────────────────────────────────────
    def get_pos(self):
        return self.pivot.getPos()

    def destroy(self, camera, render):
        """Remove o pivot e devolve a camera ao render."""
        camera.reparentTo(render)
        camera.clearTransform()
        self.pivot.removeNode()
