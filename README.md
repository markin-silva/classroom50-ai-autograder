# Classroom50 AI Autograder

Motor de avaliação automática *headless* baseado em **LangGraph** e **Gemini API** (`gemini-3.6-flash`) desenvolvido para o ecossistema **Classroom50**.

---

## 📌 Descrição

O **Classroom50 AI Autograder** é um serviço CLI containerizado responsável por processar e avaliar submissões de exercícios de programação (ex: Java) em pipelines de CI/CD ou ambientes autônomos. Ele compara o código enviado pelo aluno com uma solução de referência (gabarito) e as instruções da atividade (enunciado), produzindo um relatório pedagógico estruturado em formato JSON.

O serviço foi projetado para **nunca quebrar o pipeline**: mesmo quando a API do Gemini está indisponível, ele grava um JSON de fallback e encerra com sucesso (`exit 0`).

---

## 🏗️ Arquitetura e Fluxo de Execução

O fluxo de processamento segue as seguintes etapas:

```text
+-------------------------------------------------------------+
|                      ENTRADA DE VOLUMES                     |
|  - Diretório do aluno (arquivos .java)                      |
|  - Diretório do gabarito (arquivos .java)                   |
|  - Diretório do enunciado (arquivos .md)                    |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                     ORQUESTRADOR LANGGRAPH                  |
|  - Leitura recursiva e injeção dos arquivos no estado       |
|  - Montagem dos prompts (system + user template)            |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                    GEMINI STRUCTURED OUTPUT                 |
|  - Cliente de chat (`client.chats.create`)                  |
|  - Retorno estrito em JSON (`application/json`)             |
|  - Até 3 tentativas com backoff (5s, 10s) em caso de erro   |
|  - Validação do contrato da resposta a cada tentativa       |
+------------------------------+------------------------------+
                               |
              +----------------+----------------+
              | sucesso                         | falha em todas as
              |                                 | tentativas ou sem
              v                                 | GEMINI_API_KEY
+----------------------------+                  v
|  JSON DE SAÍDA             |   +------------------------------+
|  (resultado da IA)         |   |  JSON DE FALLBACK            |
+----------------------------+   |  (avaliacao: Parcialmente    |
              |                 |   Certo + aviso de instabi-  |
              +--------+--------+   lidade)                    |
                       v        +------------------------------+
+-------------------------------------------------------------+
|  Gravação em --output e encerramento com exit(0)            |
+-------------------------------------------------------------+
```

---

## 🔑 Variáveis de Ambiente

- **`GEMINI_API_KEY`**: Chave de API da Google Gemini para autenticação com o modelo `gemini-3.6-flash`. Se ausente, o serviço não falha: grava o JSON de fallback e encerra com `exit(0)`.

---

## 🔨 Como Construir a Imagem Docker

Para construir a imagem Docker localmente, execute o seguinte comando na raiz do repositório:

```bash
docker build -t markinsilva/classroom50-ai-autograder:v2.0 .
```

---

## 🚀 Como Executar via Docker CLI

O container aceita os seguintes argumentos. Todos têm valores padrão apontando para os caminhos montados pelo Docker, então podem ser omitidos quando os volumes estiverem nesses locais:

| Argumento     | Padrão                           | Descrição                                              |
|---------------|----------------------------------|--------------------------------------------------------|
| `--aluno`     | `/app/submission`                | Diretório com os arquivos `.java` do aluno.            |
| `--gabarito`  | `/app/reference`                 | Diretório com os arquivos `.java` do gabarito.         |
| `--enunciado` | `/app/reference`                 | Diretório com os arquivos `.md` do enunciado.          |
| `--output`    | `/app/output/results.json`       | Caminho do JSON de saída.                              |

Os diretórios são lidos recursivamente. Também é possível passar um arquivo individual para `--aluno` e `--gabarito`.

### Exemplo de Comando

```bash
docker run --rm \
  -e GEMINI_API_KEY="SEU_GEMINI_API_KEY" \
  -v "$(pwd)/test_env/aluno:/app/submission" \
  -v "$(pwd)/test_env/reference:/app/reference" \
  -v "$(pwd)/test_env/output:/app/output" \
  markinsilva/classroom50-ai-autograder:v2.0
```

Com os valores padrão, o comando acima já funciona. Para usar caminhos específicos, passe os argumentos explicitamente:

```bash
docker run --rm \
  -e GEMINI_API_KEY="SEU_GEMINI_API_KEY" \
  -v "$(pwd)/test_env/aluno:/app/aluno" \
  -v "$(pwd)/test_env/reference:/app/reference" \
  -v "$(pwd)/test_env/output:/app/output" \
  markinsilva/classroom50-ai-autograder:v2.0 \
  --aluno "/app/aluno/ContaBancaria.java" \
  --gabarito "/app/reference/Gabarito.java" \
  --enunciado "/app/reference/enunciado.md" \
  --output "/app/output/results.json"
```

---

## 🔁 Tratamento de Falhas

- **Retry com backoff:** erros da API (como 503 e 429) ou respostas fora do contrato disparam até **3 tentativas**, com pausa de 5s e depois 10s entre elas.
- **Validação:** a resposta só é aceita se `avaliacao` for `Certo`, `Parcialmente Certo` ou `Errado`, e se as demais chaves forem strings. Caso contrário, a tentativa conta como falha.
- **Fallback:** se todas as tentativas falharem ou a `GEMINI_API_KEY` não estiver definida, é gravado o seguinte JSON, com o motivo registrado no stderr:

```json
{
  "avaliacao": "Parcialmente Certo",
  "justificativa": "Ocorreu uma instabilidade temporária na avaliação via IA.",
  "dica_correcao": "Por favor, aguarde alguns minutos e execute no terminal o comando `gh student submit` para tentar novamente.",
  "sugestao_correcao": ""
}
```

- **Código de saída:** o processo sempre termina com `exit(0)`, para que o Job do GitHub Actions permaneça verde. Por isso, falhas de API e de configuração aparecem apenas no log e no conteúdo do JSON, não no status do Job.

---

## 📄 Estrutura do JSON de Saída Esperado

O resultado da avaliação é gravado no arquivo especificado em `--output` e segue rigorosamente o formato de *Structured Output*:

```json
{
  "avaliacao": "Parcialmente Certo",
  "justificativa": "O aluno criou a classe ContaBancaria conforme solicitado, porém não declarou o atributo privado 'saldo' especificado no gabarito de referência.",
  "dica_correcao": "Certifique-se de adicionar todos os atributos solicitados no enunciado com seus respectivos modificadores de acesso (ex: private).",
  "sugestao_correcao": "public class ContaBancaria {\n    private double saldo;\n}"
}
```

### Descrição dos Campos:
- **`avaliacao`**: Status pedagógico (`Certo`, `Parcialmente Certo` ou `Errado`).
- **`justificativa`**: Explicação técnica sucinta sobre o desempenho do código.
- **`dica_correcao`**: Dicas pedagógicas orientando o aluno sem necessariamente fornecer o código pronto.
- **`sugestao_correcao`**: Trecho de código Java ajustado/corrigido. Vem como string vazia quando não há sugestão de código.
