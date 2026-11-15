# Bot Qwen local no Discord

O Ollama roda **direto no Mac**, para usar a GPU do M1. Só o bot do Discord roda no Docker.

## Primeira vez

1. Instale o Ollama (`brew install ollama`) e inicie com `./start-ollama.sh`. O script aplica limites de memória e não liga o Ollama sozinho no login.
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
| Ollama | `./start-ollama.sh` | `Ctrl+C` no terminal dele |

O Ollama tira o modelo da memória depois de cerca de 5 minutos sem uso.

## Usando no Discord

- Em servidores, marque o bot (`@bot pergunta`). Em DMs, basta escrever.
- `!reset` apaga a memória da conversa no canal.
- `!<agente> mensagem` fala com um agente específico.

## Assistente de agenda e emails

Todo dia às 7h (horário de Brasília), o bot manda por DM os eventos do dia e um resumo dos emails das últimas 24h. Na segunda, manda também a agenda da semana. Na DM, você também pode pedir na hora: `!hoje`, `!semana`, `!emails` ou `!bomdia`. Esses comandos só funcionam para o dono do bot.

**Ele só lê, nunca altera nada:**
- O token do Google tem só permissões de leitura (`calendar.readonly` e `gmail.readonly`). O próprio Google recusa qualquer tentativa de apagar, editar ou enviar.
- O bot se recusa a rodar se o token tiver qualquer permissão além dessas.
- O modelo que escreve os resumos não tem ferramentas: só recebe texto e devolve texto.
- A pasta `secrets/` entra no container como somente-leitura e não vai para o git.

**Configuração (uma vez):**
1. Em https://console.cloud.google.com, crie um projeto e ative a **Gmail API** e a **Google Calendar API**.
2. Em "Google Auth Platform", configure a tela de consentimento como **External** e adicione seu email como usuário de teste.
3. Crie um **OAuth client ID** do tipo **Desktop app**, baixe o JSON e salve como `secrets/credentials.json`.
4. No Mac, rode `pip3 install google-auth-oauthlib google-api-python-client` e depois `python3 auth_google.py`. Faça login e aprove o acesso somente-leitura.
5. Reinicie o bot: `docker compose up --build`.

**Mais de uma conta:** adicione a outra conta como usuária de teste no Google Cloud e rode `python3 auth_google.py <nome>`, por exemplo `python3 auth_google.py conta2`. Isso salva `secrets/token_<nome>.json`. O bot junta os eventos de todas as contas, mostrando de qual conta veio cada um, e separa os emails por conta. Não precisa reiniciar o bot.

Enquanto o app estiver em modo "Testing" no Google, o login expira a cada 7 dias e é preciso rodar `auth_google.py` de novo. Para não expirar, mude o app para "In production". O Google vai mostrar um aviso de "app não verificado", que você pode aceitar, já que o app é seu.

Se o Mac estiver dormindo às 7h, o resumo daquele dia não é enviado. Use `!bomdia` quando abrir o Mac.

## Criando agentes

Adicione uma entrada em `AGENTS` no `agent.py`, com o papel do agente e as ferramentas dele. Ele já fica disponível como `!nome` no Discord.

## Teste rápido sem Discord

`python3 agent.py` (precisa das dependências instaladas: `pip install -r requirements.txt`)
