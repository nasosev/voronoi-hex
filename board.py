from typing import Tuple

import numpy as np
import scipy as sp
from pyrsistent import freeze, pset, s, v
from pyrsistent.typing import PSet
from toolz.curried import map, partial, pipe

from my_types import Complex, Cycle
from settings import BOARD_SIZE, BORDER_SCALE, EPSILON, SEED
from topology import (
    closure,
    edges_from_cycles,
    faces_from_edges,
    outer_edges_from_cycle,
    zero_cells_from_one_cells,
)


class Board:
    def __init__(self) -> None:
        if SEED is not None:
            np.random.seed(SEED)

        def reflect(u: np.ndarray, a: np.ndarray, c: float) -> np.ndarray:
            return u - 2 * np.broadcast_to(a, u.shape) * (
                np.reshape(np.dot(u, a) - c, (len(u), 1))
            )

        control_points = np.random.rand(BOARD_SIZE, 2) - 0.5
        reflect_control_points = partial(reflect, control_points)

        down_reflect = reflect_control_points(np.array([0, 1]), -0.5)
        up_reflect = reflect_control_points(np.array([0, 1]), 0.5)
        left_reflect = reflect_control_points(np.array([1, 0]), -0.5)
        right_reflect = reflect_control_points(np.array([1, 0]), 0.5)

        extended_points = np.concatenate(
            (control_points, up_reflect, down_reflect, left_reflect, right_reflect)
        )

        voronoi = sp.spatial.Voronoi(extended_points)

        self.cycles = freeze(
            np.array(voronoi.regions)[voronoi.point_region[: voronoi.npoints // 5]]
        )

        edges = edges_from_cycles(self.cycles)
        verts = zero_cells_from_one_cells(edges)

        self.points, self.blue_base, self.red_base, self.blue_base_cs, self.red_base_cs = self.make_border(
            voronoi.vertices, edges
        )

        self.xs = verts | edges | self.blue_base | self.red_base

    @staticmethod
    def make_border(
        vertices: np.ndarray, one_cells: Complex
    ) -> Tuple[np.ndarray, Complex, Complex, PSet[Cycle], PSet[Cycle]]:
        def first_index(array: np.ndarray, value: np.ndarray) -> float:
            return next(
                i for i, _ in enumerate(array) if np.linalg.norm(value - _) < EPSILON
            )

        first_index_vertices = partial(first_index, vertices)

        corners = v(v(-0.5, 0.5), v(-0.5, -0.5), v(0.5, -0.5), v(0.5, 0.5))

        ul, dl, dr, ur = pipe(corners, map(np.array), map(first_index_vertices))

        max_ind = len(vertices)

        cul = max_ind
        cdl = max_ind + 1
        cdr = max_ind + 2
        cur = max_ind + 3

        left_c = v(ul, cul, cdl, dl)
        right_c = v(dr, cdr, cur, ur)
        down_c = v(dl, cdl, cdr, dr)
        up_c = v(ur, cur, cul, ul)

        red_base_cs = s(left_c, right_c)
        blue_base_cs = s(up_c, down_c)

        def border_edges(vs: np.ndarray, es: Complex, pos: int, side: float) -> Complex:
            return pset(
                edge
                for edge in es
                if all(
                    np.linalg.norm(vs[point][pos] - side) < EPSILON for point in edge
                )
            )

        border_edges_from_square_side = partial(border_edges, vertices, one_cells)

        left_faces = faces_from_edges(
            border_edges_from_square_side(0, -0.5) | outer_edges_from_cycle(left_c)
        )
        right_faces = faces_from_edges(
            border_edges_from_square_side(0, 0.5) | outer_edges_from_cycle(right_c)
        )
        down_faces = faces_from_edges(
            border_edges_from_square_side(1, -0.5) | outer_edges_from_cycle(down_c)
        )
        up_faces = faces_from_edges(
            border_edges_from_square_side(1, 0.5) | outer_edges_from_cycle(up_c)
        )

        red_base = closure(left_faces | right_faces)
        blue_base = closure(down_faces | up_faces)

        border_points = np.array(corners) * BORDER_SCALE
        aug_points = np.concatenate((vertices, border_points))

        return aug_points, blue_base, red_base, blue_base_cs, red_base_cs
