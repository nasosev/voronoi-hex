from itertools import cycle
from typing import List, Optional

from more_itertools import powerset
from pyrsistent import pset, s
from pyrsistent.typing import PSet
from toolz.curried import concat, filter, first, map, pipe, sliding_window, take

from my_types import Complex, Cycle
from simplicialHomology import simplicialHomology


def edges_from_cycle(c: Cycle) -> Complex:
    return pipe(c, cycle, sliding_window(2), take(len(c)), map(pset), pset)


def edges_from_cycles(cs: PSet[Cycle]) -> Complex:
    return pipe(cs, map(edges_from_cycle), concat, pset)


def verts_from_edges(xs: Complex) -> Complex:
    return pipe(xs, concat, map(s), pset)


def outer_edges_from_cycle(c: Cycle) -> Complex:
    return pipe(c, sliding_window(2), map(pset), pset)


def face_from_cycle(c: Cycle) -> Complex:
    return pipe(c[1:], outer_edges_from_cycle, map(lambda t: t | s(c[0])), pset)


def faces_from_edges(es: Complex) -> Complex:
    v0: int = pipe(es, first, first)
    return pipe(es, filter(lambda t: v0 not in t), map(lambda t: t | s(v0)), pset)


def closure(xs: Complex) -> Complex:
    return pipe(xs, map(powerset), concat, map(pset), pset)


def betti(index: int, xs: Complex, subspace: Optional[Complex] = None) -> int:
    def lists_from_complex(immutable: Complex) -> List[List[int]]:
        return list([list(y for y in x) for x in immutable])

    if subspace is not None:
        return simplicialHomology(
            index, lists_from_complex(xs), lists_from_complex(subspace), rankOnly=True
        )
    else:
        return simplicialHomology(index, lists_from_complex(xs), rankOnly=True)
