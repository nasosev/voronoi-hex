from board import Board
from game import Game
from gui import Graphics


def main() -> None:
    board = Board()
    game = Game(board)
    Graphics(game)


if __name__ == "__main__":
    main()
