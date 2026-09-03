# Classroom50 AI Autograder

Motor de avaliação automática *headless* baseado em **LangGraph** e **Gemini API** (`gemini-3.6-flash`) desenvolvido para o ecossistema **Classroom50**.

---

## 📌 Descrição

O **Classroom50 AI Autograder** é um serviço CLI containerizado responsável por processar e avaliar submissões de exercícios de programação (ex: Java) em pipelines de CI/CD ou ambientes autônomos. Ele compara o código enviado pelo aluno com uma solução de referência (gabarito) e as instruções da atividade (enunciado), produzindo um relatório pedagógico detalhado e estruturado em formato JSON.

---

## 🏗️ Arquitetura e Fluxo de Execução

O fluxo de processamento segue as seguintes etapas:

```text
+-------------------------------------------------------------+
|                      ENTRADA DE VOLUMES                     |
|  - Arquivo do Aluno (.java)                                 |
|  - Gabarito de Referência (.java)                           |
|  - Enunciado da Tarefa (.md)                                |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                     ORQUESTRADOR LANGGRAPH                  |
|  - Leitura e injeção dos arquivos no estado do grafo        |
|  - Carregamento e montagem dos templates de prompts        |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                    GEMINI STRUCTURED OUTPUT                 |
|  - Utilização do cliente de chat (`client.chats.create`)     |
|  - Forçamento de retorno estrito em JSON (`application/json`)|
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                       JSON DE SAÍDA                         |
|  - Gravação do resultado no caminho especificado (--output) |
+-------------------------------------------------------------+
```

---

## 🔑 Variáveis de Ambiente Necessárias

- **`GEMINI_API_KEY`**: Chave de API da Google Gemini exigida para autenticação com o modelo `gemini-3.6-flash`.

---

## 🔨 Como Construir a Imagem Docker

Para construir a imagem Docker localmente, execute o seguinte comando na raiz do repositório:

```bash
docker build -t markinsilva/classroom50-ai-autograder:v2.0 .
```

---

## 🚀 Como Executar via Docker CLI

O container aceita quatro argumentos principais de linha de comando:
- `--aluno`: Caminho do arquivo de código enviado pelo aluno.
- `--gabarito`: Caminho do arquivo de gabarito de referência.
- `--enunciado`: Caminho do arquivo de enunciado da atividade.
- `--output`: Caminho onde o arquivo JSON de saída será gerado.

### Exemplo de Comando

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
- **`sugestao_correcao`**: Trecho de código Java ajustado/corrigido.
