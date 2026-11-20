"""TODO: select one public action from each immutable world observation."""
from collections import deque

from src.api import Position, WorldAction, WorldActionType, WorldSnapshot, WorldActionType


class AgentController:
    """A new controller is constructed for each run; arrival still needs EXIT."""

    def __init__(self) -> None:
        pass

    def choose_action(self, state: WorldSnapshot, agent_id: str) -> WorldAction:
        start = state.agent_position
        goal = state.exit_position
        allowed = set(state.allowed_actions)

        if WorldActionType.COLLECT in allowed:
            collected = set(state.collected_artifact_ids)
            for artifact in state.level.artifacts:
                if artifact.position == start and artifact.artifact_id not in collected:
                    return WorldAction(WorldActionType.COLLECT, target_id=artifact.artifact_id)

        if start == goal and WorldActionType.EXIT in allowed:
            return WorldAction(WorldActionType.EXIT)

        static, patrol_cells = self._enemy_maps(state)
        can_engage = WorldActionType.ENGAGE in allowed

        safe = self._bfs(state, start, goal, patrol_cells,
 set() if can_engage else static, allow_engage=False)
        risky = (self._bfs(state, start, goal, patrol_cells, static, allow_engage=True)
                 if can_engage else None)

        if risky is None:
            route = safe
        elif safe is None:
            route = risky
        else:
            safe_cost = len(safe) + 1
            risky_cost = len(risky) + 1 + sum(
                static[cell].encounter_penalty for cell in risky if cell in static)
            route = safe if safe_cost <= risky_cost else risky

        if route is not None:
            nxt = route[0]
            if nxt in static:
                return WorldAction(WorldActionType.ENGAGE, target_id=static[nxt].enemy_id)
            return self._step(start, nxt)

        if WorldActionType.WAIT in allowed:
            return WorldAction.wait()
        for fallback in self._neighbors(start):
            if state.is_traversable(fallback) and fallback not in patrol_cells:
                return self._step(start, fallback)
        return WorldAction.wait()

    def _enemy_maps(self, state: WorldSnapshot):
        static = {}
        patrol_cells = set()
        defeated = set(state.defeated_enemy_ids)
        for obs in state.enemy_observations:
            if obs.enemy_id in defeated or obs.position is None:
                continue
            if obs.phase is None:
                static[obs.position] = obs
            else:
                patrol_cells.add(obs.position)
        return static, patrol_cells

    def _bfs(self, state, start, goal, blocked, engagable, allow_engage):
        frontier = deque([[start]])
        seen = {start}
        while frontier:
            path = frontier.popleft()
            cell = path[-1]
            if cell == goal:
                return path[1:]
            for nxt in self._neighbors(cell):
                if nxt in seen or not state.is_traversable(nxt) or nxt in blocked:
                    continue
                if not allow_engage and nxt in engagable:
                    continue
                seen.add(nxt)
                frontier.append(path + [nxt])
        return None

    @staticmethod
    def _neighbors(cell: Position):
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            yield Position(cell.row + dr, cell.column + dc)

    @staticmethod
    def _step(here: Position, nxt: Position) -> WorldAction:
        if nxt.row > here.row:
            return WorldAction(WorldActionType.MOVE_SOUTH)
        if nxt.row < here.row:
            return WorldAction(WorldActionType.MOVE_NORTH)
        if nxt.column > here.column:
            return WorldAction(WorldActionType.MOVE_EAST)
        return WorldAction(WorldActionType.MOVE_WEST)