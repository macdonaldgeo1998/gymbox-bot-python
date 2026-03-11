class GymboxError(Exception):
    pass


class LoginError(GymboxError):
    pass


class TimetableFetchError(GymboxError):
    pass


class BookingError(GymboxError):
    pass


class NoMatchingClassError(GymboxError):
    pass