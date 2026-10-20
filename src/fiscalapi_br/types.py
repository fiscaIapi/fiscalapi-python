"""Tipos (TypedDict) das respostas mais usadas da FiscalAPI.

As respostas são dicionários comuns; estes tipos servem para autocompletar no
editor e para checagem estática. Campos novos podem aparecer sem aviso — o
SDK não descarta nada do que a API devolve.
"""
from __future__ import annotations

from typing import List, Literal, Optional, TypedDict

StatusFonte = Literal["success", "error", "timeout", "skipped"]
StatusCertidao = Literal[
    "negativa",
    "positiva",
    "positiva_com_efeitos_de_negativa",
    "nao_contribuinte",
    "sem_certidao",
    "erro",
]


class SourceStatus(TypedDict, total=False):
    status: StatusFonte
    error_code: str
    error_message: str


class CnaeSecundario(TypedDict, total=False):
    codigo: str
    descricao: str


class InscricaoEstadual(TypedDict, total=False):
    inscricao_estadual: str
    razao_social: str
    nome_fantasia: str
    situacao_ie: str
    uf_ie: str
    tipo_ie: str
    logradouro: str
    complemento: str
    bairro: str
    numero: str
    municipio: str
    municipio_ibge: str
    cep: str
    regime_pagamento: str
    data_situacao: str
    situacao_contribuinte: str
    data_inicio_atividade: str
    cnae_codigo: str
    cnae_descricao: str
    regime_apuracao_icms: str
    situacao_nfe: str
    cpf_cnpj: str
    situacao_cadastral: str
    cnaes_secundarios: Optional[List[CnaeSecundario]]


class ConsultaIEResponse(TypedDict, total=False):
    request_id: str
    document: str
    document_type: str
    uf: str
    cached: bool
    results: List[InscricaoEstadual]


class IEPorUF(TypedDict, total=False):
    uf: str
    source_status: SourceStatus
    results: List[InscricaoEstadual]


class ConsultaIETodosResponse(TypedDict, total=False):
    request_id: str
    document: str
    document_type: str
    cached_ufs: List[str]
    results: List[IEPorUF]
    complete: bool


class CNPJResult(TypedDict, total=False):
    razao_social: str
    nome_fantasia: str
    situacao_cadastral: str
    data_situacao_cadastral: str
    cnae_principal_codigo: str
    cnae_principal_descricao: str
    cnaes_secundarios: List[dict]
    natureza_juridica: str
    capital_social: str
    endereco: dict
    qsa: List[dict]
    porte: str


class CNPJResponse(TypedDict, total=False):
    request_id: str
    cnpj: str
    cached: bool
    source_status: SourceStatus
    result: Optional[CNPJResult]


class Certidao(TypedDict, total=False):
    status: StatusCertidao
    status_raw: str
    validade: str
    validade_iso: str
    emissao: str
    emissao_iso: str
    protocolo: str
    pdf_base64: str
    url_verificacao: str
    codigo_autenticacao: str


class CNDResponse(TypedDict, total=False):
    request_id: str
    document: str
    document_type: str
    uf: str
    cached: bool
    source_status: SourceStatus
    result: Optional[Certidao]


class CNDPorUF(TypedDict, total=False):
    uf: str
    source_status: SourceStatus
    result: Optional[Certidao]


class CNDTodosResponse(TypedDict, total=False):
    request_id: str
    document: str
    document_type: str
    results: List[CNDPorUF]


class CertidaoFederal(Certidao, total=False):
    tipo: Literal["cndt", "cnd_federal", "crf_fgts"]
    orgao: str
    modo: Literal["consulta", "emissao"]


class CertidaoFederalResponse(TypedDict, total=False):
    request_id: str
    document: str
    document_type: str
    cached: bool
    source_status: SourceStatus
    result: Optional[CertidaoFederal]


class CertidoesTodasResponse(TypedDict, total=False):
    request_id: str
    document: str
    document_type: str
    cnd_estaduais: Optional[CNDTodosResponse]
    certidoes_federais: List[CertidaoFederalResponse]


class NfeXmlResultado(TypedDict, total=False):
    chave: str
    status: str
    cstat: str
    mensagem: str
    from_cache: bool
    manifestacao: Optional[str]
    xml: Optional[str]


class NfeXmlResponse(TypedDict, total=False):
    request_id: str
    total: int
    com_dado: int
    creditos_cobrados: int
    resultados: List[NfeXmlResultado]


class SigefParcela(TypedDict, total=False):
    parcel_id: str
    codigo_parcela: str
    denominacao: str
    area_ha: float
    municipio: str
    uf: str
    codigo_ibge: str
    detentor: str
    matricula: str
    cns: str
    status: str
    data_certificacao: str
    natureza: str
    codigo_sncr: str
    cartorio: str
    geometria_wkt: str
    vertices: List[dict]
    confrontantes: List[dict]


class SigefResult(TypedDict, total=False):
    total_parcelas: int
    area_total_ha: float
    parcelas: List[SigefParcela]


class SigefResponse(TypedDict, total=False):
    request_id: str
    document: str
    document_type: str
    cached: bool
    source_status: SourceStatus
    result: Optional[SigefResult]


class SigefParcelaResponse(TypedDict, total=False):
    request_id: str
    parcel_id: str
    cached: bool
    consultado_em: str
    completo: bool
    avisos: List[str]
    source_status: SourceStatus
    result: Optional[SigefParcela]


class CnirResponse(TypedDict, total=False):
    request_id: str
    document: str
    document_type: str
    source_status: SourceStatus
    pessoa_fisica: Optional[dict]
    pessoa_juridica: Optional[dict]
    imoveis_cafir: List[dict]
    total_imoveis: int
    total_imoveis_ativos: int


class PerfilProdutorResponse(TypedDict, total=False):
    request_id: str
    document: str
    receita_federal: Optional[CNPJResponse]
    inscricoes_estaduais: Optional[ConsultaIETodosResponse]
    cnd_estaduais: Optional[CNDTodosResponse]
    certidoes_federais: List[CertidaoFederalResponse]
    cnir: Optional[CnirResponse]
