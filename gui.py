import tkinter as tk
import tkinter.font

from more_itertools import collapse
from pyrsistent import pset, s
from pyrsistent.typing import PSet
from toolz.curried import map, pipe

from board import Board
from game import Game, Player
from my_types import Cycle
from settings import (
    BORDER_SCALE,
    COLOR_BG,
    COLOR_BLUE,
    COLOR_FG,
    COLOR_RED,
    FONT_SIZE,
    OUTLINE_WIDTH,
    SCREEN_SIZE,
    TITLE,
)


class Text:
    def __init__(self, master: tk.Tk, game: Game) -> None:
        self.game = game
        self.string_var = tk.StringVar()

        frame = tk.Frame(master, height=SCREEN_SIZE, width=SCREEN_SIZE)
        frame.pack(side="right", fill="both")
        frame.pack_propagate(0)

        default_font = tkinter.font.nametofont("TkFixedFont")
        default_font.configure(size=FONT_SIZE)
        tk.Label(
            master=frame,
            textvariable=self.string_var,
            font=default_font,
            bg=COLOR_BG,
            fg=COLOR_FG,
            justify="left",
        ).pack(fill="both", expand=1)

        self.string_var.set("New game!")

    def update_text(self) -> None:
        self.string_var.set(self.game.string_from_homology())


class Graphics:
    __SCALE = (SCREEN_SIZE - 2 * OUTLINE_WIDTH) / BORDER_SCALE
    __OFFSET = 0.5 * SCREEN_SIZE

    def __init__(self, game: Game) -> None:
        root = tk.Tk()
        root.resizable(False, False)
        root.title(TITLE)

        self.canvas = tk.Canvas(
            root,
            height=SCREEN_SIZE,
            width=SCREEN_SIZE,
            bg=COLOR_BG,
            highlightthickness=0,
        )
        self.game = game
        self.text = Text(root, game)

        for player in s(Player.BLUE, Player.RED):
            self.generate_base_polygons(game.board, player)

        for c in game.board.cycles:
            CyclePolygon(self, game, c)

        self.canvas.pack(side="left", fill="both")

        root.mainloop()

    def polygon_from_cycle(
        self, c: Cycle, fill: str = COLOR_FG, state: str = "normal"
    ) -> int:
        flattened_coords = pipe(
            self.game.board.points[c], self.unit_coord_to_pixel, collapse, list
        )
        return self.canvas.create_polygon(
            flattened_coords,
            fill=fill,
            activefill=COLOR_BG,
            outline=COLOR_BG,
            width=OUTLINE_WIDTH,
            state=state,
        )

    def polygons_from_cycles(self, cs: PSet[Cycle], fill: str, state: str) -> PSet[int]:
        return pipe(cs, map(lambda c: self.polygon_from_cycle(c, fill, state)), pset)

    def generate_base_polygons(self, board: Board, team: Player) -> None:
        if team == Player.BLUE:
            fill = COLOR_BLUE
            cs = board.blue_base_cs
        else:
            fill = COLOR_RED
            cs = board.red_base_cs
        self.polygons_from_cycles(cs, fill, "disabled")

    def update_territory(self, polygon: int, player: Player) -> None:
        fill = COLOR_BLUE if player == Player.BLUE else COLOR_RED
        self.canvas.itemconfigure(polygon, fill=fill, state="disabled")
        self.text.update_text()

    def unit_coord_to_pixel(self, coord: float) -> float:
        return self.__SCALE * coord + self.__OFFSET


class CyclePolygon:
    def __init__(self, graphics: Graphics, game: Game, c: Cycle) -> None:
        self.c = c
        self.game = game
        self.graphics = graphics
        self.polygon = graphics.polygon_from_cycle(c)
        self.graphics.canvas.tag_bind(self.polygon, "<Button-1>", self.claim)

    def claim(self, _: tk.Event) -> None:
        player = self.game.player()
        self.game.add_cycle_to_player_complex(player, self.c)
        self.graphics.update_territory(self.polygon, player)
