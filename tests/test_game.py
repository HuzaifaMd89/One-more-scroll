"""Deterministic mechanics and UI checks, using only unittest and Pygame."""
import copy
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import random
import tempfile
import unittest
from pathlib import Path

import pygame
from main import Drop, Game, Round, Storage, PLAYER_Y, W


class MechanicsTests(unittest.TestCase):
    def setUp(self):
        self.r = Round(random.Random(9))
        self.r.spawn_in = 999
        self.r.power_in = 999

    def collide(self, kind):
        self.r.drops.append(Drop(kind, self.r.x, PLAYER_Y, 0, kind))
        self.r.update(0)

    def test_movement_delta_time_and_bounds(self):
        a, b = Round(random.Random(1)), Round(random.Random(1))
        for _ in range(20):
            a.update(0.01, 1)
        for _ in range(10):
            b.update(0.02, 1)
        self.assertAlmostEqual(a.x, b.x)
        for _ in range(100):
            a.update(0.05, 1)
        self.assertEqual(a.x, W - 31)
        for _ in range(100):
            a.update(0.05, -1)
        self.assertEqual(a.x, 31)

    def test_score_combo_cap_and_damage_reset(self):
        for _ in range(7):
            self.collide("focus")
        self.assertEqual(self.r.score, 10 + 20 + 30 + 40 + 50 + 50 + 50)
        self.assertEqual(self.r.combo, 5)
        self.collide("hazard")
        self.assertEqual((self.r.lives, self.r.combo), (2, 1))
        self.assertFalse(self.r.drops)

    def test_overlapping_hazards_only_cost_one_life(self):
        self.r.drops = [Drop("hazard", self.r.x, PLAYER_Y, 0, "SPAM") for _ in range(6)]
        self.r.update(0.01)
        self.assertEqual(self.r.lives, 2)
        for _ in range(27):
            self.r.update(0.05)
        self.collide("hazard")
        self.assertEqual(self.r.lives, 1)

    def test_mute_lasts_three_active_seconds(self):
        self.collide("mute")
        self.assertEqual(self.r.mute, 3)
        self.collide("hazard")
        self.assertEqual(self.r.lives, 3)
        for _ in range(59):
            self.r.update(0.05)
        self.assertGreater(self.r.mute, 0)
        self.r.update(0.05)
        self.assertAlmostEqual(self.r.mute, 0)
        self.collide("hazard")
        self.assertEqual(self.r.lives, 2)

    def test_pause_freezes_everything(self):
        self.collide("mute")
        self.r.paused = True
        before = copy.deepcopy(self.r.__dict__)
        for _ in range(100):
            self.r.update(0.05, 1)
        for key in before:
            if key != "rng":
                self.assertEqual(before[key], self.r.__dict__[key], key)

    def test_round_end_restart_and_cleanup(self):
        self.r.drops.append(Drop("focus", 100, 900, 0, "FOCUS"))
        self.r.update(0.01)
        self.assertFalse(self.r.drops)
        self.r.elapsed = 44.99
        self.r.update(0.02)
        self.assertTrue(self.r.over)
        self.r.reset()
        self.assertEqual((self.r.elapsed, self.r.score, self.r.lives, self.r.combo, self.r.mute), (0, 0, 3, 1, 0))
        self.assertFalse(self.r.drops or self.r.particles or self.r.popups)
        self.r.lives = 1
        self.collide("hazard")
        self.assertTrue(self.r.over)

    def test_large_delta_is_clamped(self):
        self.r.update(300, 1)
        self.assertAlmostEqual(self.r.elapsed, 0.05)
        self.assertAlmostEqual(self.r.x, W / 2 + 18)

    def test_difficulty_ramps_and_objects_stay_bounded(self):
        r = Round(random.Random(3))
        for _ in range(900):
            r.invulnerable = 10
            r.update(0.05)
            self.assertLess(len(r.drops), 24)
        self.assertTrue(r.over)
        self.assertGreater(max(d.speed for d in r.drops), 260)


class StorageTests(unittest.TestCase):
    def test_missing_corrupt_invalid_and_roundtrip(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            path = Path(directory) / "best.json"
            store = Storage(path)
            self.assertEqual(store.load(), 0)
            store.save(170)
            self.assertEqual(Storage(path).load(), 170)
            for data in ('broken', '{"best": -1}', '{"best": true}', '{"best": "999"}', '[]'):
                path.write_text(data)
                self.assertEqual(Storage(path).load(), 0)

    def test_unwritable_storage_does_not_crash(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            store = Storage(Path(directory))
            store.save(20)
            self.assertFalse(store.available)


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.g = Game()

    def tearDown(self):
        pygame.quit()

    def test_focus_loss_clears_keys_and_touch_and_pauses(self):
        self.g.start()
        self.g.keys.add(pygame.K_a)
        self.g.pointers[123] = 1
        self.g.event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertTrue(self.g.round.paused)
        self.assertFalse(self.g.keys or self.g.pointers)
        self.g.action("resume")
        self.assertTrue(self.g.round.paused)
        self.g.event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.g.action("resume")
        self.assertFalse(self.g.round.paused)

    def test_scaling_mouse_touch_and_menu(self):
        self.g.screen = pygame.display.set_mode((1080, 900), pygame.RESIZABLE)
        self.g.draw()
        rect = self.g.viewport
        self.assertAlmostEqual(self.g.logical(rect.center)[0], W / 2, delta=1)
        self.g.start()
        self.g.draw()
        self.g.pointer_down(7, (100, 755))
        self.g.update(0.05)
        self.assertLess(self.g.round.x, W / 2)
        self.g.event(pygame.event.Event(pygame.FINGERUP, finger_id=7))
        self.assertFalse(self.g.pointers)
        self.g.pause()
        self.g.draw()
        self.assertNotIn("pause", self.g.buttons)
        self.g.action("menu")
        self.g.draw()
        self.assertIn("play", self.g.buttons)

    def test_draw_all_screens_and_restart_preserves_best(self):
        self.g.best = 700
        self.g.draw()
        self.g.start()
        self.g.round.drops = [Drop(kind, 100 + i * 150, 300, 0, label) for i, (kind, label) in enumerate((("focus", "FOCUS"), ("hazard", "CLICKBAIT"), ("mute", "MUTE")))]
        self.g.draw()
        self.g.state = "over"
        self.g.draw()
        self.g.action("again")
        self.assertEqual(self.g.best, 700)
        self.assertEqual(self.g.round.score, 0)


if __name__ == "__main__":
    unittest.main()
