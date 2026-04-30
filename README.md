# Coletor 3D — Trabalho de Computação Gráfica

Jogo 3D de coleta em terceira pessoa desenvolvido com **Python + Panda3D**.
Toda a geometria do cenário, do personagem e dos coletáveis é
**gerada proceduralmente** em tempo de execução (sem assets externos de
modelo) — apenas uma fonte TrueType (Font Awesome) é distribuída junto.

![Stack](https://img.shields.io/badge/Python-3.9%E2%80%933.11-blue)
![Engine](https://img.shields.io/badge/Panda3D-%E2%89%A51.10.13-success)

---

## Sumário

- [Estrutura do projeto](#estrutura-do-projeto)
- [Dependências](#dependências)
- [Instalação e execução](#instalação-e-execução)
- [Como jogar](#como-jogar)
- [Fluxo do jogo](#fluxo-do-jogo)
- [Conceitos de Computação Gráfica demonstrados](#conceitos-de-computação-gráfica-demonstrados)
- [Descrição técnica dos arquivos](#descrição-técnica-dos-arquivos)

---

## Estrutura do projeto

```
trabalho_compgrafica/
├── main.py             # Ponto de entrada — máquina de estados Menu / Jogo / Pause
├── menu.py             # Menu principal + menu de pause (overlay modal)
├── player.py           # Personagem 3ª pessoa (corpo procedural + câmera orbital)
├── collectibles.py     # Coletáveis normais e bônus (com glow procedural)
├── obstacles.py        # Poças de lama (penalidade de tempo)
├── scene.py            # Cenário (terreno, montanhas, árvores, grama, flores…)
├── hud.py              # HUD (pontos, itens, timer, vitória)
├── ui_art.py           # Texturas procedurais (banners do menu/vitória)
├── fa-solid-900.ttf    # Fonte de ícones (Font Awesome 6 Solid)
├── requirements.txt    # Dependência única: panda3d
├── scores.json         # Recorde persistente (melhor tempo)
└── README.md
```

---

## Dependências

| Pacote   | Versão mínima | Uso                                            |
|----------|---------------|------------------------------------------------|
| panda3d  | 1.10.13       | Render, input, colisão, GUI, fontes, materiais |

Python recomendado: **3.9 – 3.11** (testado em Windows com PowerShell).

---

## Instalação e execução

### 1. Clonar o repositório

```powershell
git clone https://github.com/inoa-rfschuinki/JogoCompGrafica.git
cd JogoCompGrafica
```

### 2. Criar ambiente virtual (recomendado)

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependências

```powershell
pip install -r requirements.txt
```

### 4. Executar

```powershell
python main.py
```

A janela abre em **1280×720** com o menu principal.

---

## Como jogar

### Objetivo

Colete todos os **10 objetos coloridos** espalhados pelo mapa no menor
tempo possível. Quatro **coletáveis bônus** verdes brilhantes também
existem — eles são **opcionais** (não contam para a vitória), mas cada
um remove **−10 segundos** do cronômetro e dá pontos extras.

Cuidado com as **poças de lama** espalhadas: cada vez que pisar em uma,
**+3 segundos** são adicionados ao tempo.

### Controles

| Tecla / Mouse                | Ação                                  |
|------------------------------|----------------------------------------|
| **W** / **S**                | Mover para frente / trás               |
| **A** / **D**                | Girar à esquerda / direita             |
| **Mouse**                    | Olhar (pitch + leve yaw orbital)       |
| **ESC** (durante a partida)  | Abrir / fechar o menu de **pause**     |
| **ESC** (no menu principal)  | Sair do jogo                           |

### Coletáveis

| Tipo                          | Aparência                                        | Efeito                                            |
|-------------------------------|--------------------------------------------------|---------------------------------------------------|
| Normal (10 itens)             | Esfera / cubo / octaedro colorido + anel girando | +10 pts. Necessário para vencer                   |
| **Bônus de tempo** (4 itens)  | Octaedro verde com **3 anéis pulsantes** emissivos | +25 pts e **−10s** no cronômetro. Opcional       |

### Recorde

Ao vencer uma partida, se o tempo total for menor que o recorde
anterior (salvo em `scores.json`), o novo tempo é gravado
automaticamente e o menu principal exibe o recorde atual em
**MELHOR TEMPO**.

---

## Fluxo do jogo

```
                  ┌────────────────────┐
                  │  MENU PRINCIPAL    │
                  │  (banner + recorde)│
                  └─────────┬──────────┘
                            │ JOGAR
                            ▼
        ┌──────────────────────────────────────────┐
        │          PARTIDA EM CURSO                │
        │  (HUD ativo, cronômetro rodando, mouse   │
        │   capturado)                             │
        └──┬─────────────────┬──────────────────┬──┘
           │ ESC             │ todos coletados  │
           ▼                 ▼                  │
   ┌─────────────────┐  ┌──────────────┐        │
   │  MENU DE PAUSE  │  │  VITÓRIA     │        │
   │  • Continuar    │  │  • Reiniciar │        │
   │  • Reiniciar    │  │  • Menu      │        │
   │  • Menu         │  └──────┬───────┘        │
   └─┬───────┬───────┘         │                │
     │       │                 │                │
     │       └── Reiniciar ────┴────────────────┘
     │
     └── Continuar (volta à partida congelada)
```

---

## Conceitos de Computação Gráfica demonstrados

| Conceito | Onde é aplicado |
|----------|-----------------|
| **Geometria procedural** (vértices/normais/UVs gerados em código) | `scene.py` — esferas UV, cilindros, cones, caixas, picos de montanha, tufos de grama, anéis de toro; `player.py` — corpo inteiro; `collectibles.py` — esferas / cubos / octaedros + anéis decorativos |
| **Normais por face / suavizadas** | Caixas e cones têm normais por face (silhueta dura); esferas e cilindros laterais usam normais suavizadas (sombreamento Gouraud-like) |
| **Cor por vértice (vertex color)** | Picos de montanha — gradiente sopé → cume com linha de neve, em formato `V3n3c4` |
| **Coordenadas de textura (UVs) + tiling** | Plano de grama com `_make_textured_plane(divs=48, uv_repeat=…)` em formato `V3n3t2` |
| **Texturas procedurais em RAM** | `_make_grass_texture()` (ruído pixel-a-pixel) e `ui_art.py` (banners do menu / vitória escritos em `bytearray` → `Texture.setRamImage`) |
| **Material Phong** (ambiente + difuso + especular + shininess) | Todos os corpos via `panda3d.core.Material` |
| **Iluminação multi-fonte** | Ambiente + sol direcional (warm) + preenchimento de céu (azul) + contraluz fria — `main.py → _setup_lighting()` |
| **Fog exponencial** | `Fog(setExpDensity=0.007)` aplicado a `render` para profundidade atmosférica |
| **Anti-aliasing** | `render.setAntialias(AntialiasAttrib.MAuto)` |
| **Skybox** | Cubo invertido com `setLightOff()` + `setBin("background", 0)` |
| **Grafo de cena hierárquico** | Player: `pivot → torso/braços/pernas`, com `shoulder_l/r → deltoid/upper_arm/elbow/forearm/wrist/hand` para animação por rotação local |
| **Câmera orbital de 3ª pessoa** | `player.py` — pivot do personagem + braço de câmera (`CAM_DIST=8`, `CAM_HEIGHT`), pitch via mouse com clamp, look-at no torso |
| **Animação procedural de caminhada** | Sin/cos da fase de passo aplicado a quadril e ombro (`±28°`), além de bob vertical do corpo |
| **Animações por seno** (oscilação + rotação) | Coletáveis flutuam (`bob = sin(elapsed * BOB_SPEED + phase) * BOB_AMPLITUDE`) e giram em múltiplos eixos |
| **Sistema de colisão por máscaras** | `BitMask32.bit(N)` separa coletáveis (bit 2), obstáculos (bit 3), árvores (bit 1). Detecção via `CollisionTraverser` + `CollisionHandlerEvent` com padrão `"%fn-into-%in"` |
| **Hitboxes adequadas a cada objeto** | `CollisionCapsule` para troncos de árvore — apenas o cilindro do tronco bloqueia, a copa não; `CollisionSphere` para coletáveis e personagem |
| **Empurrador físico** | `CollisionHandlerPusher` impede o jogador de atravessar troncos |
| **Identificação de instâncias via tags** | Cada coletável grava `setTag('cid', str(idx))` no nó de colisão; o handler recupera com `getTag('cid')` |
| **Lente perspectiva customizada** | `setNear(0.1)`, `setFar(1000)`, `setFov(75)` |
| **HUD 2D sobreposto em aspect2d** | `OnscreenText`, `DirectFrame`, `DirectButton`, `TransparencyAttrib.MAlpha` em coordenadas normalizadas |
| **Texto com fonte TTF + ícones glifo** | Impact / Arial Bold + Font Awesome 6 Solid (`fa-solid-900.ttf`) |
| **Persistência simples (JSON)** | Recorde de melhor tempo em `scores.json` |
| **Máquina de estados** | `main.py` separa Menu / Partida / Pause / Vitória, com `_cleanup_game()` desmontando subsistemas para evitar leaks |

---

## Descrição técnica dos arquivos

### `main.py`

Classe `Game` (herda `ShowBase`). Centraliza a **máquina de estados**:
menu → jogo → (pause / vitória) → menu. Configura iluminação, fog,
captura/liberação do mouse e o ciclo de vida completo dos subsistemas
(`_start_game`, `_cleanup_game`, `_pause_game`, `_resume_game`,
`_trigger_victory`). O ESC alterna pause durante a partida e sai do
jogo no menu principal.

### `menu.py`

Duas classes:

- **`Menu`** — tela inicial em tela cheia. Banner panorâmico
  procedural (gerado por `ui_art.make_game_artwork`) cobre todo o
  fundo, com cortina suave para legibilidade. Painel central com
  bordas em camadas (cyan + escuro + cyan), títulos em Impact, ícones
  Font Awesome para Objetivo / Controles / Melhor tempo, e botões
  **Jogar** / **Sair**.
- **`PauseMenu`** — overlay modal acionado com ESC. Cortina escura +
  painel compacto com 3 botões: **Continuar** (verde), **Reiniciar**
  (azul) e **Menu Principal** (laranja).

### `player.py`

Classe `Player`. Personagem totalmente procedural, organizado em uma
hierarquia de NodePaths:

```
pivot ─┬─ pelvis, belt, torso, shoulder_pad, collar, neck, head, hair, eyes…
       ├─ shoulder_l ── deltoid, upper_arm, elbow, forearm, wrist, hand, thumb
       ├─ shoulder_r ── (idem)
       ├─ hip_l ── thigh, knee, shin, ankle, sole, toe, heel
       └─ hip_r ── (idem)
```

Câmera orbital de 3ª pessoa (`CAM_DIST=8`, foco no torso). Movimento
WASD com `_handle_movement()` e clamp a ±45 nos eixos X/Y. Animação de
caminhada procedural via `_animate_walk()` aplicando `sin(phase)*28°`
nas juntas dos quadris e ombros.

### `scene.py`

Classe `Scene` constrói o mundo. Constantes principais:

- `MAP_SIZE = 100` (lado do gramado).
- `GRASS_TUFT_COUNT = 600` (tufos médios) + `GRASS_BLADE_COUNT = 2200`
  (gramíneas micro espalhadas por toda a área, inclusive nos caminhos).
- `FLOWER_COUNT = 110`, `PEBBLE_COUNT = 70`.
- 5 fileiras de **picos de montanha** procedurais
  (`_make_mountain_peak`) com offset negativo na primeira fileira para
  encaixar na grama; calotas de neve coloridas via cor por vértice.
- **40 árvores** com tronco cilíndrico levemente inclinado, base/raiz e
  copa formada por 8–12 esferas de tamanho aleatório (folhagem
  orgânica). Hitbox = cápsula do tronco apenas.
- Plano de grama texturizado (textura procedural ruidosa), caminhos de
  terra em cruz, sub-solo escuro nas bordas.
- Skybox de cubo invertido com `setLightOff()`.

### `collectibles.py`

- `Collectible` — instância individual com forma sortida (esfera /
  cubo / octaedro), anel decorativo girando em eixo perpendicular,
  oscilação senoidal vertical e rotação contínua. Aceita
  `kind="normal"` ou `kind="time_bonus"`.
- Itens **bônus** ganham aura de 3 anéis emissivos verdes que pulsam
  de tamanho em ritmos diferentes.
- `CollectibleManager` instancia **10 itens normais** + **4 bônus** em
  posições fixas. `collect()` retorna a string do tipo coletado;
  `remaining()` ignora os bônus para que a vitória dependa apenas dos
  obrigatórios.

### `obstacles.py`

Poças de lama com colisor por esfera. Ao atravessar, dispara penalidade
de tempo via evento de colisão (handler `try_penalty`).

### `hud.py`

Card de status no canto superior esquerdo (PONTOS, ITENS, TEMPO) com
cabeçalho cyan e linhas em ícones tipográficos (`$`, `*`, `T`). Métodos
`add_score`, `add_time_penalty` (texto vermelho flutuante "+3s"),
`add_time_bonus` (texto verde "−10s"), e `show_victory()` que exibe o
banner de vitória (gerado por `ui_art.make_victory_artwork`) com tempo
final, recorde e botões.

### `ui_art.py`

Geradores procedurais de **texturas em RAM** (sem arquivos):

- `make_game_artwork(width=960, height=576)` — banner do menu com 5
  camadas de montanhas (parallax), sol com halo radial e reflexo no
  horizonte, nuvens, árvores em silhueta, grama densa com flores e
  coletáveis dourados.
- `make_victory_artwork(width=512, height=140)` — céu noturno
  estrelado, halo dourado e silhueta de troféu.

Ambas escrevem um `bytearray` linha-a-linha (RGBA8), aplicam vinheta,
fazem flip vertical (`_flip_buffer_vertical`) e entregam um
`panda3d.core.Texture` via `setRamImage`.

---

## Créditos

Trabalho da disciplina de **Computação Gráfica**.
Engine: [Panda3D](https://www.panda3d.org/).
Ícones: [Font Awesome 6 Free Solid](https://fontawesome.com/) (SIL OFL).
