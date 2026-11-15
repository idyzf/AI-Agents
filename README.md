# Bot Qwen local no Discord

O Ollama roda **direto no Mac**, para usar a GPU do M1. Só o bot do Discord roda no Docker.

## Primeira vez

1. Instale e abra o Ollama: `brew install ollama` e depois `brew services start ollama`, ou instale o app de https://ollama.com
2. Baixe o modelo: `ollama pull qwen3.5:4b` (cerca de 3 GB). Para respostas melhores, use `qwen3.5:9b` (cerca de 6 GB de RAM) e troque `MODEL_NAME` no `docker-compose.yml`.
3. Crie o `.env` com:
   ```
   DISCORD_TOKEN=seu_token
   ALLOWED_USER_IDS=seu_id_do_discord   # opcional: só esses usuários podem usar o bot
   ```
4. Suba o bot: `docker compose up --build`

## Ligar e desligar

| | Ligar | Desligar |
|---|---|---|
| Bot | `docker compose up` | `Ctrl+C` ou `docker compose down` |
| Ollama | `brew services start ollama` | `brew services stop ollama` (ou "Quit" no ícone do app) |

O Ollama tira o modelo da memória depois de cerca de 5 minutos sem uso.

## Usando no Discord

- Em servidores, marque o bot (`@bot pergunta`). Em DMs, basta escrever.
- `!reset` apaga a memória da conversa no canal.
- `!<agente> mensagem` fala com um agente específico.

## Criando agentes

Adicione uma entrada em `AGENTS` no `agent.py`, com o papel do agente e as ferramentas dele. Ele já fica disponível como `!nome` no Discord.

## Teste rápido sem Discord

`python3 agent.py` (precisa das dependências instaladas: `pip install -r requirements.txt`)
