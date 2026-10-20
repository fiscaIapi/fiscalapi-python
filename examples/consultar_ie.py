"""Exemplo: consulta de Inscrição Estadual com tratamento de erros.

Uso:  FISCALAPI_API_KEY=... python examples/consultar_ie.py MT 12345678909
"""
import sys

from fiscalapi_br import FiscalAPI, FiscalAPIError, InsufficientBalanceError

uf, cpf = sys.argv[1], sys.argv[2]
api = FiscalAPI()  # lê FISCALAPI_API_KEY

try:
    resp = api.consultar_ie(uf=uf, cpf=cpf)
except InsufficientBalanceError as exc:
    print("Sem saldo ou sem plano ativo:", exc.message)
    sys.exit(1)
except FiscalAPIError as exc:
    print("Erro:", exc)
    sys.exit(1)

for inscricao in resp.get("results", []):
    print(inscricao["inscricao_estadual"], inscricao.get("situacao_ie"), inscricao.get("municipio"))
