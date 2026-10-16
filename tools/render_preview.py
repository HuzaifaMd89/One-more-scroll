"""Render real game screens without opening a window, for visual QA."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from main import Game, Drop

output = Path(__file__).resolve().parents[1] / "build" / "previews"
output.mkdir(parents=True, exist_ok=True)
game = Game()
game.draw()
pygame.image.save(game.canvas, output / "menu.png")
game.start()
game.round.drops = [Drop("focus", 130, 265, 200, "FOCUS"), Drop("hazard", 370, 320, 200, "CLICKBAIT"), Drop("hazard", 160, 440, 200, "REELS"), Drop("mute", 390, 515, 200, "MUTE")]
game.round.score = 230
game.round.combo = 5
game.round.elapsed = 21
game.draw()
pygame.image.save(game.canvas, output / "play.png")
game.pause()
game.draw()
pygame.image.save(game.canvas, output / "pause.png")
game.state = "over"
game.draw()
pygame.image.save(game.canvas, output / "over.png")
pygame.quit()
print(output)
