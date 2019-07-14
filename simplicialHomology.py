# Relative simplicial homology library
#
# Copyright (c) 2014-2017, Michael Robinson, Chris Capraro
# Distribution of unaltered copies permitted for noncommercial use only
# All other uses require express permission of the author
# This software comes with no warrantees express or implied

import numpy as np
import itertools as it
import multiprocessing as mp
import functools as ft

# If you're using Python 2.x you'll need to install the futures module (e.g., pip install futures)
try:
    import concurrent.futures as th
except:
    pass

try:
    import networkx as nx
except:
    pass


def kernel(A, tol=1e-5):
    _, s, vh = np.linalg.svd(A)
    sing = np.zeros(vh.shape[0], dtype=np.complex)
    sing[: s.size] = s
    null_mask = sing <= tol
    null_space = np.compress(null_mask, vh, axis=0)
    return null_space.conj().T


def cokernel(A, tol=1e-5):
    u, s, _ = np.linalg.svd(A)
    sing = np.zeros(u.shape[1], dtype=np.complex)
    sing[: s.size] = s
    null_mask = sing <= tol
    return np.compress(null_mask, u, axis=1)


def toplexify(simplices):
    """Reduce a simplicial complex to merely specification of its toplices"""
    simplices = sorted(simplices, key=len, reverse=True)
    return [
        spx
        for i, spx in enumerate(simplices)
        if not [
            sp2
            for j, sp2 in enumerate(simplices)
            if (i != j and set(spx).issubset(sp2)) and (i > j or set(spx) == set(sp2))
        ]
    ]


def ksublists(lst, n, sublist=[]):
    """Iterate over all ordered n-sublists of a list lst"""
    return (list(tup) for tup in (it.combinations(lst, n)))


def simpcluded(spx, simplices):
    """Is a simplex in a list of simplices?"""
    isIncluded = False
    for s in simplices:
        if s == spx:
            isIncluded = True
            break

    return isIncluded


def ksimplices(toplexes, k, relative=None):
    """List of k-simplices in a list of toplexes"""
    simplices = [
        tuple(tup) for toplex in toplexes for tup in (it.combinations(toplex, k + 1))
    ]

    if relative is not None:
        simplices = set(simplices) - set(relative)

    simplices = [
        list(x) for x in set(x for x in simplices)
    ]  # not sure why this is so much faster (~5x) than simplices=[list(x) for x in simplices]

    return simplices


def kflag(subcomplex, k, verts=None):
    """Determine the k-cells of a flag complex"""
    if verts == None:
        verts = list(set([v for s in subcomplex for v in s]))

    return [
        s
        for s in ksublists(verts, k + 1)
        if all(
            [
                [r for r in subcomplex if (p[0] in r) and (p[1] in r)]
                for p in ksublists(s, 2)
            ]
        )
    ]


def flag(subcomplex, maxdim=None):
    """Construct the flag complex based on a given subcomplex"""
    edgelist = ksimplices(subcomplex, 1)

    G = nx.Graph(edgelist)
    cplx = closure(nx.find_cliques(G))
    cplx = [sorted(value) for value in cplx]
    cplx = set(map(tuple, cplx))
    cplx = [value for value in cplx]
    cplx = [value for value in cplx if len(value) <= maxdim + 1]
    cplx = [list(elem) for elem in cplx]

    return cplx


def vietorisRips(pts, diameter, maxdim=None):
    """Construct a Vietoris-Rips complex over a point cloud"""
    subcomplex = [
        [x, y]
        for x in range(len(pts))
        for y in range(x, len(pts))
        if np.linalg.norm(pts[x] - pts[y]) < diameter
    ]
    if maxdim == 1:
        return subcomplex
    if maxdim == None:
        G = nx.Graph()
        G.add_edges_from(subcomplex)
        return nx.find_cliques(G)
    else:
        return flag(subcomplex, maxdim)


def closure(toplexes):
    ## returns the closure of the given complex - adds all of the sublists
    res = set()
    for toplex in toplexes:
        cl = it.chain.from_iterable(
            it.combinations(toplex, r) for r in range(1, len(toplex) + 1)
        )
        res = res | set(cl)
    return list((list(e1) for e1 in res))


def sstar(toplexes, complx):
    ## computes the star of the complex in the ASC generated by the toplexes
    i = 0
    asc = closure(toplexes)

    A = list(complx)
    i += 1
    for simplex in complx:
        B = star(asc, simplex)
        i += 1
        for b in B:
            if not simpcluded(b, A):
                A.append(b)
    return A


def star(cplx, face):
    """Compute the star over a given face.  Works with toplexes (it will return toplexes only, then) or full complexes."""
    return [s for s in cplx if set(face).issubset(s)]


def boundary(toplexes, k, relative=None, km1chain=None):
    """Compute the k-boundary matrix for a simplicial complex"""

    # Retrieve k chain and k-1 chain from toplexes and excised simplices
    kchain = ksimplices(toplexes, k, relative)
    if km1chain == None:
        km1chain = ksimplices(toplexes, k - 1, relative)

    if k <= 0 or not kchain or not km1chain:
        return np.zeros((0, len(kchain)), np.int8), None

    bndry = np.zeros((len(km1chain), len(kchain)), np.int8)

    # Generate dictionary of boundary matrix row indices
    # i.e., Keys = km1chain simplices labels, Values = row index
    km1Dict = dict(list(zip(list(map(str, km1chain)), list(range(0, len(km1chain))))))

    # Get index into kchain simplices for constructing boundary
    # e.g., [A,B,C] => [B,C] - [A,C] + [A,B] so
    # indices would be [[1,2],[0,2],[0,1]]
    indexLst = list(it.combinations(list(range(k + 1)), k))
    indexLst.reverse()

    # Get boundary matrix coefficient list that corresponds index list
    # e.g., [B,C] - [A,C] + [A,B] => [1, -1, 1]
    coefLst = [1] * len(indexLst)
    coefLst[1::2] = [-1] * len(coefLst[1::2])

    # Loop through kchain and build boundary matrix
    for colIdx, splx in enumerate(kchain):
        rowKey = [list(splx[i] for i in li) for li in indexLst]
        rowInd = [km1Dict.get(rowKeyStr, -1) for rowKeyStr in map(str, rowKey)]
        rowIdxVals = [(v, coefLst[ci]) for ci, v in enumerate(rowInd) if v != -1]
        for rowIdxVal in rowIdxVals:
            bndry[rowIdxVal[0], colIdx] = rowIdxVal[1]

    return bndry, kchain


def simplicialHomology(k, X, Y=None, rankOnly=False, tol=1e-5):
    """Compute relative k-homology of a simplicial complex"""
    X, Y = integerVertices(X, Y)
    X = [sorted(value) for value in X]
    Y = [sorted(value) for value in Y]
    Y = set(map(tuple, Y))

    dk, km1chain = boundary(X, k, Y)
    dkp1, _ = boundary(X, k + 1, Y, km1chain)

    if rankOnly:
        return homologyRankOnly(dk, dkp1)
    else:
        return homology(dk, dkp1)


def homology(b1, b2, tol=1e-5):
    """Compute homology from two matrices whose product b1*b2=0"""
    b2p = np.compress(np.any(abs(b2) > tol, axis=0), b2, axis=1)

    # Compute kernel
    if b1.size:
        ker = kernel(b1, tol)
    else:
        ker = np.eye(b1.shape[1])

    # Remove image
    if b2.any():
        kermap, _, _, _ = np.linalg.lstsq(ker, b2p)
        Hk = np.dot(ker, cokernel(kermap, tol))
    else:
        Hk = ker

    return Hk


def homologyRankOnly(b1, b2, tol=1e-5):
    """Compute homology"""
    rankB1 = 0
    rankB2 = 0

    if b1.size > 0:
        rankB1 = np.linalg.matrix_rank(b1, tol)

    if b2.size > 0:
        rankB2 = np.linalg.matrix_rank(b2, tol)

    Hk = b1.shape[1] - rankB1 - rankB2

    return Hk


def localHomology(k, toplexes, simplices, rankOnly=False):
    """Compute local homology relative to the star over a list of simplices"""
    rel = [
        spx
        for spx in (ksimplices(toplexes, k) + ksimplices(toplexes, k - 1))
        if not any([set(simplex).issubset(spx) for simplex in simplices])
    ]

    return simplicialHomology(k, toplexes, rel, rankOnly)


def localHomologyMultithread(k, cplx, numThreads):
    """Compute local homology relative to the star over a list of simplices in parallel"""

    localSimplices = []
    for ki in range(k + 1):
        localSimplices += ksimplices(cplx, ki)

    Hks = [[0 for _ in range(len(localSimplices))] for _ in range(k)]
    with th.ThreadPoolExecutor(max_workers=numThreads) as executor:
        futures = {
            executor.submit(localHomology, ki, cplx, [spx], True): [ki - 1] + [si]
            for ki in range(1, k + 1)
            for si, spx in enumerate(localSimplices)
        }

        for future in th.as_completed(futures, timeout=None):
            key = futures[future]
            Hks[key[0]][key[1]] = future.result()

    return Hks, localSimplices


def localHomologyMultiproc(
    k, cplx, numProcs, localSimplices=None, iterate=True, rankOnly=False
):
    """Compute local homology relative to the star over a list of simplices in parallel"""

    if localSimplices is None:
        localSimplices = []
        for ki in range(k + 1):
            localSimplices += ksimplices(cplx, ki)

    pool = mp.Pool(numProcs)  # creates a pool of process, controls workers
    # the pool.map only accepts one iterable, so use the partial function
    # so that we only need to deal with one variable.
    if iterate:
        Hks = [[0 for _ in range(len(localSimplices))] for _ in range(k)]
        for isplx, splx in enumerate(localSimplices):
            partialLocalHomology = ft.partial(
                localHomology, toplexes=cplx, simplices=[splx], rankOnly=rankOnly
            )
            res = pool.map(
                partialLocalHomology, list(range(1, k + 1))
            )  # make our results with a map call
            for ri, r in enumerate(res):
                Hks[ri][isplx] = r
    else:
        Hks = [0 for _ in range(k)]
        partialLocalHomology = ft.partial(
            localHomology, toplexes=cplx, simplices=localSimplices, rankOnly=rankOnly
        )
        Hks = pool.map(
            partialLocalHomology, list(range(1, k + 1))
        )  # make our results with a map call

    pool.close()  # we are not adding any more processes
    pool.join()  # tell it to wait until all threads are done before

    return Hks, localSimplices


def cone(toplexes, subcomplex, coneVertex="*"):
    """Construct the cone over a subcomplex.  The cone vertex can be renamed if desired.  The resulting complex is homotopy equivalent to the quotient by the subcomplex."""
    return toplexes + [spx + [coneVertex] for spx in subcomplex]


def integerVertices(cplx1, cplx2=[]):
    """Rename vertices in a complex so that they are all integers"""
    if cplx1 is None:
        cplx1 = []

    if cplx2 is None:
        cplx2 = []

    cplx = cplx1 + cplx2
    vertslist = set([v for s in cplx for v in s])
    vertsdict = dict(list(zip(vertslist, list(range(len(vertslist))))))
    cplx1 = [[vertsdict[v] for v in s] for s in cplx1]
    cplx2 = [[vertsdict[v] for v in s] for s in cplx2]

    return cplx1, cplx2


def vertexHoplength(toplexes, vertices, maxHoplength=None):
    """Compute the edge hoplength distance to a set of vertices within the complex.  Returns the list of tuples (vertex,distance)"""
    vertslist = list(set([v for s in toplexes for v in s if v not in vertices]))
    outlist = [(v, 0) for v in vertices]  # Prebuild output of the function
    outsimplices = [w for s in toplexes if [v for v in vertices if v in s] for w in s]

    # Consume the remaining vertices
    currentlen = 1
    while vertslist and (maxHoplength == None or currentlen < maxHoplength):
        # Find all vertices adjacent to the current ones
        nextverts = [v for v in vertslist if v in outsimplices]

        # Rebuild the output
        outlist = outlist + [(v, currentlen) for v in nextverts]

        # Recompute implicated simplices
        outsimplices = [
            w for s in toplexes if [v for v, _ in outlist if v in s] for w in s
        ]

        # Rebuild current vertex list
        vertslist = [v for v in vertslist if v not in nextverts]
        currentlen += 1

    return outlist


def vertexLabels2simplices(toplexes, vertexLabels, nonConeLabel=None, coneName=None):
    """Propagate numerical vertex labels (list of pairs: (vertex, label)) to labels on simplices.  If you want the same label applied to simplices not touching a particular 'cone' vertex named coneName, set that nonConeLabel to the desired label.  Note: will use the smallest vertex label or infinity if none given"""
    if nonConeLabel == None:
        return [
            (s, min([label for v, label in vertexLabels if v in s] + [float("inf")]))
            for s in toplexes
        ]
    else:
        return [
            (
                s,
                min([label for v, label in vertexLabels if v in s] + [float("inf")])
                if [v for v in s if v == coneName]
                else nonConeLabel,
            )
            for s in toplexes
        ]


def iteratedCone(toplexes, subcomplex):
    """Prepare to compute local homology centered at subcomplex using Perseus.  In order to that, this function constructs a labeled sequence of (coned off) simplices paired with birth times. NB: We want reduced homology, but Perseus doesn't compute that..."""

    # Hoplengths to all vertices -- will be used for anti-birth times
    vertexLabels = vertexHoplength(
        toplexes, list(set([v for s in subcomplex for v in s]))
    )

    # Maximum hoplength
    maxHopLength = max([t for v, t in vertexLabels])

    # All the toplexes in the final, coned off complex
    coned = cone(toplexes, [s for s in toplexes if s not in subcomplex])

    # Propagate vertex labels
    conedLabeled = vertexLabels2simplices(
        coned, vertexLabels, nonConeLabel=maxHopLength - 1, coneName="*"
    )

    # Renumber vertices and return
    vertslist = list(set([v for s in coned for v in s]))
    return [
        ([vertslist.index(x) for x in s], maxHopLength - t) for s, t in conedLabeled
    ]


def complex2perseus(filename, toplexes, labels=False):
    """Write a complex out as a file for input into Perseus.  If there are labels containing birth times, set labels=True"""
    with open(filename, "wt") as fp:
        fp.write("1\n")
        for tp in toplexes:
            fp.write(str(len(tp[0]) - 1) + " ")
            for v in tp[0]:
                fp.write(str(v + 1) + " ")

            if labels:
                fp.write(str(tp[1]) + "\n")
            else:
                fp.write("1 \n")


def jaccardIndexFaces(face1, face2):
    """Compute the Jaccard index between two faces"""
    face1Set = set(face1)
    face2Set = set(face2)
    inter = len(face1Set.intersection(face2Set))
    union = len(face1Set.union(face2Set))
    if union == 0:
        return 1
    else:
        return float(inter) / float(union)