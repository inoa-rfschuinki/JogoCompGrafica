"""
menu.py — Tela de menu principal do jogo.
"""

from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame, DirectButton, DGG
from panda3d.core import TextNode

# Font Awesome 6 Solid — code points dos ícones usados
FA_CROSSHAIRS = ""   # fa-crosshairs
FA_KEYBOARD   = ""   # fa-keyboard
FA_STOPWATCH  = ""   # fa-stopwatch
FA_PLAY       = "\uf04b" # fa-play
FA_SIGN_OUT   = "\uf2f5" # fa-right-from-bracket
FA_TROPHY     = "\uf091" # fa-trophy
FA_MOUSE      = "\uf8cc" # fa-computer-mouse


class Menu:
    def __init__(self, base, on_start, on_quit):
        self.base      = base
        self._on_start = on_start
        self._on_quit  = on_quit

        # ── Fontes TTF ───────────────────────────────────────────────────────
        _title_font = base.loader.loadFont("/c/Windows/Fonts/impact.ttf")
        _title_font.setPixelsPerUnit(150)

        _ui_font = base.loader.loadFont("/c/Windows/Fonts/arialbd.ttf")
        _ui_font.setPixelsPerUnit(80)

        _icon_font = base.loader.loadFont("fa-solid-900.ttf")
        _icon_font.setPixelsPerUnit(80)
        self._ui_font = _ui_font
        self._icon_font = _icon_font

        # ── Fundo ────────────────────────────────────────────────────────────
        self._frame = DirectFrame(
            frameColor=(0.05, 0.07, 0.18, 1.0),
            frameSize=(-2, 2, -1.2, 1.2),
            pos=(0, 0, 0),
        )

        # ── Painel central (criado antes do texto para ficar atrás) ──────────
        DirectFrame(
            frameColor=(0.12, 0.65, 1.00, 0.42),
            frameSize=(-0.862, 0.862, -0.402, 0.402),
            pos=(0, 0, 0.0),
            parent=self._frame,
        )
        DirectFrame(
            frameColor=(0.04, 0.08, 0.22, 0.94),
            frameSize=(-0.858, 0.858, -0.398, 0.398),
            pos=(0, 0, 0.0),
            parent=self._frame,
        )

        # ── Título ───────────────────────────────────────────────────────────
        _SCALE = 0.22
        _GAP   = 0.055
        _tn = TextNode("_measure")
        _tn.setFont(_title_font)
        _tn.setText("COLETOR")
        _coletor_w = _tn.getWidth() * _SCALE
        _tn.setText("3D")
        _3d_w = _tn.getWidth() * _SCALE
        _title_left = -(_coletor_w + _GAP + _3d_w) / 2.0

        OnscreenText(
            text="COLETOR",
            pos=(_title_left, 0.70), scale=_SCALE,
            fg=(0.93, 0.96, 1.00, 1),
            shadow=(0.03, 0.07, 0.25, 0.85), shadowOffset=(0.007, -0.007),
            align=TextNode.ALeft, font=_title_font, parent=self._frame,
        )
        OnscreenText(
            text="3D",
            pos=(_title_left + _coletor_w + _GAP, 0.70), scale=_SCALE,
            fg=(1.00, 0.84, 0.00, 1),
            shadow=(0.03, 0.07, 0.25, 0.85), shadowOffset=(0.007, -0.007),
            align=TextNode.ALeft, font=_title_font, parent=self._frame,
        )

        # ── Subtítulo ────────────────────────────────────────────────────────
        OnscreenText(
            text="—  TRABALHO DE COMPUTACAO GRAFICA  —",
            pos=(0, 0.50), scale=0.046,
            fg=(0.25, 0.72, 1.00, 1),
            align=TextNode.ACenter, font=_ui_font, parent=self._frame,
        )

        _CYAN = (0.10, 0.80, 1.00, 1)
        _TEXT = (0.82, 0.86, 0.92, 1)

        # ── OBJETIVO ─────────────────────────────────────────────────────────
        OnscreenText(
            text=FA_CROSSHAIRS,
            pos=(-0.78, 0.305), scale=0.065,
            fg=_CYAN, align=TextNode.ALeft,
            font=_icon_font, parent=self._frame,
        )
        OnscreenText(
            text="OBJETIVO", pos=(-0.63, 0.305), scale=0.052,
            fg=_CYAN, align=TextNode.ALeft,
            font=_ui_font, parent=self._frame,
        )
        OnscreenText(
            text="Colete todos os 5 objetos espalhados pelo mapa!",
            pos=(-0.63, 0.215), scale=0.043,
            fg=_TEXT, align=TextNode.ALeft,
            font=_ui_font, parent=self._frame,
        )

        # ── CONTROLES ────────────────────────────────────────────────────────
        OnscreenText(
            text=FA_KEYBOARD,
            pos=(-0.78, 0.055), scale=0.065,
            fg=_CYAN, align=TextNode.ALeft,
            font=_icon_font, parent=self._frame,
        )
        OnscreenText(
            text="CONTROLES", pos=(-0.63, 0.055), scale=0.052,
            fg=_CYAN, align=TextNode.ALeft,
            font=_ui_font, parent=self._frame,
        )
        self._create_key_label("W", -0.60, -0.045)
        self._create_key_label("S", -0.545, -0.045)
        OnscreenText(
            text="— mover", pos=(-0.49, -0.057), scale=0.040,
            fg=_TEXT, align=TextNode.ALeft, font=_ui_font, parent=self._frame,
        )
        self._create_key_label("A", -0.21, -0.045)
        self._create_key_label("D", -0.155, -0.045)
        OnscreenText(
            text="— girar", pos=(-0.10, -0.057), scale=0.040,
            fg=_TEXT, align=TextNode.ALeft, font=_ui_font, parent=self._frame,
        )
        self._create_mouse_label(0.28, -0.045)
        OnscreenText(
            text="— olhar", pos=(0.35, -0.057), scale=0.040,
            fg=_TEXT, align=TextNode.ALeft, font=_ui_font, parent=self._frame,
        )

        # ── MELHOR TEMPO ─────────────────────────────────────────────────────
        OnscreenText(
            text=FA_STOPWATCH,
            pos=(-0.78, -0.195), scale=0.065,
            fg=_CYAN, align=TextNode.ALeft,
            font=_icon_font, parent=self._frame,
        )
        OnscreenText(
            text="MELHOR TEMPO", pos=(-0.63, -0.195), scale=0.052,
            fg=_CYAN, align=TextNode.ALeft,
            font=_ui_font, parent=self._frame,
        )
        self._record_text = OnscreenText(
            text="Sem recorde — seja o primeiro!",
            pos=(0.07, -0.305), scale=0.070,
            fg=(0.55, 0.55, 0.55, 1),
            shadow=(0, 0, 0, 0.8), shadowOffset=(0.004, 0.004),
            align=TextNode.ACenter,
            font=_ui_font, mayChange=True, parent=self._frame,
        )
        OnscreenText(
            text=FA_TROPHY,
            pos=(-0.26, -0.305), scale=0.060,
            fg=(1.0, 0.74, 0.10, 1),
            shadow=(0.75, 0.42, 0.00, 0.8), shadowOffset=(0.003, -0.003),
            align=TextNode.ACenter,
            font=_icon_font, parent=self._frame,
        )

        # ── Botões ───────────────────────────────────────────────────────────
        self._create_menu_button(
            text="JOGAR",
            icon=FA_PLAY,
            pos=(0, 0, -0.64),
            width=0.94,
            height=0.18,
            accent=(0.25, 1.00, 0.16, 1),
            accent_hot=(0.45, 1.00, 0.34, 1),
            fill=(0.02, 0.24, 0.04, 0.92),
            fill_hot=(0.08, 0.58, 0.12, 1.00),
            text_scale=0.086,
            icon_scale=0.072,
            command=on_start,
        )
        self._create_menu_button(
            text="SAIR",
            icon=FA_SIGN_OUT,
            pos=(0, 0, -0.85),
            width=0.72,
            height=0.14,
            accent=(1.00, 0.22, 0.16, 1),
            accent_hot=(1.00, 0.42, 0.34, 1),
            fill=(0.22, 0.03, 0.03, 0.90),
            fill_hot=(0.56, 0.08, 0.06, 1.00),
            text_scale=0.065,
            icon_scale=0.055,
            command=on_quit,
        )

        # ── Resultado da última partida ──────────────────────────────────────
        self._result_text = OnscreenText(
            text="", pos=(0, -1.03), scale=0.048,
            fg=(0.60, 1.0, 0.60, 1), shadow=(0, 0, 0, 0.6),
            align=TextNode.ACenter,
            font=_ui_font, mayChange=True, parent=self._frame,
        )

    # ────────────────────────────────────────────────────────────────────────
    def _create_key_label(self, text, x, z):
        DirectFrame(
            frameColor=(0.54, 0.70, 0.84, 0.70),
            frameSize=(-0.027, 0.027, -0.033, 0.033),
            pos=(x, 0, z), parent=self._frame,
        )
        DirectFrame(
            frameColor=(0.05, 0.09, 0.18, 0.96),
            frameSize=(-0.024, 0.024, -0.030, 0.030),
            pos=(x, 0, z), parent=self._frame,
        )
        OnscreenText(
            text=text,
            pos=(x, z - 0.017), scale=0.042,
            fg=(0.94, 0.97, 1.00, 1),
            shadow=(0, 0, 0, 0.8), shadowOffset=(0.002, -0.002),
            align=TextNode.ACenter,
            font=self._ui_font,
            parent=self._frame,
        )

    def _create_mouse_label(self, x, z):
        OnscreenText(
            text=FA_MOUSE,
            pos=(x, z - 0.020), scale=0.060,
            fg=(0.90, 0.96, 1.00, 1),
            shadow=(0.10, 0.80, 1.00, 0.75), shadowOffset=(0.002, -0.002),
            align=TextNode.ACenter,
            font=self._icon_font,
            parent=self._frame,
        )

    def _create_menu_button(self, text, icon, pos, width, height, accent,
                            accent_hot, fill, fill_hot, text_scale,
                            icon_scale, command):
        x0, x1 = -width / 2.0, width / 2.0
        y0, y1 = -height / 2.0, height / 2.0

        glow = DirectFrame(
            frameColor=(accent[0], accent[1], accent[2], 0.14),
            frameSize=(x0 - 0.014, x1 + 0.014, y0 - 0.014, y1 + 0.014),
            pos=pos, parent=self._frame,
        )
        border = DirectFrame(
            frameColor=accent,
            frameSize=(x0 - 0.006, x1 + 0.006, y0 - 0.006, y1 + 0.006),
            pos=pos, parent=self._frame,
        )
        face = DirectFrame(
            frameColor=fill,
            frameSize=(x0, x1, y0, y1),
            pos=pos, parent=self._frame,
        )
        shine = DirectFrame(
            frameColor=(1, 1, 1, 0.08),
            frameSize=(x0 + 0.025, x1 - 0.025, y1 - height * 0.34, y1 - 0.018),
            pos=pos, parent=self._frame,
        )
        hit = DirectButton(
            text="",
            frameSize=(x0 - 0.014, x1 + 0.014, y0 - 0.014, y1 + 0.014),
            frameColor=(1, 1, 1, 0.01),
            relief=DGG.FLAT,
            command=command,
            pos=pos,
            parent=self._frame,
        )

        icon_text = OnscreenText(
            text=icon,
            pos=(pos[0] + x0 + width * 0.17, pos[2] - icon_scale * 0.38),
            scale=icon_scale,
            fg=(1, 1, 1, 0.96),
            shadow=(accent[0], accent[1], accent[2], 0.85),
            shadowOffset=(0.003, -0.003),
            align=TextNode.ACenter,
            font=self._icon_font,
            parent=self._frame,
        )
        label_text = OnscreenText(
            text=text,
            pos=(pos[0] + width * 0.09, pos[2] - text_scale * 0.43),
            scale=text_scale,
            fg=(1, 1, 1, 1),
            shadow=(0, 0, 0, 0.9),
            shadowOffset=(0.004, -0.004),
            align=TextNode.ACenter,
            font=self._ui_font,
            parent=self._frame,
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

    def show(self, last_score: int = None, last_time: float = None,
             best_time: float = None, is_new_record: bool = False):

        if best_time is not None:
            if is_new_record:
                self._record_text.setText(f"{best_time:.1f}s  —  NOVO RECORDE!")
                self._record_text["fg"] = (1.0, 0.50, 0.0, 1)
            else:
                self._record_text.setText(f"{best_time:.1f} segundos")
                self._record_text["fg"] = (1.0, 0.85, 0.0, 1)
        else:
            self._record_text.setText("Sem recorde — seja o primeiro!")
            self._record_text["fg"] = (0.55, 0.55, 0.55, 1)

        if last_score is not None:
            self._result_text.setText(
                f"Ultima partida:  {last_score} pontos  em  {last_time:.1f}s"
            )
        else:
            self._result_text.setText("")

        self._frame.show()

    def hide(self):
        self._frame.hide()

    def destroy(self):
        self._frame.destroy()
