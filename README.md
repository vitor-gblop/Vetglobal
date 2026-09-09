# VetGlobal - API e Worker de documentos clínicos

Backend assíncrono para cadastro de pets, upload de documentos clínicos e geração
de resumos. A solução é dividida em dois serviços:

- **API:** recebe requisições, persiste pets/documentos/jobs e expõe os endpoints
  públicos.
- **Worker:** recebe jobs, extrai texto de TXT/PDF e produz o resumo determinístico
  ou o resumo com Gemini.

O fluxo foi implementado para atender ao projeto técnico descrito em
[PROJECT.md](./PROJECT.md).

## Arquitetura

```text
Cliente
   |
   v
API (127.0.0.1:8000)
   |-- PostgreSQL: pets, documentos e jobs
   |-- salva arquivos em api/src/main/docs/
   |-- envia o job para o worker
   |
   v
Worker (127.0.0.1:8001)
   |-- fila FIFO em memória
   |-- pode extrair texto de TXT ou PDF em determinados padrões de documento
   |-- pode gerar resumo de conteudo ou usando Gemini
   |
   v
Callback HTTP para a API
   POST /internal/jobs/{job_id}/complete
```

O upload retorna imediatamente `202 Accepted`. O cliente pode consultar o
resultado por `GET /documents/{document_id}` ou usar long-polling.

## Tecnologias

- Python 3.11+
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL
- pytest
- pypdf
- Google Gemini (`google-genai`, opcional)

## Estrutura

```text
api/
├── .env.example
├── requirements.txt
├── main.py
├── src/main/
│   ├── models/          # Modelos SQLAlchemy
│   ├── routes/          # Endpoints públicos e callback interno
│   ├── schemas/         # Contratos Pydantic
│   └── utils/           # Validação e armazenamento de arquivos
└── tests/

worker/
├── .env.example
├── requirements.txt
├── main.py
├── src/
│   ├── AI/              # Integração com Gemini
│   └── main/
│       ├── routes/      # Endpoint de entrada de jobs
│       ├── schemas/     # Contratos Pydantic do worker
│       ├── utils/       # Extração TXT/PDF
│       └── workers/     # Fila e processamento
└── tests/
```

## Pré-requisitos

- Python 3.11+
- PostgreSQL acessível pela API
- `pip`
- Uma chave Gemini somente para a rota de sumarização por IA (essa usa API do google ai studio)

Criação dos ambientes virtuais:

```bash
python3 -m venv api/venv
python3 -m venv worker/venv
```

Acesse usando 

```bash
linux: source venv/bin/activate
windows: .\venv\Scripts\Activate.ps1

```
Instale as dependencias

```bash
pip install -r requirements.txt
```

## Configuração

### API

Copie o arquivo de exemplo e ajuste a conexão do banco:

```bash
cp api/.env.example api/.env
```

Variáveis:

```env
API_BASE_URL="http://127.0.0.1:8000"
WORKER_START_URL="http://127.0.0.1:8001/worker/start"
DATABASE_URL="postgresql+psycopg2://usuario:senha@localhost:5432/vetglobal"
```

### Worker

```bash
cp worker/.env.example worker/.env
```

Variáveis:

```env
WORKER_HOST="127.0.0.1"
WORKER_PORT="8001"
WORKER_RELOAD="false"
GOOGLE_API_KEY=""
GOOGLE_MODEL="gemini-3.5-flash-lite" ('versões anteriores ja não funcionam')
SUMMARY_LANGUAGE="portuguese"
```

`GOOGLE_API_KEY` pode permanecer vazio para usar apenas a sumarização
determinística.  
Para usar `/pets/{pet_id}/documents/ai`, a chave é obrigatória.

## Instalação

```bash
api/venv/bin/pip install -r api/requirements.txt
worker/venv/bin/pip install -r worker/requirements.txt
```

No Windows, use o executável equivalente dentro de `venv/Scripts`.

## Execução

Abra dois terminais na raiz do projeto.

### Worker

```bash
cd worker
./venv/bin/python -m uvicorn main:app --reload
  --host 127.0.0.1 --port 8001
```

### API

```bash
cd api
./venv/bin/python -m uvicorn main:app
  --host 127.0.0.1 --port 8000
```

Verifique o status dos serviços:

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8001/
```

Respostas esperadas:

```json
{"message":"VetGlobal API funcionando"}
```

```json
{"message":"Worker service running"}
```

Também é possível abrir a documentação interativa:

- API: http://127.0.0.1:8000/docs
- Worker: http://127.0.0.1:8001/docs

## Endpoints da API

### Criar um pet

```http
POST /pets/
Content-Type: application/json
```

Exemplo:

```bash
curl -X POST http://127.0.0.1:8000/pets/ \
  -H 'Content-Type: application/json' \
  -d '{"name":"Luna","owner_name":"Ana","species":"Corgi","age":4}'
```

### Upload e resumo determinístico

```http
POST /pets/{pet_id}/documents
Content-Type: multipart/form-data
```

```bash
curl -X POST http://127.0.0.1:8000/pets/1/documents \
  -F 'file=@pet_doc_pdf.pdf;type=application/pdf'
```

Aceita:

- `.txt` com `text/plain`;
- `.pdf` com `application/pdf`.

Resposta:

```json
{
  "id": 1,
  "document_id": 1,
  "job_id": 1,
  "status": "ENQUEUED"
}
```

### Upload e resumo usando IA

```http
POST /pets/{pet_id}/documents/ai
Content-Type: multipart/form-data
```

```bash
curl -X POST http://127.0.0.1:8000/pets/1/documents/ai \
  -F 'file=@pet_doc_pdf.pdf;type=application/pdf'
```

Essa rota usa o mesmo fluxo de upload, mas envia `use_ai=true` ao worker. O
worker extrai o texto e chama o modelo Gemini configurado no `.env`.

### Consultar documento

```http
GET /documents/{document_id}
```

Retorna metadados, pet associado e resumo quando disponível.

### Polling

```http
GET /documents/{document_id}/poll?after_job_id=0
```

O endpoint aguarda até 25 segundos por um job terminal:

- `200`: resumo pronto;
- `200`: falha do job, com `status` e `error`;
- `204 No Content`: timeout sem novo resultado.

Em caso de `204`, repita a consulta usando o mesmo `after_job_id`.

### Callback interno

```http
POST /internal/jobs/{job_id}/complete
```

É chamado pelo worker com um payload como:

```json
{
  "status": "DONE",
  "summary": "Resumo do documento"
}
```

Ou, em caso de falha:

```json
{
  "status": "FAILED",
  "error": "Não foi possível processar o documento"
}
```

Callbacks repetidos não sobrescrevem jobs que já estejam em `DONE` ou `FAILED`.

## Endpoint do worker

### Enfileirar job

```http
POST http://127.0.0.1:8001/worker/start
Content-Type: application/json
```

Payload:

```json
{
  "job_id": 1,
  "document_id": 1,
  "document_content": "...",
  "document_extension": "pdf",
  "use_ai": true,
  "callback_url": "http://127.0.0.1:8000/internal/jobs/1/complete"
}
```

O worker retorna `202 Accepted` e processa o job em sua fila FIFO.

## Processamento de arquivos

### TXT

O conteúdo é lido como UTF-8, com fallback para Latin-1 na API, e enviado ao
worker como texto.

### PDF

O arquivo é enviado pela API em Base64. O worker usa `pypdf` para extrair o
texto. O modelo [pet_doc_pdf.pdf](./pet_doc_pdf.pdf) é usado como referência de
formato e reconhece campos como:

- Nome do pet;
- Idade;
- Nome do proprietário;
- Raça;
- Sintomas;
- Notas clínicas.

PDFs escaneados sem camada de texto não são processados por OCR nesta versão e
resultam em falha quando não há texto extraível.

## Testes

Os testes são separados por serviço:

```bash
./api/venv/bin/pytest -q api/tests
./worker/venv/bin/pytest -q worker/tests
```

Os testes cobrem:

- validação de uploads;
- leitura de TXT;
- extração do PDF de referência;
- rejeição de PDF inválido;
- resumo determinístico;
- caminho de sumarização com IA usando mock;
- callback do worker;
- validação Pydantic dos jobs.

Nenhum teste chama a API real do Google. O caminho de IA é isolado com mock para
manter a suíte rápida e determinística.

## Decisões técnicas

- **API e worker separados:** permitem escalar e reiniciar o processamento sem
  bloquear os endpoints públicos.
- **Pydantic:** valida os contratos de pets, jobs e callbacks antes da execução.
- **Fila FIFO em memória:** suficiente para a simulação técnica, simples de
  testar e adequada ao escopo do projeto. Em produção real, o correto é ser substituída
  por uma fila externa (por exemplo, Redis, RabbitMQ ou SQS), com
  confirmação de processamento, retries, dead-letter queue e monitoramento.
- **Callback HTTP:** permite que o worker atualize o estado persistido na API.
- **Polling de 25 segundos:** evita manter uma conexão indefinida e retorna
  `204` quando não há atualização.
- **Armazenamento local:** mantém a implementação pequena e permite consultar o
  caminho salvo no documento.

## Limitações e próximos passos

Intencionalmente fora do escopo atual:

- fila durável ou distribuída;
- retries com backoff e dead-letter queue;
- storage S3/MinIO;
- OCR para PDFs escaneados;
- autenticação e autorização;
- isolamento por tenant;
- migrations com Alembic;
- observabilidade e métricas;
- execução paralela de múltiplos consumidores;
- idempotência de upload.

Para produção, as primeiras melhorias recomendadas são trocar a fila em memória
por Redis/RabbitMQ/SQS, usar storage compartilhado, adicionar autenticação
entre serviços e configurar retries. Também é necessário remover a recriação
destrutiva de tabelas na inicialização da API e substituí-la por migrations.

## Resolução de problemas

### `DATABASE_URL não foi configurada`

Verifique se `api/.env` existe e contém uma URL PostgreSQL válida.

### Worker indisponível

Confirme se o worker está rodando na porta configurada e se
`WORKER_START_URL` aponta para `/worker/start`.

### Erro na sumarização por IA

Confirme `GOOGLE_API_KEY`, `GOOGLE_MODEL` e a conectividade com a API do Google.
Sem a chave, use `/pets/{pet_id}/documents` para o resumo determinístico.

### PDF sem texto

O PDF precisa ter uma camada de texto extraível. PDFs compostos apenas por
imagens exigem OCR, que ainda não está implementado.