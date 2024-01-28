class WorkWithWebError(Exception):
    pass


class NotCorrectResponseError(WorkWithWebError):
    pass

class RequestError(WorkWithWebError):
    pass

class StatusCodeError(WorkWithWebError):
    pass


class BotError(Exception):
    pass


class AuthorizationError(BotError):
    pass


class SendRequestError(BotError):
    pass
