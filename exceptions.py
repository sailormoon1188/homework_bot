class EndpointError(Exception):
    """API не доступен по URL"""
    pass

class EmtyHomeworkListExc(Exception):
    """Список homework пуст"""
    pass