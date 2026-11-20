"""TODO: generate canonical terrain deterministically from specification and seed."""
import random

from src.api import GenerationFailure, Terrain, TerrainGenerationSpec, TerrainTopology


class TerrainGenerator:
    """Keep state local; identical inputs must also agree across fresh instances."""

    def __init__(self) -> None:
        pass

    def generate_terrain(self, specification: TerrainGenerationSpec, seed: int) -> Terrain:
        rng = random.Random(seed)   
        for _ in range(max(1, specification.max_attempts)):
            grid = self._grow(specification, rng)
            if grid is not None:
                return Terrain(tuple("".join(row) for row in grid))
        raise GenerationFailure("TerrainGenerator", "no attempt satisfied the specification")

    def _grow(self, spec: TerrainGenerationSpec, rng: random.Random):
        rows, columns = spec.rows, spec.columns
        low = max(1, spec.min_open_tiles)
        high = min(max(low, spec.max_open_tiles), rows * columns)
        target = rng.randint(low, high)

        grid = [["#"] * columns for _ in range(rows)]
        floor: set = set()
        degree: dict = {}
        start = (rng.randrange(rows), rng.randrange(columns))
        floor.add(start)
        degree[start] = 0
        grid[start[0]][start[1]] = "."

        keep_linear = spec.topology in (TerrainTopology.STRAIGHT_PATH, TerrainTopology.BENT_PATH)
        while len(floor) < target:
            candidates = []
            for cell in floor:
                if keep_linear and degree[cell] >= 2:
                    continue   
                for nxt in self._orthogonal(cell, rows, columns):
                    if nxt in floor:
                        continue
                    if sum(n in floor for n in self._orthogonal(nxt, rows, columns)) != 1:
                        continue   
                    candidates.append((cell, nxt))
            if not candidates:
                return None   
            parent, child = rng.choice(candidates)
            floor.add(child)
            degree[child] = 1
            degree[parent] += 1
            grid[child[0]][child[1]] = "."
        return grid

    @staticmethod
    def _orthogonal(cell, rows, columns):
        r, c = cell
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < columns:
                yield (nr, nc)