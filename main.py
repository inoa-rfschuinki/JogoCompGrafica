"""
Jogo 3D de Coleta - Trabalho de Computacao Grafica
Desenvolvido com Python + Panda3D

Controles:
  W / S        - Mover para frente / tras
  A / D        - Rotacionar (girar) o jogador
  Mouse        - Controlar camera (pitch/yaw)
  ESC          - Voltar ao menu
"""

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import (
    AmbientLight, DirectionalLight,
    CollisionTraverser, CollisionHandlerEvent, CollisionHandlerPusher,
    WindowProperties, AntialiasAttrib,
    Fog,
    Vec4, Vec3
)
from panda3d.core import loadPrcFileData
import sys
import json

loadPrcFileData("", "window-title Coletor 3D - Computacao Grafica")
loadPrcFileData("", "win-size 1280 720")
loadPrcFileData("", "sync-video 0")

from player import Player
from collectibles import CollectibleManager
from obstacles import ObstacleManager
from hud import HUD
from scene import Scene
from menu import Menu


class Game(ShowBase):
    def __init__(self):
        super().__init__()

        self.disableMouse()

        self.camLens.setNear(0.1)
        self.camLens.setFar(1000)
        self.camLens.setFov(75)

        self.render.setAntialias(AntialiasAttrib.MAuto)
        self.setBackgroundColor(0.08, 0.10, 0.20, 1)

        self._setup_lighting()

        self._game_running = False
        self.scene = None
        self.player = None
        self.collectible_manager = None
        self.obstacle_manager = None
        self.hud = None

        self.accept("escape", self._on_escape)

        self._menu = Menu(self, on_start=self._start_game, on_quit=self._quit)
        self._menu.show(best_time=self._load_best_time())

    def _setup_lighting(self):
        ambient = AmbientLight("ambient_light")
        ambient.setColor(Vec4(0.28, 0.32, 0.40, 1))
        self.render.setLight(self.render.attachNewNode(ambient))

        sun = DirectionalLight("sun_light")
        sun.setColor(Vec4(1.0, 0.92, 0.75, 1))
        sun.setDirection(Vec3(-1.5, -2.5, -3))
        self.render.setLight(self.render.attachNewNode(sun))

        sky_fill = DirectionalLight("sky_fill")
        sky_fill.setColor(Vec4(0.20, 0.30, 0.55, 1))
        sky_fill.setDirection(Vec3(0.5, 0.5, -1))
        self.render.setLight(self.render.attachNewNode(sky_fill))

        fill = DirectionalLight("fill_light")
        fill.setColor(Vec4(0.18, 0.22, 0.28, 1))
        fill.setDirection(Vec3(1.5, 2.5, -1))
        self.render.setLight(self.render.attachNewNode(fill))

    _SCORES_FILE = "scores.json"

    def _load_best_time(self) -> float | None:
        try:
            with open(self._SCORES_FILE) as f:
                return json.load(f).get("best_time")
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    def _update_best_time(self, time: float) -> bool:
        """Salva o tempo se for novo recorde. Retorna True se bateu o recorde."""
        best = self._load_best_time()
        if best is None or time < best:
            with open(self._SCORES_FILE, "w") as f:
                json.dump({"best_time": round(time, 2)}, f)
            return True
        return False

    def _start_game(self):
        self._menu.hide()
        self._cleanup_game()

        self.setBackgroundColor(0.52, 0.73, 0.95, 1)

        self.cTrav = CollisionTraverser("main_traverser")
        self.collision_handler = CollisionHandlerEvent()
        self.collision_handler.addInPattern("%fn-into-%in")

        self.pusher = CollisionHandlerPusher()
        self.pusher.setHorizontal(True)

        # Névoa exponencial para profundidade atmosférica
        fog = Fog("scene_fog")
        fog.setColor(0.62, 0.80, 0.95)
        fog.setExpDensity(0.007)
        self.render.setFog(fog)

        self.scene = Scene(self.render, self.loader)
        self.player = Player(self, self.camera, self.render, self.pusher)
        self.collectible_manager = CollectibleManager(
            self.render, self.loader, self.cTrav, self.collision_handler
        )
        self.obstacle_manager = ObstacleManager(self.render)
        self.hud = HUD(self)

        self._game_running = True
        self.accept("player_collect_sphere-into-collectible_sphere", self._on_collect)
        self.accept("player_obstacle_sphere-into-obstacle_sphere", self._on_obstacle_hit)
        self._capture_mouse()
        self.taskMgr.add(self._update, "update_task")

    def _cleanup_game(self):
        self._game_running = False
        self.taskMgr.remove("update_task")
        self.ignore("player_collect_sphere-into-collectible_sphere")
        self.ignore("player_collect_sphere-into-obstacle_sphere")

        if self.hud:
            self.hud.destroy()
            self.hud = None
        if self.player:
            self.player.destroy(self.camera, self.render)
            self.player = None
        if self.scene:
            self.scene.destroy()
            self.scene = None
        if self.collectible_manager:
            self.collectible_manager.destroy()
            self.collectible_manager = None
        if self.obstacle_manager:
            self.obstacle_manager.destroy()
            self.obstacle_manager = None
        self.render.clearFog()

    def _go_to_menu(self):
        score = self.hud.score        if self.hud else None
        time  = self.hud.elapsed_time if self.hud else None
        self._cleanup_game()
        self._free_mouse()
        self.setBackgroundColor(0.08, 0.10, 0.20, 1)
        self._menu.show(
            last_score=score,
            last_time=time,
            best_time=self._load_best_time(),
        )

    def _update(self, _task):
        if not self._game_running:
            return Task.done
        dt = globalClock.getDt()  # builtin injetado pelo Panda3D ShowBase
        self.cTrav.traverse(self.render)
        self.player.update(dt)
        self.collectible_manager.update(dt)
        self.obstacle_manager.update(dt)
        self.hud.update(dt)
        return Task.cont

    def _on_collect(self, entry):
        if not self._game_running:
            return
        collected = self.collectible_manager.collect(entry.getIntoNodePath())
        if collected:
            self.hud.add_score(10)
            if self.collectible_manager.remaining() == 0:
                self._trigger_victory()

    def _on_obstacle_hit(self, entry):
        if not self._game_running:
            return
        penalty = self.obstacle_manager.try_penalty(entry.getIntoNodePath())
        if penalty:
            self.hud.add_time_penalty(penalty)

    def _trigger_victory(self):
        self._game_running = False
        self.taskMgr.remove("update_task")
        self.ignore("player_collect_sphere-into-collectible_sphere")
        self._free_mouse()

        final_time    = self.hud.elapsed_time
        is_new_record = self._update_best_time(final_time)
        best_time     = self._load_best_time()

        self.hud.show_victory(
            final_score=self.hud.score,
            final_time=final_time,
            best_time=best_time,
            is_new_record=is_new_record,
            on_restart=self._start_game,
            on_menu=self._go_to_menu,
        )

    def _capture_mouse(self):
        props = WindowProperties()
        props.setCursorHidden(True)
        self.win.requestProperties(props)
        self.win.movePointer(0, self.win.getXSize() // 2, self.win.getYSize() // 2)

    def _free_mouse(self):
        props = WindowProperties()
        props.setCursorHidden(False)
        self.win.requestProperties(props)

    def _on_escape(self):
        if self._game_running:
            self._go_to_menu()
        else:
            self._quit()

    def _quit(self):
        self._free_mouse()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
