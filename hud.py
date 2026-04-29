"""
hud.py - Interface grafica sobreposta (HUD).
"""

from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame, DirectButton, DGG
from panda3d.core import TextNode


FA_PLAY      = "\uf04b"
FA_HOME      = "\uf015"
FA_STOPWATCH = "\uf2f2"
FA_COINS     = "\uf51e"
FA_CROWN     = "\uf521"


class HUD:
    def __init__(self, base):
        self.base         = base
        self.score        = 0
        self.elapsed_time = 0.0

        try:
            self._icon_font = base.loader.loadFont("fa-solid-900.ttf")
        except OSError:
            self._icon_font = None
        try:
            self._title_font = base.loader.loadFont("/c/Windows/Fonts/impact.ttf")
        except OSError:
            self._title_font = None

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
        self._crosshair = OnscreenText(
            text="+",
            pos=(0, 0),
            scale=0.05,
            fg=(1, 1, 1, 0.8),
            shadow=(0, 0, 0, 0.5),
            align=TextNode.ACenter,
        )
        self._help_text = OnscreenText(
            text="WASD: mover  |  Mouse: girar  |  ESC: sair",
            pos=(0, -0.92),
            scale=0.045,
            fg=(0.7, 0.7, 0.7, 0.8),
            shadow=(0, 0, 0, 0.6),
            align=TextNode.ACenter,
        )
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

    def update(self, dt: float):
        self.elapsed_time += dt

        total = self.base.collectible_manager.total()
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
        self._penalty_text.setText(f"+{seconds}s  Pisou na lama!")
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

    def show_victory(self, final_score: int, final_time: float,
                     best_time: float = None, is_new_record: bool = False,
                     on_restart=None, on_menu=None):
        if self._victory_frame:
            self._victory_frame.destroy()

        self._victory_frame = DirectFrame(
            frameColor=(0.02, 0.04, 0.10, 0.45),
            frameSize=(-2.0, 2.0, -1.2, 1.2),
            pos=(0, 0, 0),
        )

        self._create_panel_frame()
        OnscreenText(
            text="OBJETIVO CONCLUIDO",
            pos=(0, 0.40),
            scale=0.104,
            fg=(1.0, 0.84, 0.00, 1),
            shadow=(0.05, 0.03, 0.00, 1),
            shadowOffset=(0.006, -0.006),
            align=TextNode.ACenter,
            font=self._title_font,
            parent=self._victory_frame,
        )
        self._add_divider(0.31)

        self._add_stat_row(
            z=0.08,
            icon=FA_COINS,
            label="Pontuacao:",
            value=f"{final_score} pontos",
            accent=(1.0, 0.78, 0.08, 1),
        )
        self._add_stat_row(
            z=-0.11,
            icon=FA_STOPWATCH,
            label="Tempo:",
            value=f"{final_time:.1f} segundos",
            accent=(0.18, 0.72, 1.0, 1),
        )
        self._add_stat_row(
            z=-0.30,
            icon=FA_CROWN,
            label="Novo recorde:" if is_new_record else "Melhor tempo:",
            value=f"{best_time:.1f}s" if best_time is not None else "--",
            accent=(1.0, 0.48, 0.08, 1) if is_new_record else (0.62, 0.36, 1.0, 1),
        )

        if on_restart:
            self._create_victory_button(
                text="JOGAR NOVAMENTE",
                icon=FA_PLAY,
                pos=(0, 0, -0.51),
                width=1.48,
                height=0.16,
                accent=(0.25, 1.00, 0.16, 1),
                accent_hot=(0.45, 1.00, 0.34, 1),
                fill=(0.03, 0.34, 0.06, 0.95),
                fill_hot=(0.08, 0.58, 0.12, 1.00),
                command=on_restart,
            )

        if on_menu:
            self._create_victory_button(
                text="MENU PRINCIPAL",
                icon=FA_HOME,
                pos=(0, 0, -0.70),
                width=1.48,
                height=0.16,
                accent=(0.18, 0.50, 1.00, 1),
                accent_hot=(0.36, 0.68, 1.00, 1),
                fill=(0.03, 0.16, 0.46, 0.95),
                fill_hot=(0.08, 0.30, 0.72, 1.00),
                command=on_menu,
            )

    def _create_panel_frame(self):
        DirectFrame(
            frameColor=(0.64, 0.75, 0.86, 0.45),
            frameSize=(-1.12, 1.12, -0.97, 0.79),
            pos=(0, 0, -0.02),
            parent=self._victory_frame,
        )
        DirectFrame(
            frameColor=(0.03, 0.07, 0.15, 0.94),
            frameSize=(-1.105, 1.105, -0.955, 0.775),
            pos=(0, 0, -0.02),
            parent=self._victory_frame,
        )
        DirectFrame(
            frameColor=(0.02, 0.05, 0.11, 0.88),
            frameSize=(-1.02, 1.02, -0.875, 0.665),
            pos=(0, 0, -0.02),
            parent=self._victory_frame,
        )

    def _add_icon(self, icon, x, z, scale, color):
        OnscreenText(
            text=icon,
            pos=(x, z),
            scale=scale,
            fg=color,
            shadow=(0, 0, 0, 0.9),
            shadowOffset=(0.006, -0.006),
            align=TextNode.ACenter,
            font=self._icon_font,
            parent=self._victory_frame,
        )

    def _add_divider(self, z):
        DirectFrame(
            frameColor=(0.12, 0.65, 1.00, 0.35),
            frameSize=(-0.55, 0.55, -0.004, 0.004),
            pos=(0, 0, z),
            parent=self._victory_frame,
        )
        DirectFrame(
            frameColor=(0.35, 0.72, 1.00, 0.85),
            frameSize=(-0.018, 0.018, -0.018, 0.018),
            pos=(0, 0, z),
            parent=self._victory_frame,
        )

    def _add_stat_row(self, z, icon, label, value, accent):
        DirectFrame(
            frameColor=(0.11, 0.18, 0.26, 0.72),
            frameSize=(-0.82, 0.82, -0.075, 0.075),
            pos=(0, 0, z),
            parent=self._victory_frame,
        )
        DirectFrame(
            frameColor=(accent[0], accent[1], accent[2], 0.22),
            frameSize=(-0.82, 0.82, -0.075, -0.062),
            pos=(0, 0, z),
            parent=self._victory_frame,
        )
        self._add_icon(icon, -0.66, z - 0.030, 0.070, accent)
        OnscreenText(
            text=label,
            pos=(-0.50, z - 0.030),
            scale=0.055,
            fg=(0.94, 0.97, 1.0, 1),
            shadow=(0, 0, 0, 0.8),
            shadowOffset=(0.003, -0.003),
            align=TextNode.ALeft,
            parent=self._victory_frame,
        )
        OnscreenText(
            text=value,
            pos=(0.72, z - 0.030),
            scale=0.060,
            fg=accent,
            shadow=(0, 0, 0, 0.8),
            shadowOffset=(0.003, -0.003),
            align=TextNode.ARight,
            parent=self._victory_frame,
        )

    def _create_victory_button(self, text, icon, pos, width, height, accent,
                               accent_hot, fill, fill_hot, command):
        x0, x1 = -width / 2.0, width / 2.0
        y0, y1 = -height / 2.0, height / 2.0

        glow = DirectFrame(
            frameColor=(accent[0], accent[1], accent[2], 0.14),
            frameSize=(x0 - 0.014, x1 + 0.014, y0 - 0.014, y1 + 0.014),
            pos=pos,
            parent=self._victory_frame,
        )
        border = DirectFrame(
            frameColor=accent,
            frameSize=(x0 - 0.006, x1 + 0.006, y0 - 0.006, y1 + 0.006),
            pos=pos,
            parent=self._victory_frame,
        )
        face = DirectFrame(
            frameColor=fill,
            frameSize=(x0, x1, y0, y1),
            pos=pos,
            parent=self._victory_frame,
        )
        shine = DirectFrame(
            frameColor=(1, 1, 1, 0.08),
            frameSize=(x0 + 0.025, x1 - 0.025, y1 - height * 0.34, y1 - 0.018),
            pos=pos,
            parent=self._victory_frame,
        )
        hit = DirectButton(
            text="",
            frameSize=(x0 - 0.014, x1 + 0.014, y0 - 0.014, y1 + 0.014),
            frameColor=(1, 1, 1, 0.01),
            relief=DGG.FLAT,
            command=command,
            pos=pos,
            parent=self._victory_frame,
        )
        icon_text = OnscreenText(
            text=icon,
            pos=(pos[0] + x0 + width * 0.16, pos[2] - 0.027),
            scale=0.060,
            fg=(1, 1, 1, 0.96),
            shadow=(accent[0], accent[1], accent[2], 0.85),
            shadowOffset=(0.003, -0.003),
            align=TextNode.ACenter,
            font=self._icon_font,
            parent=self._victory_frame,
        )
        label_text = OnscreenText(
            text=text,
            pos=(pos[0] + width * 0.07, pos[2] - 0.038),
            scale=0.062,
            fg=(1, 1, 1, 1),
            shadow=(0, 0, 0, 0.9),
            shadowOffset=(0.004, -0.004),
            align=TextNode.ACenter,
            parent=self._victory_frame,
        )

        def set_hot():
            glow["frameColor"] = (accent_hot[0], accent_hot[1], accent_hot[2], 0.34)
            border["frameColor"] = accent_hot
            face["frameColor"] = fill_hot
            shine["frameColor"] = (1, 1, 1, 0.20)
            icon_text["fg"] = accent_hot
            label_text["fg"] = (1.0, 1.0, 0.92, 1)

        def set_normal():
            glow["frameColor"] = (accent[0], accent[1], accent[2], 0.14)
            border["frameColor"] = accent
            face["frameColor"] = fill
            shine["frameColor"] = (1, 1, 1, 0.08)
            icon_text["fg"] = (1, 1, 1, 0.96)
            label_text["fg"] = (1, 1, 1, 1)

        hit.bind(DGG.ENTER, lambda _event: set_hot())
        hit.bind(DGG.EXIT, lambda _event: set_normal())
