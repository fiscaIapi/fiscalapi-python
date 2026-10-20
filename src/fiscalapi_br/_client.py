"""Cliente HTTP da FiscalAPI — somente biblioteca padrão (zero dependências)."""
from __future__ import annotations

import base64
import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Mapping, Optional, Union, cast

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
from .types import (
    CertidaoFederalResponse,
    CertidoesTodasResponse,
    CNDResponse,
    CNDTodosResponse,
    CnirResponse,
    CNPJResponse,
    ConsultaIEResponse,
    ConsultaIETodosResponse,
    NfeXmlResponse,
    PerfilProdutorResponse,
    SigefParcelaResponse,
    SigefResponse,
)

DEFAULT_BASE_URL = "https://api.fiscalapi.com.br"
# Algumas consultas (NF-e, SIGEF) podem levar até 180 s no servidor.
DEFAULT_TIMEOUT = 200.0
DEFAULT_MAX_RETRIES = 3

_RETRYABLE_ANY_METHOD = {429}
_RETRYABLE_IDEMPOTENT = {500, 502, 503, 504}
_MAX_BACKOFF = 30.0
_MAX_RETRY_AFTER = 60.0

Certificado = Union[bytes, bytearray, str, "os.PathLike[str]"]


class FiscalAPI:
    """Cliente da FiscalAPI.

    Exemplo::

        from fiscalapi_br import FiscalAPI

        api = FiscalAPI("sua-chave")
        resp = api.consultar_ie(uf="MT", cpf="12345678909")

    Args:
        api_key: chave de API do painel. Se omitida, lê ``FISCALAPI_API_KEY``.
        base_url: URL base da API.
        timeout: tempo máximo, em segundos, de cada tentativa.
        max_retries: novas tentativas em 429 e (para GET) em 5xx/falha de rede.
        user_agent: sufixo opcional para o cabeçalho ``User-Agent``.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        user_agent: Optional[str] = None,
    ) -> None:
        key = api_key or os.environ.get("FISCALAPI_API_KEY")
        if not key:
            raise ValueError(
                "Informe a chave de API: FiscalAPI('sua-chave') ou a variável FISCALAPI_API_KEY."
            )
        self.api_key = key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        ua = f"fiscalapi-br-python/{__version__}"
        self.user_agent = f"{ua} {user_agent}" if user_agent else ua

    # ------------------------------------------------------------------ IE

    def consultar_ie(
        self,
        uf: str,
        *,
        cpf: Optional[str] = None,
        cnpj: Optional[str] = None,
        ie: Optional[str] = None,
        secundarias: bool = False,
    ) -> ConsultaIEResponse:
        """Inscrição Estadual em uma UF (``GET /api/consultar``).

        Informe exatamente um entre ``cpf``, ``cnpj`` e ``ie``. Com
        ``secundarias=True`` a resposta traz as atividades secundárias
        (``cnaes_secundarios``) — a consulta fica mais lenta.
        """
        doc = _um_documento(cpf=cpf, cnpj=cnpj, ie=ie)
        params = {"uf": _uf(uf), **doc, "secundarias": secundarias or None}
        return cast(ConsultaIEResponse, self._get("/api/consultar", params))

    def consultar_ie_todos(
        self,
        *,
        cpf: Optional[str] = None,
        cnpj: Optional[str] = None,
        ie: Optional[str] = None,
        secundarias: bool = False,
    ) -> ConsultaIETodosResponse:
        """Inscrição Estadual em todos os estados (``GET /api/consultar-ie-todos``).

        Confira ``complete``: quando ``False``, algum estado falhou e um
        resultado vazio não significa "não encontrado".
        """
        doc = _um_documento(cpf=cpf, cnpj=cnpj, ie=ie)
        params = {**doc, "secundarias": secundarias or None}
        return cast(ConsultaIETodosResponse, self._get("/api/consultar-ie-todos", params))

    # ---------------------------------------------------------------- CNPJ

    def consultar_cnpj(self, cnpj: str, *, force_fresh: bool = False) -> CNPJResponse:
        """Dados cadastrais do CNPJ na Receita Federal (``GET /api/consultar-cnpj``).

        ``force_fresh=True`` consulta o dado atual, sem cache (mais lento e
        consome mais créditos).
        """
        if not cnpj:
            raise ValueError("Informe o CNPJ.")
        params = {"cnpj": cnpj, "force_fresh": force_fresh or None}
        return cast(CNPJResponse, self._get("/api/consultar-cnpj", params))

    # ----------------------------------------------------------- Certidões

    def consultar_cnd(
        self, uf: str, *, cpf: Optional[str] = None, cnpj: Optional[str] = None
    ) -> CNDResponse:
        """CND estadual (ICMS) em uma UF (``GET /api/consultar-cnd``)."""
        params = {"uf": _uf(uf), **_um_documento(cpf=cpf, cnpj=cnpj)}
        return cast(CNDResponse, self._get("/api/consultar-cnd", params))

    def consultar_cnd_todos(
        self, *, cpf: Optional[str] = None, cnpj: Optional[str] = None
    ) -> CNDTodosResponse:
        """CND estadual em todos os estados disponíveis (``GET /api/consultar-cnd-todos``)."""
        params = _um_documento(cpf=cpf, cnpj=cnpj)
        return cast(CNDTodosResponse, self._get("/api/consultar-cnd-todos", params))

    def consultar_cnd_federal(
        self,
        *,
        cpf: Optional[str] = None,
        cnpj: Optional[str] = None,
        emitir_nova: bool = False,
    ) -> CertidaoFederalResponse:
        """CND Federal — Receita Federal + PGFN (``GET /api/consultar-cnd-federal``).

        Devolve a certidão vigente quando ela vale por mais de 3 dias
        (``modo="consulta"``); senão, emite uma nova (``modo="emissao"``).
        ``emitir_nova=True`` força uma nova emissão.
        """
        params = {**_um_documento(cpf=cpf, cnpj=cnpj), "emitir_nova": emitir_nova or None}
        return cast(CertidaoFederalResponse, self._get("/api/consultar-cnd-federal", params))

    def consultar_cndt(
        self, *, cpf: Optional[str] = None, cnpj: Optional[str] = None
    ) -> CertidaoFederalResponse:
        """CNDT — débitos trabalhistas (``GET /api/consultar-cndt``)."""
        params = _um_documento(cpf=cpf, cnpj=cnpj)
        return cast(CertidaoFederalResponse, self._get("/api/consultar-cndt", params))

    def consultar_crf_fgts(
        self, *, cpf: Optional[str] = None, cnpj: Optional[str] = None
    ) -> CertidaoFederalResponse:
        """CRF — regularidade do FGTS (``GET /api/consultar-crf-fgts``)."""
        params = _um_documento(cpf=cpf, cnpj=cnpj)
        return cast(CertidaoFederalResponse, self._get("/api/consultar-crf-fgts", params))

    def consultar_certidoes_todas(
        self,
        *,
        cpf: Optional[str] = None,
        cnpj: Optional[str] = None,
        skip_estaduais: bool = False,
    ) -> CertidoesTodasResponse:
        """CNDs estaduais + CNDT + CND Federal + CRF/FGTS em uma chamada
        (``GET /api/certidoes-todas``)."""
        params = {**_um_documento(cpf=cpf, cnpj=cnpj), "skip_estaduais": skip_estaduais or None}
        return cast(CertidoesTodasResponse, self._get("/api/certidoes-todas", params))

    # ---------------------------------------------------------------- NF-e

    def consultar_nfe_xml(
        self,
        chave: str,
        *,
        certificado: Certificado,
        senha: str,
        manifestar: bool = True,
    ) -> NfeXmlResponse:
        """XML completo de uma NF-e pela chave de acesso (``POST /api/consultar-nfe-xml``).

        Args:
            chave: chave de acesso com 44 dígitos.
            certificado: certificado A1 (.pfx/.p12) do participante da nota —
                caminho do arquivo, ``bytes`` do arquivo ou o conteúdo já em
                base64. O certificado não é armazenado pela API.
            senha: senha do certificado.
            manifestar: quando só há o resumo da nota, registra a manifestação
                do destinatário para liberar o XML. ``False`` não registra
                nenhum evento.
        """
        if not chave:
            raise ValueError("Informe a chave de acesso.")
        body = {
            "chave": "".join(ch for ch in chave if ch.isdigit()),
            "certificado": _certificado_base64(certificado),
            "senha": senha,
            "manifestar": manifestar,
        }
        # POST não é repetido em 5xx: a manifestação pode já ter sido registrada.
        return cast(NfeXmlResponse, self._request("POST", "/api/consultar-nfe-xml", json_body=body))

    # ------------------------------------------------------- Imóvel rural

    def consultar_sigef(
        self, *, cpf: Optional[str] = None, cnpj: Optional[str] = None
    ) -> SigefResponse:
        """Parcelas certificadas no SIGEF/INCRA do detentor (``GET /api/consultar-sigef``)."""
        params = _um_documento(cpf=cpf, cnpj=cnpj)
        return cast(SigefResponse, self._get("/api/consultar-sigef", params))

    def consultar_sigef_parcela(
        self, uuid: str, *, force_fresh: bool = False
    ) -> SigefParcelaResponse:
        """Uma parcela SIGEF pelo UUID, com polígono, vértices e confrontantes
        (``GET /api/consultar-sigef-parcela``)."""
        if not uuid:
            raise ValueError("Informe o UUID da parcela.")
        params = {"uuid": uuid.strip(), "force_fresh": force_fresh or None}
        return cast(SigefParcelaResponse, self._get("/api/consultar-sigef-parcela", params))

    def consultar_cnir(
        self, *, cpf: Optional[str] = None, cnpj: Optional[str] = None
    ) -> CnirResponse:
        """Imóveis rurais no CNIR/CAFIR (``GET /api/consultar-cnir``)."""
        params = _um_documento(cpf=cpf, cnpj=cnpj)
        return cast(CnirResponse, self._get("/api/consultar-cnir", params))

    # ------------------------------------------------------------- Perfil

    def perfil_produtor(
        self, *, cpf: Optional[str] = None, cnpj: Optional[str] = None
    ) -> PerfilProdutorResponse:
        """Perfil consolidado do produtor rural (``GET /api/perfil-produtor``)."""
        params = _um_documento(cpf=cpf, cnpj=cnpj)
        return cast(PerfilProdutorResponse, self._get("/api/perfil-produtor", params))

    # ----------------------------------------------------------- Transporte

    def _get(self, path: str, params: Mapping[str, Any]) -> Dict[str, Any]:
        return self._request("GET", path, params=params)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = self.base_url + path
        query = _encode_query(params or {})
        if query:
            url = f"{url}?{query}"

        data: Optional[bytes] = None
        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        idempotent = method == "GET"
        attempt = 0
        while True:
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                return _decode_success(raw)
            except urllib.error.HTTPError as exc:
                status = exc.code
                resp_headers = dict(exc.headers.items()) if exc.headers else {}
                try:
                    raw_err = exc.read()
                except OSError:
                    raw_err = b""
                retryable = status in _RETRYABLE_ANY_METHOD or (
                    idempotent and status in _RETRYABLE_IDEMPOTENT
                )
                if retryable and attempt < self.max_retries:
                    time.sleep(_delay(attempt, resp_headers.get("Retry-After")))
                    attempt += 1
                    continue
                raise _error_from_response(status, raw_err, resp_headers) from None
            except OSError as exc:  # URLError, timeout, conexão recusada
                if idempotent and attempt < self.max_retries:
                    time.sleep(_delay(attempt, None))
                    attempt += 1
                    continue
                raise APIConnectionError(f"Falha ao conectar à FiscalAPI: {exc}") from exc


# ---------------------------------------------------------------- utilitários


def _um_documento(**docs: Optional[str]) -> Dict[str, str]:
    informados = {k: v.strip() for k, v in docs.items() if v is not None and v.strip()}
    nomes = " ou ".join(docs.keys())
    if not informados:
        raise ValueError(f"Informe {nomes}.")
    if len(informados) > 1:
        raise ValueError(f"Informe apenas um: {nomes}.")
    return informados


def _uf(uf: str) -> str:
    if not uf or len(uf.strip()) != 2:
        raise ValueError("Informe a UF com 2 letras (ex.: MT).")
    return uf.strip().upper()


def _encode_query(params: Mapping[str, Any]) -> str:
    clean = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        clean.append((key, str(value)))
    return urllib.parse.urlencode(clean)


def _certificado_base64(cert: Certificado) -> str:
    if isinstance(cert, (bytes, bytearray)):
        return base64.b64encode(bytes(cert)).decode("ascii")
    if isinstance(cert, os.PathLike):
        with open(cert, "rb") as fh:
            return base64.b64encode(fh.read()).decode("ascii")
    if isinstance(cert, str):
        try:
            is_file = len(cert) < 4096 and os.path.isfile(cert)
        except (OSError, ValueError):
            is_file = False
        if is_file:
            with open(cert, "rb") as fh:
                return base64.b64encode(fh.read()).decode("ascii")
        return "".join(cert.split())  # já está em base64
    raise TypeError("certificado deve ser caminho, bytes ou string base64.")


def _delay(attempt: int, retry_after: Optional[str]) -> float:
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), _MAX_RETRY_AFTER)
        except ValueError:
            pass
    base = min(_MAX_BACKOFF, 0.5 * (2 ** attempt))
    return base + random.uniform(0, base / 4)


def _decode_success(raw: bytes) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FiscalAPIError("Resposta da API não é JSON válido.", body=raw[:500]) from exc
    return decoded if isinstance(decoded, dict) else {"data": decoded}


def _error_from_response(status: int, raw: bytes, headers: Mapping[str, str]) -> FiscalAPIError:
    body: Any
    try:
        body = json.loads(raw.decode("utf-8")) if raw else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        body = raw.decode("utf-8", errors="replace")[:500]

    code: Optional[str] = None
    message = f"Erro HTTP {status}"
    request_id: Optional[str] = None
    if isinstance(body, dict):
        code = body.get("error") or body.get("title")
        detail = body.get("message") or body.get("detail")
        if isinstance(detail, str) and detail:
            message = detail
        elif isinstance(detail, list) and detail:
            message = "; ".join(str(d.get("msg", d)) if isinstance(d, dict) else str(d) for d in detail)
        request_id = body.get("request_id") or None
    elif isinstance(body, str) and body:
        message = body

    kwargs = dict(status_code=status, code=code, request_id=request_id, body=body, headers=headers)
    if status in (401, 403):
        return AuthenticationError(message, **kwargs)
    if status == 402:
        return InsufficientBalanceError(message, **kwargs)
    if status == 429:
        return RateLimitError(message, **kwargs)
    if status >= 500:
        return ServerError(message, **kwargs)
    if 400 <= status < 500:
        return BadRequestError(message, **kwargs)
    return FiscalAPIError(message, **kwargs)
