class IncorrectFormatResponseError(Exception):
    """"формат данных не соответствует требуемому"""
    pass

class EndpointError(Exception):
    """API не доступен по URL"""
    pass
