from three_maps.domain.types import ActivationState, ApplicabilityState


def resolve_activation(*, valid: bool, required_inputs_available: bool, applicability: ApplicabilityState, context_available: bool = True, evidence_available: bool = True) -> ActivationState:
    if not valid:
        return ActivationState.INVALID
    if not required_inputs_available:
        return ActivationState.UNAVAILABLE
    if applicability in {ApplicabilityState.BLOCKED, ApplicabilityState.NOT_APPLICABLE}:
        return ActivationState.NOT_PERMITTED
    if applicability == ApplicabilityState.CONTEXTUAL and not context_available:
        return ActivationState.UNAVAILABLE
    if not evidence_available:
        return ActivationState.UNAVAILABLE
    return ActivationState.ACTIVE
