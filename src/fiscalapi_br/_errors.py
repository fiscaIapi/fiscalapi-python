"""Exceções levantadas pelo cliente da FiscalAPI."""
from __future__ import annotations

from typing import Any, Mapping, Optional


class FiscalAPIError(Exception):
    """Erro base. Toda exceção do SDK herda desta classe.

    Atributos:
        message: mensagem legível devolvida pela API (ou gerada pelo SDK).
        status_code: status HTTP (``None`` em falha de conexão).
        code: código do erro devolvido pela API (ex.: ``PARAMETRO_AUSENTE``).
        request_id: identificador da requisição — informe-o ao suporte.
        body: corpo da resposta já decodificado (dict) ou texto bruto.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        request_id: Optional[str] = None,
        body: Any = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.request_id = request_id
        self.body = body
        self.headers = dict(headers or {})

    def __str__(self) -> str:
        parts = []
        if self.status_code is not None:
            parts.append(f"HTTP {self.status_code}")
        if self.code:
            parts.append(self.code)
        prefix = " ".join(parts)
        suffix = f" (request_id={self.request_id})" if self.request_id else ""
        return f"{prefix}: {self.message}{suffix}" if prefix else f"{self.message}{suffix}"


class AuthenticationError(FiscalAPIError):
    """Chave de API ausente, inválida ou revogada (HTTP 401/403)."""


class InsufficientBalanceError(FiscalAPIError):
    """Sem plano ativo ou saldo esgotado (HTTP 402).

    ``consultas_restantes`` diz quantas consultas desse tipo o saldo ainda paga
    (quando a API informa).
    """

    @property
    def consultas_restantes(self) -> Optional[int]:
        if isinstance(self.body, dict):
            value = self.body.get("consultas_restantes")
            return value if isinstance(value, int) else None
        return None

    @property
    def plan(self) -> Optional[str]:
        if isinstance(self.body, dict):
            value = self.body.get("plan")
            return value if isinstance(value, str) else None
        return None


class RateLimitError(FiscalAPIError):
    """Limite de requisições por minuto do plano excedido (HTTP 429).

    ``retry_after`` traz, em segundos, quanto esperar antes de tentar de novo.
    """

    @property
    def retry_after(self) -> Optional[int]:
        raw = self.headers.get("Retry-After") or self.headers.get("retry-after")
        if raw is None and isinstance(self.body, dict):
            raw = self.body.get("retry_after")
        try:
            return int(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None


class BadRequestError(FiscalAPIError):
    """Parâmetro ausente, conflitante ou inválido (HTTP 400/404/422)."""


class ServerError(FiscalAPIError):
    """Falha do lado da API ou tempo esgotado na fonte (HTTP 5xx)."""


class APIConnectionError(FiscalAPIError):
    """Não foi possível falar com a API (DNS, TLS, conexão recusada, timeout)."""
