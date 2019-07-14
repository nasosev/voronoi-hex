from enum import Enum
from itertools import cycle

from pyrsistent import s
from toolz.curried import pipe

from board import Board
from my_types import Cycle
from topology import betti, closure, face_from_cycle


class Player(Enum):
    NEUTRAL = 1
    BLUE = 2
    RED = 3


class Game:
    def __init__(self, board: Board):
        self.board = board
        self.blue = board.blue_base
        self.red = board.red_base
        self.__player = cycle(s(Player.RED, Player.BLUE))

    def player(self) -> Player:
        return next(self.__player)

    def add_cycle_to_player_complex(self, player: Player, c: Cycle) -> None:
        cell_region = pipe(c, face_from_cycle, closure)
        if player == Player.BLUE:
            self.blue |= cell_region
        else:
            self.red |= cell_region

    def string_from_homology(self) -> str:
        h0b = betti(0, self.blue)
        h1b = betti(1, self.blue)
        h0r = betti(0, self.red)
        h1r = betti(1, self.red)

        h0bb = betti(0, self.blue, self.board.blue_base)
        h1bb = betti(1, self.blue, self.board.blue_base)
        h0rr = betti(0, self.red, self.board.red_base)
        h1rr = betti(1, self.red, self.board.red_base)

        winner = "winner: blue!" if h1bb > h1b else "winner: red!" if h1rr > h1r else ""

        string = (
            f"betti    :\tdim=0\tdim=1\n"
            f"------------------------------\n"
            f"b(B)     :\t{h0b}\t{h1b}\n"
            f"b(B,B_0) :\t{h0bb}\t{h1bb}\n"
            f"b(R)     :\t{h0r}\t{h1r}\n"
            f"b(R,R_0) :\t{h0rr}\t{h1rr}\n"
            f"\n\n"
            f"{winner}"
        )

        return string
