
class CustomError(Exception):
    pass


class InvalidTemplateError(CustomError):
    pass


class InvalidCustomerError(CustomError):
    pass


class InvalidImageError(CustomError):
    pass
