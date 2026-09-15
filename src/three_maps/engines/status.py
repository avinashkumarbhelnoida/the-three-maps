from three_maps.domain.types import SystemScoreStatus


def resolve_system_status(*, target_valid: bool, score_calculable: bool, material_gap: bool) -> SystemScoreStatus:
    """Canonical precedence: INVALID > UNAVAILABLE > PARTIAL > EVALUATED."""
    if not target_valid:
        return SystemScoreStatus.INVALID
    if not score_calculable:
        return SystemScoreStatus.UNAVAILABLE
    if material_gap:
        return SystemScoreStatus.PARTIAL
    return SystemScoreStatus.EVALUATED
