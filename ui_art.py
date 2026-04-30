"""
ui_art.py — Geração procedural de imagens decorativas usadas pela UI.

As texturas são montadas em memória (sem dependência de arquivos externos),
combinando várias camadas de pixels: gradiente de céu, silhuetas de
montanhas, sol, grama no primeiro plano e detalhes (coins/sparkles).
"""

import math
import random

from panda3d.core import Texture


def _lerp(a, b, t):
    return a + (b - a) * t


def _mix(c1, c2, t):
    return (
        _lerp(c1[0], c2[0], t),
        _lerp(c1[1], c2[1], t),
        _lerp(c1[2], c2[2], t),
    )


def _put(buf, w, x, y, color):
    if 0 <= x < w and 0 <= y < len(buf) // (w * 4):
        i = (y * w + x) * 4
        buf[i + 0] = max(0, min(255, int(color[0] * 255)))
        buf[i + 1] = max(0, min(255, int(color[1] * 255)))
        buf[i + 2] = max(0, min(255, int(color[2] * 255)))
        buf[i + 3] = 255


def _fill_rect(buf, w, h, x0, y0, x1, y1, color):
    for y in range(max(0, y0), min(h, y1)):
        for x in range(max(0, x0), min(w, x1)):
            _put(buf, w, x, y, color)


def _flip_buffer_vertical(buf: bytearray, w: int, h: int):
    """Inverte o buffer no eixo Y (Panda3D espera origem no topo).
    Convenção das funções de geração: y=0 corresponde à base da imagem.
    """
    row_bytes = w * 4
    for y in range(h // 2):
        top = y * row_bytes
        bot = (h - 1 - y) * row_bytes
        tmp = buf[top:top + row_bytes]
        buf[top:top + row_bytes] = buf[bot:bot + row_bytes]
        buf[bot:bot + row_bytes] = tmp


def _disc(buf, w, h, cx, cy, r, color, soft=2):
    for y in range(max(0, cy - r - soft), min(h, cy + r + soft)):
        for x in range(max(0, cx - r - soft), min(w, cx + r + soft)):
            d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if d <= r:
                _put(buf, w, x, y, color)
            elif d <= r + soft:
                t = 1.0 - (d - r) / soft
                # mistura simples com o pixel existente
                i = (y * w + x) * 4
                base = (buf[i] / 255, buf[i + 1] / 255, buf[i + 2] / 255)
                _put(buf, w, x, y, _mix(base, color, t * 0.85))


def make_game_artwork(width: int = 960, height: int = 576,
                      seed: int = 7) -> Texture:
    """
    Banner panorâmico estilizado representando o jogo.
    Composição:
        - Céu com gradiente vibrante e nuvens em pinceladas finas.
        - Sol baixo com halo radial e raios sutis.
        - 5 camadas de montanhas (parallax) com calotas de neve.
        - Linha de árvores em silhueta na base das montanhas próximas.
        - Faixa de grama densa em primeiro plano.
        - Coletáveis dourados flutuando com brilho em estrela.
        - Vinheta sutil nas bordas para foco no centro.
    """
    rng = random.Random(seed)
    buf = bytearray(width * height * 4)

    # ── Céu (gradiente vertical em 3 paradas) ────────────────────────────
    sky_top = (0.06, 0.10, 0.34)
    sky_mid = (0.55, 0.38, 0.62)
    sky_low = (1.00, 0.62, 0.30)
    horizon = int(height * 0.60)

    for y in range(height):
        if y < horizon:
            inv = 1.0 - y / max(1, horizon - 1)
            if inv < 0.55:
                color = _mix(sky_low, sky_mid, inv / 0.55)
            else:
                color = _mix(sky_mid, sky_top, (inv - 0.55) / 0.45)
        else:
            color = (0.18, 0.40, 0.16)
        for x in range(width):
            _put(buf, width, x, y, color)

    # ── Sol no horizonte ────────────────────────────────────────────────
    sun_cx = int(width * 0.74)
    sun_cy = horizon - int(height * 0.04)
    # Halo externo (rosa/dourado bem suave)
    for k, (rad_f, col) in enumerate((
        (0.32, (1.00, 0.55, 0.30)),
        (0.24, (1.00, 0.72, 0.40)),
        (0.18, (1.00, 0.88, 0.55)),
        (0.12, (1.00, 0.96, 0.78)),
        (0.07, (1.00, 1.00, 0.92)),
    )):
        _disc(buf, width, height, sun_cx, sun_cy,
              int(height * rad_f), col,
              soft=int(height * 0.04) if k < 3 else 2)
    # Reflexo horizontal sobre o horizonte (faixa fina)
    for x in range(sun_cx - int(width * 0.18),
                   sun_cx + int(width * 0.18)):
        if 0 <= x < width:
            t = 1.0 - abs(x - sun_cx) / (width * 0.18)
            for dy in range(-2, 3):
                yy = sun_cy + dy
                if 0 <= yy < height:
                    i = (yy * width + x) * 4
                    base = (buf[i] / 255, buf[i + 1] / 255, buf[i + 2] / 255)
                    c = _mix(base, (1.0, 0.95, 0.70), t * 0.45)
                    _put(buf, width, x, yy, c)

    # ── Nuvens em pinceladas elípticas ──────────────────────────────────
    for _ in range(12):
        cx = rng.randint(0, width - 1)
        cy = rng.randint(int(height * 0.08), int(height * 0.45))
        cw = rng.randint(int(width * 0.08), int(width * 0.18))
        ch = rng.randint(int(height * 0.012), int(height * 0.030))
        bright = rng.uniform(0.85, 1.0)
        for y in range(max(0, cy - ch), min(height, cy + ch + 1)):
            for x in range(max(0, cx - cw), min(width, cx + cw + 1)):
                dx = (x - cx) / cw
                dy = (y - cy) / ch
                d2 = dx * dx + dy * dy
                if d2 < 1.0:
                    t = (1.0 - d2) * 0.55
                    i = (y * width + x) * 4
                    base = (buf[i] / 255, buf[i + 1] / 255, buf[i + 2] / 255)
                    cloud = (bright, bright * 0.95, bright * 0.92)
                    _put(buf, width, x, y, _mix(base, cloud, t))

    # ── Camadas de montanhas (5, parallax do mais distante p/ próximo) ──
    def draw_range(base_y, peaks, h_min, h_max, color, snow_color=None,
                   snow_thresh=0.75, jitter=1.5):
        seg_w = width / peaks
        silhouette = [base_y] * width
        for i in range(peaks + 2):
            cx = int(seg_w * (i - 0.5) + rng.uniform(-seg_w * 0.30,
                                                     seg_w * 0.30))
            ph = rng.randint(h_min, h_max)
            half_w = int(seg_w * rng.uniform(0.55, 1.05))
            for x in range(max(0, cx - half_w), min(width, cx + half_w)):
                d = abs(x - cx)
                hloc = int(ph * (1.0 - d / max(1, half_w)))
                hloc += int(math.sin(x * 0.32 + i * 1.7) * jitter)
                hloc += int(math.sin(x * 1.10 + i * 0.5) * jitter * 0.4)
                top_y = base_y - hloc
                if top_y < silhouette[x]:
                    silhouette[x] = top_y

        for x in range(width):
            top_y = silhouette[x]
            for y in range(top_y, base_y):
                # leve sombreamento vertical (mais escuro no sopé)
                t = (y - top_y) / max(1, base_y - top_y)
                shade = _mix(color,
                             (color[0] * 0.78, color[1] * 0.78, color[2] * 0.82),
                             t * 0.55)
                _put(buf, width, x, y, shade)
            if snow_color is not None:
                local_h = base_y - top_y
                if local_h > 0:
                    snow_h = int(local_h * (1.0 - snow_thresh))
                    for y in range(top_y, top_y + snow_h):
                        t = 1.0 - (y - top_y) / max(1, snow_h)
                        c = _mix(color, snow_color, 0.55 + 0.45 * t)
                        _put(buf, width, x, y, c)

    # 1ª camada — quase fundida ao céu
    draw_range(horizon + int(height * 0.00), peaks=10,
               h_min=int(height * 0.07), h_max=int(height * 0.16),
               color=(0.42, 0.40, 0.58),
               snow_color=(0.96, 0.97, 1.00), snow_thresh=0.68)
    # 2ª camada
    draw_range(horizon + int(height * 0.04), peaks=8,
               h_min=int(height * 0.10), h_max=int(height * 0.22),
               color=(0.32, 0.30, 0.48),
               snow_color=(0.94, 0.96, 1.00), snow_thresh=0.74)
    # 3ª camada (intermediária)
    draw_range(horizon + int(height * 0.08), peaks=6,
               h_min=int(height * 0.13), h_max=int(height * 0.26),
               color=(0.24, 0.22, 0.36),
               snow_color=(0.92, 0.94, 0.98), snow_thresh=0.78)
    # 4ª camada
    draw_range(horizon + int(height * 0.13), peaks=5,
               h_min=int(height * 0.10), h_max=int(height * 0.20),
               color=(0.16, 0.16, 0.26),
               snow_color=None)
    # 5ª camada — colina escura próxima
    draw_range(horizon + int(height * 0.18), peaks=4,
               h_min=int(height * 0.06), h_max=int(height * 0.12),
               color=(0.10, 0.12, 0.10),
               snow_color=None, jitter=2.0)

    # ── Árvores em silhueta na base das colinas ─────────────────────────
    tree_base_y = horizon + int(height * 0.18)
    for _ in range(width // 14):
        x = rng.randint(0, width - 1)
        h_tree = rng.randint(int(height * 0.025), int(height * 0.060))
        tw = max(1, h_tree // 4)
        # tronco
        for y in range(tree_base_y - h_tree, tree_base_y):
            _put(buf, width, x, y, (0.10, 0.07, 0.05))
        # copa triangular
        crown_h = h_tree
        for k in range(crown_h):
            half = max(1, int((1.0 - k / crown_h) * tw * 2.5))
            yy = tree_base_y - h_tree - crown_h + k
            for dx in range(-half, half + 1):
                xx = x + dx
                if 0 <= xx < width and 0 <= yy < height:
                    _put(buf, width, xx, yy, (0.08, 0.18, 0.08))

    # ── Faixa de grama em primeiro plano ────────────────────────────────
    grass_start = horizon + int(height * 0.20)
    for y in range(grass_start, height):
        t = (y - grass_start) / max(1, height - grass_start)
        base = _mix((0.20, 0.45, 0.18), (0.08, 0.18, 0.06), t)
        for x in range(width):
            n = (math.sin(x * 0.31 + y * 0.7) +
                 math.sin(x * 0.13 - y * 0.21)) * 0.030
            c = (base[0] + n, base[1] + n * 1.4, base[2] + n)
            _put(buf, width, x, y, c)

    # Tufos densos de grama
    for _ in range(width // 2):
        x = rng.randint(0, width - 1)
        y = rng.randint(grass_start + 4, height - 2)
        bh = rng.randint(2, 6)
        col = (rng.uniform(0.30, 0.55),
               rng.uniform(0.55, 0.90),
               rng.uniform(0.10, 0.28))
        for k in range(bh):
            _put(buf, width, x, y - k, col)
        # alguns tufos com 3 lâminas
        if rng.random() < 0.4:
            for k in range(bh - 1):
                _put(buf, width, x - 1, y - k, col)
                _put(buf, width, x + 1, y - k, col)

    # Pequenas flores no gramado
    for _ in range(width // 18):
        x = rng.randint(0, width - 1)
        y = rng.randint(grass_start + 6, height - 4)
        flower = rng.choice([
            (1.00, 0.92, 0.30),
            (0.95, 0.40, 0.55),
            (0.55, 0.30, 0.85),
            (0.95, 0.95, 0.95),
        ])
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            xx, yy = x + dx, y + dy
            if 0 <= xx < width and 0 <= yy < height:
                _put(buf, width, xx, yy, flower)

    # ── Coletáveis dourados (estrelas pequenas brilhando) ───────────────
    for _ in range(11):
        cx = rng.randint(int(width * 0.05), int(width * 0.95))
        cy = rng.randint(int(height * 0.20), horizon - int(height * 0.04))
        r = rng.randint(2, 4)
        _disc(buf, width, height, cx, cy, r + 2,
              (1.00, 0.78, 0.20), soft=1)
        _disc(buf, width, height, cx, cy, r,
              (1.00, 0.97, 0.55), soft=1)
        for k in range(1, r + 4):
            _put(buf, width, cx + k, cy, (1.0, 0.95, 0.55))
            _put(buf, width, cx - k, cy, (1.0, 0.95, 0.55))
            _put(buf, width, cx, cy + k, (1.0, 0.95, 0.55))
            _put(buf, width, cx, cy - k, (1.0, 0.95, 0.55))

    # ── Vinheta de bordas ───────────────────────────────────────────────
    cx = width / 2
    cy = height / 2
    rmax = math.sqrt(cx * cx + cy * cy)
    for y in range(height):
        for x in range(width):
            d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / rmax
            if d > 0.74:
                t = min(1.0, (d - 0.74) / 0.26) * 0.55
                i = (y * width + x) * 4
                buf[i]     = int(buf[i]     * (1.0 - t))
                buf[i + 1] = int(buf[i + 1] * (1.0 - t))
                buf[i + 2] = int(buf[i + 2] * (1.0 - t))

    _flip_buffer_vertical(buf, width, height)
    tex = Texture("menu_artwork")
    tex.setup2dTexture(width, height, Texture.TUnsignedByte, Texture.FRgba8)
    tex.setRamImage(bytes(buf))
    tex.setMagfilter(Texture.FTLinear)
    tex.setMinfilter(Texture.FTLinearMipmapLinear)
    tex.setWrapU(Texture.WMClamp)
    tex.setWrapV(Texture.WMClamp)
    return tex


def make_victory_artwork(width: int = 512, height: int = 140,
                         seed: int = 19) -> Texture:
    """
    Banner para a tela de vitória — paleta dourada sobre céu noturno
    estrelado, com troféu silhueta no centro.
    """
    rng = random.Random(seed)
    buf = bytearray(width * height * 4)

    # Gradiente noturno
    sky_top = (0.04, 0.05, 0.18)
    sky_bot = (0.32, 0.18, 0.40)
    for y in range(height):
        t = y / max(1, height - 1)
        c = _mix(sky_bot, sky_top, t)
        for x in range(width):
            _put(buf, width, x, y, c)

    # Estrelas
    for _ in range(width // 3):
        x = rng.randint(0, width - 1)
        y = rng.randint(int(height * 0.15), height - 1)
        b = rng.uniform(0.7, 1.0)
        _put(buf, width, x, y, (b, b, b * 0.95))
        if rng.random() < 0.25:
            _put(buf, width, x + 1, y, (b * 0.7, b * 0.7, b * 0.65))
            _put(buf, width, x, y + 1, (b * 0.7, b * 0.7, b * 0.65))

    # Halo dourado central
    cx, cy = width // 2, int(height * 0.42)
    for y in range(height):
        for x in range(width):
            d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            r_in = int(min(width, height) * 0.30)
            if d < r_in:
                t = 1.0 - d / r_in
                i = (y * width + x) * 4
                base = (buf[i] / 255, buf[i + 1] / 255, buf[i + 2] / 255)
                glow = (1.00, 0.78, 0.25)
                c = _mix(base, glow, t * 0.55)
                _put(buf, width, x, y, c)

    # Silhueta esquemática de troféu (taça)
    gold = (1.00, 0.84, 0.20)
    cup_top = cy - int(height * 0.20)
    cup_bot = cy + int(height * 0.05)
    cup_w   = int(width * 0.10)
    for y in range(cup_top, cup_bot):
        t = (y - cup_top) / max(1, cup_bot - cup_top)
        w_local = int(cup_w * (1.0 - 0.4 * t))
        for x in range(cx - w_local, cx + w_local):
            _put(buf, width, x, y, gold)
    # base
    base_y0 = cup_bot
    base_y1 = cup_bot + int(height * 0.05)
    for y in range(base_y0, base_y1):
        for x in range(cx - int(cup_w * 0.6), cx + int(cup_w * 0.6)):
            _put(buf, width, x, y, gold)
    # pé
    foot_y0 = base_y1
    foot_y1 = foot_y0 + int(height * 0.06)
    for y in range(foot_y0, foot_y1):
        for x in range(cx - int(cup_w * 1.1), cx + int(cup_w * 1.1)):
            _put(buf, width, x, y, gold)
    # alças
    for k in range(int(cup_w * 0.6)):
        y = cup_top + int((cup_bot - cup_top) * 0.25) + k // 2
        _put(buf, width, cx - cup_w - k, y, gold)
        _put(buf, width, cx + cup_w + k, y, gold)

    _flip_buffer_vertical(buf, width, height)
    tex = Texture("victory_artwork")
    tex.setup2dTexture(width, height, Texture.TUnsignedByte, Texture.FRgba8)
    tex.setRamImage(bytes(buf))
    tex.setMagfilter(Texture.FTLinear)
    tex.setMinfilter(Texture.FTLinearMipmapLinear)
    tex.setWrapU(Texture.WMClamp)
    tex.setWrapV(Texture.WMClamp)
    return tex
