"""The staged-entry HUD strip + multi-state keyboard painting (pygame-only).

PyGame has no widgets, so the HUD is hand-drawn rects + pygame.font text with a manual
rect->action hit-test. Geometry and hit-testing of the piano itself are reused from the
library (pypiano_2607.gui); only the PAINTING is redone here, because the spike needs more
key states (live-held / staged / just-fired) than the base widget's single pressed-colour
render supports. Visuals only -- no second acoustic authority lives here.
"""
from __future__ import annotations

import pygame

# --- palette -----------------------------------------------------------------
BG            = (24, 24, 28)
PANEL         = (30, 30, 36)
WHITE_KEY     = (238, 238, 234)
BLACK_KEY     = (18, 18, 20)
BORDER        = (70, 70, 76)
LIVE          = (120, 180, 235)   # live-held (blue)
STAGED        = (232, 172, 74)    # staged (amber)
FLASH         = (120, 205, 130)   # just-fired (green)
TEXT          = (232, 232, 232)
TEXT_MUTED    = (150, 150, 158)
TEXT_ON_LIGHT = (40, 40, 44)
BTN           = (52, 52, 60)
BTN_BORDER    = (92, 92, 104)


class Hud:
    """The top strip: mode toggle, tuning badge, pending tray, action buttons, preset,
    hint. Button rects are fixed at construction so draw() and hit() always agree."""

    def __init__(self, width: int, hud_h: int, margin: int):
        self.width = width
        self.hud_h = hud_h
        self.margin = margin
        x = margin
        self.mode_rect    = pygame.Rect(x, 14, 168, 40)
        by = 100                                              # staged-mode action row
        self.play_rect    = pygame.Rect(x,       by, 168, 38)
        self.save_rect    = pygame.Rect(x + 180, by, 156, 38)
        self.release_rect = pygame.Rect(x + 348, by, 120, 38)
        self._fonts = None

    def fonts(self):
        if self._fonts is None:
            self._fonts = {
                "big":   pygame.font.Font(None, 34),
                "mid":   pygame.font.Font(None, 26),
                "small": pygame.font.Font(None, 22),
            }
        return self._fonts

    def hit(self, pos, mode):
        """Which HUD action (if any) is under pos, honouring what's visible in `mode`."""
        if self.mode_rect.collidepoint(pos):
            return "mode"
        if mode == "staged":
            if self.play_rect.collidepoint(pos):    return "play"
            if self.save_rect.collidepoint(pos):    return "save"
            if self.release_rect.collidepoint(pos): return "release"
        return None

    def _button(self, screen, rect, label, font, *, accent=None, muted=False):
        pygame.draw.rect(screen, accent or BTN, rect, border_radius=6)
        pygame.draw.rect(screen, BTN_BORDER, rect, 1, border_radius=6)
        col = TEXT_MUTED if muted else (TEXT_ON_LIGHT if accent else TEXT)
        surf = font.render(label, True, col)
        screen.blit(surf, surf.get_rect(center=rect.center))

    def draw(self, screen, *, mode, staged_names, preset_names, tuning_label, hint):
        f = self.fonts()
        pygame.draw.rect(screen, PANEL, pygame.Rect(0, 0, self.width, self.hud_h))
        pygame.draw.line(screen, BORDER, (0, self.hud_h - 1), (self.width, self.hud_h - 1))

        staged = mode == "staged"
        self._button(screen, self.mode_rect, "STAGED" if staged else "LIVE",
                     f["big"], accent=STAGED if staged else None)

        tsurf = f["small"].render("tuning: " + tuning_label, True, TEXT_MUTED)
        screen.blit(tsurf, tsurf.get_rect(topright=(self.width - self.margin, 22)))

        if staged:
            tray = "Pending:  " + ("  ·  ".join(staged_names) if staged_names
                                   else "nothing staged yet")
            screen.blit(f["mid"].render(tray, True, TEXT if staged_names else TEXT_MUTED),
                        (self.margin, 62))
            self._button(screen, self.play_rect, "Play chord (space)", f["small"])
            if preset_names is None:
                self._button(screen, self.save_rect, "Save chord -> Z", f["small"])
            else:
                self._button(screen, self.save_rect, "Preset full", f["small"], muted=True)
            self._button(screen, self.release_rect, "Release", f["small"])

        pv = "  ·  ".join(preset_names) if preset_names else "(empty)"
        screen.blit(f["small"].render("Z:  " + pv, True,
                    TEXT if preset_names else TEXT_MUTED), (self.margin, 148))

        screen.blit(f["small"].render(hint, True, TEXT_MUTED), (self.margin, 176))


def draw_keyboard(screen, white_keys, black_keys, *, held, staged, flashing,
                  labels, key_font, name_font):
    """Paint every key coloured by state (flash > staged > live-held > base), then its
    physical-key-over-note label. Whites first, then blacks on top (the overlap wrinkle)."""
    for k in white_keys:
        _paint_key(screen, k, held, staged, flashing, labels, key_font, name_font)
    for k in black_keys:
        _paint_key(screen, k, held, staged, flashing, labels, key_font, name_font)


def _paint_key(screen, key, held, staged, flashing, labels, key_font, name_font):
    midi = key.midi
    if midi in flashing:
        col = FLASH
    elif midi in staged:
        col = STAGED
    elif midi in held:
        col = LIVE
    else:
        col = BLACK_KEY if key.is_black else WHITE_KEY
    pygame.draw.rect(screen, col, key.rect)
    if not key.is_black:
        pygame.draw.rect(screen, BORDER, key.rect, 1)

    lab = labels.get(midi)
    if not lab:
        return
    char, name = lab
    if key.is_black:
        cs = key_font.render(char, True, (214, 214, 218))
        screen.blit(cs, cs.get_rect(center=(key.rect.centerx, key.rect.bottom - 16)))
    else:
        cs = key_font.render(char, True, TEXT_ON_LIGHT)
        ns = name_font.render(name, True, (96, 96, 102))
        screen.blit(cs, cs.get_rect(center=(key.rect.centerx, key.rect.bottom - 34)))
        screen.blit(ns, ns.get_rect(center=(key.rect.centerx, key.rect.bottom - 14)))
