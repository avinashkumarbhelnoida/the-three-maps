from three_maps.config.thresholds import TAU_D, TAU_P
from three_maps.domain.types import AxisDirectionState, PoleStrength


def resolve_direction(poles: PoleStrength, tau_p: float = TAU_P, tau_d: float = TAU_D, tie_tolerance: float = 0.05) -> AxisDirectionState:
    a, b = poles.pole_a, poles.pole_b
    a_meaningful = a >= tau_p
    b_meaningful = b >= tau_p

    if not a_meaningful and not b_meaningful:
        return AxisDirectionState.INSUFFICIENT
    if a_meaningful and not b_meaningful:
        return AxisDirectionState.A_DOMINANT if a - b >= tau_d else AxisDirectionState.A_ONE_SIDED_SUPPORT
    if b_meaningful and not a_meaningful:
        return AxisDirectionState.B_DOMINANT if b - a >= tau_d else AxisDirectionState.B_ONE_SIDED_SUPPORT

    if abs(a - b) <= tie_tolerance:
        return AxisDirectionState.MEANINGFUL_TIE
    if abs(a - b) >= tau_d:
        return AxisDirectionState.A_DOMINANT if a > b else AxisDirectionState.B_DOMINANT
    return AxisDirectionState.BALANCED
