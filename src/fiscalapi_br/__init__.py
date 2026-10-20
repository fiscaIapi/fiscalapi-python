"""SDK oficial da FiscalAPI para Python.

Consulta de Inscrição Estadual, CNPJ, certidões, NF-e, SIGEF, CNIR e perfil
do produtor rural pela API REST https://api.fiscalapi.com.br.
"""
from ._client import DEFAULT_BASE_URL, FiscalAPI
from ._errors import (
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
    FiscalAPIError,
    InsufficientBalanceError,
    RateLimitError,
    ServerError,
)
from ._version import __version__

__all__ = [
    "DEFAULT_BASE_URL",
    "FiscalAPI",
    "FiscalAPIError",
    "AuthenticationError",
    "InsufficientBalanceError",
    "RateLimitError",
    "BadRequestError",
    "ServerError",
    "APIConnectionError",
    "__version__",
]
