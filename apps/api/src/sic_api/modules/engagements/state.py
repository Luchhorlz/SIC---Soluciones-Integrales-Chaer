from .models import BookingStatus, ServiceRequestStatus


class InvalidTransitionError(ValueError):
    pass


def request_transition(current: ServiceRequestStatus, action: str) -> ServiceRequestStatus:
    transitions = {
        "view": ({ServiceRequestStatus.REQUESTED}, ServiceRequestStatus.VIEWED),
        "quote": ({ServiceRequestStatus.REQUESTED, ServiceRequestStatus.VIEWED, ServiceRequestStatus.QUOTED}, ServiceRequestStatus.QUOTED),
        "accept": ({ServiceRequestStatus.REQUESTED, ServiceRequestStatus.VIEWED, ServiceRequestStatus.QUOTED}, ServiceRequestStatus.ACCEPTED),
        "decline": ({ServiceRequestStatus.REQUESTED, ServiceRequestStatus.VIEWED, ServiceRequestStatus.QUOTED}, ServiceRequestStatus.DECLINED),
        "cancel": ({ServiceRequestStatus.REQUESTED, ServiceRequestStatus.VIEWED, ServiceRequestStatus.QUOTED}, ServiceRequestStatus.CANCELLED),
        "convert": ({ServiceRequestStatus.ACCEPTED}, ServiceRequestStatus.CONVERTED_TO_BOOKING),
    }
    allowed, target = transitions[action]
    if current not in allowed:
        raise InvalidTransitionError(f"Request cannot perform {action} from {current.value}")
    return target


def booking_transition(current: BookingStatus, action: str, *, actor: str, client_confirmed: bool = False) -> BookingStatus:
    if action == "confirm" and actor == "provider" and current == BookingStatus.PENDING_PROVIDER:
        return BookingStatus.CONFIRMED
    if action == "start" and actor == "provider" and current == BookingStatus.CONFIRMED:
        return BookingStatus.IN_PROGRESS
    if action == "complete" and actor == "provider" and current == BookingStatus.IN_PROGRESS:
        return BookingStatus.COMPLETED
    if action == "confirm" and actor == "client" and current == BookingStatus.COMPLETED and not client_confirmed:
        return BookingStatus.COMPLETED
    if action == "dispute" and actor == "client" and current == BookingStatus.COMPLETED and not client_confirmed:
        return BookingStatus.DISPUTED
    if action == "cancel" and actor == "client" and current in {BookingStatus.PENDING_PROVIDER, BookingStatus.CONFIRMED}:
        return BookingStatus.CANCELLED_BY_CLIENT
    if action == "cancel" and actor == "provider" and current in {BookingStatus.PENDING_PROVIDER, BookingStatus.CONFIRMED}:
        return BookingStatus.CANCELLED_BY_PROVIDER
    if action == "no_show" and actor == "provider" and current == BookingStatus.CONFIRMED:
        return BookingStatus.NO_SHOW
    raise InvalidTransitionError(f"Booking cannot perform {action} as {actor} from {current.value}")
