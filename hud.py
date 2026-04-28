"""
hud.py — Interface gráfica sobreposta (HUD).
"""

from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame, DirectButton
from panda3d.core import TextNode


class HUD:
    def __init__(self, base):
        self.base         = base
        self.score        = 0
        self.elapsed_time = 0.0

        # ── Painel superior esquerdo ──────────────────────────────────────
        self._score_text = OnscreenText(
            text="Pontos: 0",
            pos=(-1.55, 0.88),
            scale=0.07,
            fg=(1, 1, 0.2, 1),
            shadow=(0, 0, 0, 0.8),
            shadowOffset=(0.003, 0.003),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self._items_text = OnscreenText(
            text="Itens: 0 / 0",
            pos=(-1.55, 0.78),
            scale=0.06,
            fg=(0.9, 0.9, 0.9, 1),
            shadow=(0, 0, 0, 0.8),
            shadowOffset=(0.003, 0.003),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self._timer_text = OnscreenText(
            text="Tempo: 0s",
            pos=(-1.55, 0.68),
            scale=0.06,
            fg=(0.7, 1.0, 1.0, 1),
            shadow=(0, 0, 0, 0.8),
            shadowOffset=(0.003, 0.003),
            align=TextNode.ALeft,
            mayChange=True,
        )

        # ── Mira central ─────────────────────────────────────────────────
        self._crosshair = OnscreenText(
            text="+",
            pos=(0, 0),
            scale=0.05,
            fg=(1, 1, 1, 0.8),
            shadow=(0, 0, 0, 0.5),
            align=TextNode.ACenter,
        )

        # ── Dicas de controle ─────────────────────────────────────────────
        self._help_text = OnscreenText(
            text="WASD: mover  |  Mouse: girar  |  ESC: sair",
            pos=(0, -0.92),
            scale=0.045,
            fg=(0.7, 0.7, 0.7, 0.8),
            shadow=(0, 0, 0, 0.6),
            align=TextNode.ACenter,
        )

        # ── Flash de penalidade ────────────────────────────────────────────
        self._penalty_text = OnscreenText(
            text="",
            pos=(0, 0.28),
            scale=0.10,
            fg=(1.0, 0.2, 0.1, 1),
            shadow=(0, 0, 0, 0.9),
            shadowOffset=(0.004, 0.004),
            align=TextNode.ACenter,
            mayChange=True,
        )
        self._penalty_timer = 0.0
        self._victory_frame = None

    # ─────────────────────────────────────────────────────────────────────
    def update(self, dt: float):
        self.elapsed_time += dt

        total     = self.base.collectible_manager.total()
        remaining = self.base.collectible_manager.remaining()
        collected = total - remaining

        self._score_text.setText(f"Pontos: {self.score}")
        self._items_text.setText(f"Itens: {collected} / {total}")
        self._timer_text.setText(f"Tempo: {self.elapsed_time:.1f}s")

        if self._penalty_timer > 0:
            self._penalty_timer = max(0.0, self._penalty_timer - dt)
            if self._penalty_timer == 0.0:
                self._penalty_text.setText("")

    def add_score(self, points: int):
        self.score += points

    def add_time_penalty(self, seconds: int):
        self.elapsed_time += seconds
        self._penalty_text.setText(f"+{seconds}s  Pisou na poca!")
        self._penalty_timer = 1.8

    def destroy(self):
        self._score_text.removeNode()
        self._items_text.removeNode()
        self._timer_text.removeNode()
        self._crosshair.removeNode()
        self._help_text.removeNode()
        self._penalty_text.removeNode()
        if self._victory_frame:
            self._victory_frame.destroy()
            self._victory_frame = None

    # ─────────────────────────────────────────────────────────────────────
    # Tela de vitória
    # ─────────────────────────────────────────────────────────────────────
    def show_victory(self, final_score: int, final_time: float,
                     best_time: float = None, is_new_record: bool = False,
                     on_restart=None, on_menu=None):

        self._victory_frame = DirectFrame(
            frameColor=(0.04, 0.06, 0.16, 0.93),
            frameSize=(-1.05, 1.05, -0.76, 0.72),
            pos=(0, 0, 0),
        )

        # ── Título ────────────────────────────────────────────────────────
        OnscreenText(
            text="VOCE VENCEU!",
            pos=(0, 0.52),
            scale=0.14,
            fg=(1.0, 0.85, 0.0, 1),
            shadow=(0, 0, 0, 1),
            shadowOffset=(0.005, 0.005),
            align=TextNode.ACenter,
            parent=self._victory_frame,
        )

        # ── Separador ─────────────────────────────────────────────────────
        OnscreenText(
            text="─" * 42,
            pos=(0, 0.34),
            scale=0.042,
            fg=(0.3, 0.4, 0.6, 1),
            align=TextNode.ACenter,
            parent=self._victory_frame,
        )

        # ── Estatísticas ──────────────────────────────────────────────────
        OnscreenText(
            text=f"Pontuacao:  {final_score} pontos",
            pos=(0, 0.20),
            scale=0.075,
            fg=(1, 1, 1, 1),
            shadow=(0, 0, 0, 0.7),
            align=TextNode.ACenter,
            parent=self._victory_frame,
        )
        OnscreenText(
            text=f"Tempo:  {final_time:.1f} segundos",
            pos=(0, 0.06),
            scale=0.068,
            fg=(0.7, 1.0, 1.0, 1),
            shadow=(0, 0, 0, 0.7),
            align=TextNode.ACenter,
            parent=self._victory_frame,
        )

        # ── Recorde ───────────────────────────────────────────────────────
        if best_time is not None:
            if is_new_record:
                rec_text = f"★  NOVO RECORDE:  {best_time:.1f}s  ★"
                rec_color = (1.0, 0.50, 0.0, 1)
            else:
                rec_text = f"Melhor tempo:  {best_time:.1f}s"
                rec_color = (0.65, 0.75, 1.0, 1)
            OnscreenText(
                text=rec_text,
                pos=(0, -0.08),
                scale=0.065,
                fg=rec_color,
                shadow=(0, 0, 0, 0.7),
                shadowOffset=(0.003, 0.003),
                align=TextNode.ACenter,
                parent=self._victory_frame,
            )

        # ── Separador ─────────────────────────────────────────────────────
        OnscreenText(
            text="─" * 42,
            pos=(0, -0.20),
            scale=0.042,
            fg=(0.3, 0.4, 0.6, 1),
            align=TextNode.ACenter,
            parent=self._victory_frame,
        )

        # ── Botões (empilhados verticalmente) ─────────────────────────────
        #
        # frameSize está no espaço local do botão (antes do scale).
        # Com scale=0.09 e frameSize=(-5.8, 5.8, ...) o botão ocupa
        # 11.6 * 0.09 = 1.044 unidades de tela — cabe dentro do frame.
        #
        _btn_green = [
            (0.15, 0.50, 0.15, 1),
            (0.22, 0.70, 0.22, 1),
            (0.10, 0.35, 0.10, 1),
            (0.08, 0.25, 0.08, 1),
        ]
        _btn_blue = [
            (0.15, 0.25, 0.55, 1),
            (0.22, 0.38, 0.75, 1),
            (0.10, 0.18, 0.38, 1),
            (0.08, 0.12, 0.28, 1),
        ]

        if on_restart:
            DirectButton(
                text="Jogar Novamente",
                scale=0.085,
                pos=(0, 0, -0.36),
                frameSize=(-5.8, 5.8, -0.75, 1.05),
                frameColor=_btn_green,
                text_fg=(1, 1, 1, 1),
                text_shadow=(0, 0, 0, 0.8),
                relief=1,
                command=on_restart,
                parent=self._victory_frame,
            )

        if on_menu:
            DirectButton(
                text="Menu Principal",
                scale=0.085,
                pos=(0, 0, -0.57),
                frameSize=(-5.8, 5.8, -0.75, 1.05),
                frameColor=_btn_blue,
                text_fg=(1, 1, 1, 1),
                text_shadow=(0, 0, 0, 0.8),
                relief=1,
                command=on_menu,
                parent=self._victory_frame,
            )
