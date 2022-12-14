class HTTPStatusNotOK(Exception):
    """Статус код не 200."""


class SendMessageError(Exception):
    """Ошибка отправки сообщения."""


class ReturnedStatusIsEmpty(Exception):
    """Пустое значение статуса."""


class UnknownHomeworkStatus(Exception):
    """Неизвестный статус домашней работы."""


class TypeNotList(Exception):
    """response['homeworks'] не список."""


class UnexpectedError(Exception):
    """Непредвиденная ошибка."""


class DecodeError(Exception):
    """Ошибка декодирования."""

class ReturnedHomeWorkNameIsEmpty(Exception):
    """Пустое значение названия домашней работы."""