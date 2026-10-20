# FiscalAPI — SDK Python

Cliente Python da [FiscalAPI](https://fiscalapi.com.br): Inscrição Estadual nos 27 estados, CNPJ, certidões (CND estadual, CND Federal, CNDT, CRF/FGTS), XML de NF-e por chave, SIGEF, CNIR e perfil do produtor rural.

- Zero dependências (só a biblioteca padrão).
- Python 3.9 ou superior.
- Novas tentativas automáticas em `429` e em falhas temporárias.
- Erros tipados para chave inválida, falta de saldo e limite de requisições.

## Instalação

```bash
pip install fiscalapi-br
```

## Antes de começar

1. Crie sua conta em [app.fiscalapi.com.br](https://app.fiscalapi.com.br) e copie a chave de API no painel.
2. **O uso pela API exige um plano ativo ou créditos.** As consultas gratuitas do mês valem só no painel; pela API, uma conta sem plano recebe `402` (`InsufficientBalanceError`).
3. Planos e consumo de créditos: [docs.fiscalapi.com.br](https://docs.fiscalapi.com.br/docs/referencia/plans-and-limits).

## Uso rápido

```python
from fiscalapi_br import FiscalAPI

api = FiscalAPI("sua-chave")          # ou defina FISCALAPI_API_KEY

resp = api.consultar_ie(uf="MT", cpf="12345678909")
for ie in resp["results"]:
    print(ie["inscricao_estadual"], ie["situacao_ie"], ie["municipio"])
```

## Métodos

| Método | Endpoint | O que retorna |
|---|---|---|
| `consultar_ie(uf, cpf=/cnpj=/ie=, secundarias=False)` | `GET /api/consultar` | Inscrições estaduais em uma UF |
| `consultar_ie_todos(cpf=/cnpj=/ie=, secundarias=False)` | `GET /api/consultar-ie-todos` | Inscrições em todos os estados |
| `consultar_cnpj(cnpj, force_fresh=False)` | `GET /api/consultar-cnpj` | Dados cadastrais da Receita Federal |
| `consultar_cnd(uf, cpf=/cnpj=)` | `GET /api/consultar-cnd` | CND estadual (ICMS) com PDF |
| `consultar_cnd_todos(cpf=/cnpj=)` | `GET /api/consultar-cnd-todos` | CND estadual em todos os estados disponíveis |
| `consultar_cnd_federal(cpf=/cnpj=, emitir_nova=False)` | `GET /api/consultar-cnd-federal` | CND Federal (Receita Federal + PGFN) |
| `consultar_cndt(cpf=/cnpj=)` | `GET /api/consultar-cndt` | Certidão de débitos trabalhistas |
| `consultar_crf_fgts(cpf=/cnpj=)` | `GET /api/consultar-crf-fgts` | Regularidade do FGTS |
| `consultar_certidoes_todas(cpf=/cnpj=, skip_estaduais=False)` | `GET /api/certidoes-todas` | Todas as certidões em uma chamada |
| `consultar_nfe_xml(chave, certificado=, senha=, manifestar=True)` | `POST /api/consultar-nfe-xml` | XML completo da NF-e |
| `consultar_sigef(cpf=/cnpj=)` | `GET /api/consultar-sigef` | Parcelas certificadas no SIGEF/INCRA |
| `consultar_sigef_parcela(uuid, force_fresh=False)` | `GET /api/consultar-sigef-parcela` | Uma parcela com polígono, vértices e confrontantes |
| `consultar_cnir(cpf=/cnpj=)` | `GET /api/consultar-cnir` | Imóveis rurais no CNIR/CAFIR |
| `perfil_produtor(cpf=/cnpj=)` | `GET /api/perfil-produtor` | Perfil consolidado do produtor |

Informe **um** documento por chamada (`cpf`, `cnpj` ou, onde couber, `ie`). Pontuação é aceita. Todas as respostas são `dict` com o JSON da API; os tipos em `fiscalapi_br.types` ajudam no autocompletar.

## Exemplos

### Inscrição Estadual em todos os estados

```python
resp = api.consultar_ie_todos(cnpj="12.345.678/0001-95")
if not resp.get("complete", True):
    print("Algum estado não respondeu; tente de novo antes de concluir que não há IE.")
for uf in resp["results"]:
    for ie in uf["results"]:
        print(uf["uf"], ie["inscricao_estadual"], ie["situacao_ie"])
```

### CNPJ

```python
empresa = api.consultar_cnpj("12345678000195")
print(empresa["result"]["razao_social"], empresa["result"]["situacao_cadastral"])

# Dado atual, sem cache (consome mais créditos):
api.consultar_cnpj("12345678000195", force_fresh=True)
```

### Certidões com PDF

```python
import base64

cnd = api.consultar_cnd("MT", cpf="12345678909")
resultado = cnd["result"]
print(resultado["status"], resultado["validade_iso"])
if resultado.get("pdf_base64"):
    with open("cnd-mt.pdf", "wb") as f:
        f.write(base64.b64decode(resultado["pdf_base64"]))

federal = api.consultar_cnd_federal(cnpj="12345678000195")
trabalhista = api.consultar_cndt(cnpj="12345678000195")
fgts = api.consultar_crf_fgts(cnpj="12345678000195")
```

O campo `status` vem como `negativa`, `positiva`, `positiva_com_efeitos_de_negativa`, `nao_contribuinte`, `sem_certidao` ou `erro`.

### XML de NF-e por chave

```python
resp = api.consultar_nfe_xml(
    "35260112345678000195550010000012341000012345",
    certificado="certificado.pfx",   # caminho, bytes do arquivo ou base64
    senha="senha-do-certificado",
)
nota = resp["resultados"][0]
if nota["status"] == "ok":
    with open(f"{nota['chave']}.xml", "w", encoding="utf-8") as f:
        f.write(nota["xml"])
else:
    print(nota["status"], nota["mensagem"])
```

O certificado A1 precisa ser de um participante da nota (emitente, destinatário, transportador ou autorizado) e **não é armazenado** pela API. Só há cobrança quando o XML é devolvido.

### Imóvel rural

```python
sigef = api.consultar_sigef(cpf="12345678909")
for parcela in sigef["result"]["parcelas"]:
    print(parcela["denominacao"], parcela["area_ha"], parcela["municipio"], parcela["uf"])

parcela = api.consultar_sigef_parcela("0f1e2d3c-4b5a-6978-8a9b-0c1d2e3f4a5b")
print(parcela["result"]["geometria_wkt"])

cnir = api.consultar_cnir(cpf="12345678909")
print(cnir["total_imoveis"], "imóveis")
```

### Perfil do produtor

```python
perfil = api.perfil_produtor(cpf="12345678909")
```

## Status da fonte

Uma resposta `200` pode trazer `source_status.status` diferente de `success` (por exemplo, `timeout` quando o órgão não respondeu a tempo). Confira esse campo antes de concluir que o documento não tem registro.

## Erros

```python
from fiscalapi_br import (
    FiscalAPIError, AuthenticationError, InsufficientBalanceError,
    RateLimitError, BadRequestError, ServerError, APIConnectionError,
)

try:
    api.consultar_ie(uf="SP", cnpj="12345678000195")
except AuthenticationError:
    ...  # chave ausente, inválida ou revogada (401/403)
except InsufficientBalanceError as e:
    print(e.consultas_restantes)  # sem plano ou saldo esgotado (402)
except RateLimitError as e:
    print(e.retry_after)  # limite por minuto do plano (429)
except BadRequestError as e:
    print(e.code, e.message)  # parâmetro ausente ou inválido (400/422)
except FiscalAPIError as e:
    print(e.status_code, e.request_id)  # demais erros; informe o request_id ao suporte
```

## Novas tentativas e timeout

```python
api = FiscalAPI("sua-chave", timeout=200, max_retries=3)
```

- `429`: o SDK espera o tempo do cabeçalho `Retry-After` e tenta de novo.
- `500`, `502`, `503`, `504` e falhas de rede: novas tentativas com espera exponencial, **só em consultas GET**. A consulta de NF-e (POST) não é repetida automaticamente.
- Algumas consultas (NF-e, SIGEF) podem levar até 3 minutos; o timeout padrão é 200 s.

## Links

- Documentação: [docs.fiscalapi.com.br](https://docs.fiscalapi.com.br)
- Painel: [app.fiscalapi.com.br](https://app.fiscalapi.com.br)
- Suporte: contato@fiscalapi.com.br

## Licença

MIT
