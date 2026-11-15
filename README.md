# Assistente pessoal local no Discord

Bot do Discord com um modelo de IA que roda 100% no Mac: Qwen 3.5 via Ollama, usando a GPU do M1.

- **Conversa:** responde quando é marcado num servidor ou por DM.
- **Agenda e emails:** todo dia às 7h manda por DM os eventos do dia e um resumo dos emails das últimas 24h. Na segunda, inclui a agenda da semana. Funciona com uma ou mais contas Google.
- **Somente leitura:** o acesso ao Google é só de leitura, e o modelo não tem ferramentas. Ele nunca apaga, edita ou envia nada.

## Como rodar

```bash
./start-ollama.sh            # Ollama com limites de memória
docker compose up --build    # bot do Discord
python3 auth_google.py       # uma vez por conta Google (veja o início do arquivo)
```

Segredos ficam em `.env` (token do Discord) e `secrets/` (Google), ambos fora do git.

## Estrutura

| Arquivo | Função |
|---|---|
| `discord_bot.py` | Bot, comandos e agendamento dos resumos |
| `agent.py` | Configuração do modelo e lista de agentes |
| `briefing.py` | Monta os resumos de agenda e emails |
| `google_readonly.py` | Leitura do Google Calendar e Gmail, somente leitura |
| `auth_google.py` | Login no Google, feito uma vez por conta |
