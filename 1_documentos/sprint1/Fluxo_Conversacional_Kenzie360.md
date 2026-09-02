# Fluxo Conversacional da Kenzie — Especificação (Projeto Kenzie 360)

> Documento de referência do **modelo de atendimento** reproduzido na base sintética.
> Define quem fala, em que ordem, quais caminhos existem, como cada conversa termina
> e como os dados pessoais são tratados. É a "máquina de estados" do dataset.

---

## 1. Canais e papéis

| Papel | Quem é | Onde atua |
|---|---|---|
| **Cliente** | Correntista (CDE, Nacional ou PJ) | WhatsApp |
| **Kenzie** | Assistente virtual (bot V1, baseado em script) | **Somente WhatsApp**, via Take Blip |
| **Atendente Humano** | Time de especialistas do banco | WhatsApp, **Telefone** ou **E-mail** |

O campo `canal_entrada` é sempre `WhatsApp` (a Kenzie só existe lá).
O campo `canal_humano` só é preenchido quando um humano efetivamente assume.

**Identidade padronizada:** a Kenzie sempre se apresenta com a mesma frase canônica,
uma por idioma — *"Olá! Sou a Kenzie, assistente virtual do banco."* / *"Hello! I'm
Kenzie, the bank's virtual assistant."* / *"Hola! Soy Kenzie, asistente virtual del banco."*

---

## 2. Origem da conversa

Toda conversa nasce de um destes dois gatilhos (`origem`):

### 2.1 Receptivo (~82%)
O **cliente** manda a primeira mensagem. A Kenzie responde já se identificando
(saudação canônica + resposta do tema) na mesma mensagem.

```
[01] Cliente:  "Meu PIX foi bloqueado sem aviso!"
[02] Kenzie:   "Olá! Sou a Kenzie, assistente virtual do banco. Sinto muito pelo
                transtorno. Bloqueios ocorrem por segurança. Já estou verificando."
```

### 2.2 Ativo (~18%) — disparo do banco
A **Kenzie** manda a primeira mensagem (campanha/aviso disparado pelo Blip).
Três desfechos possíveis:

- **Sem resposta** (~36% dos ativos) → cliente ignora. Status: `Sem resposta (disparo ativo)`.
- **Opt-out** (~19%) → cliente pede descadastro. Status: `Opt-out / descadastro`.
- **Engaja** (~45%) → segue para o fluxo de atendimento normal.

---

## 3. Máquina de estados (fluxo completo)

```
                    ┌──────────────────────────┐
                    │        ORIGEM            │
                    └───────┬──────────┬───────┘
                  Receptivo │          │ Ativo (disparo Kenzie)
                            │          ├── ignora ──► Sem resposta
                            │          ├── recusa ──► Opt-out
                            │          └── engaja ──┐
                            ▼                       ▼
                    ┌───────────────────────────────────┐
                    │  RUÍDO? (5%, só receptivo)        │
                    │  engano · já resolveu · "oi/teste"│──► encerra (Não aplicável)
                    └───────────────┬───────────────────┘
                                    ▼
                    ┌───────────────────────────────────┐
                    │  ATENDIMENTO PELA KENZIE          │
                    │  · abertura do cliente            │
                    │  · resposta do bot                │
                    │  · NLU miss (15%): bot erra e     │
                    │    o cliente corrige              │
                    │  · 1 a 4 rodadas de vai-e-vem     │
                    └───────────────┬───────────────────┘
                                    ▼
                     resolve? (p_bot por assunto, ~25%)
                    ┌───────────────┴───────────────────┐
                   SIM                                  NÃO
                    ▼                                    ▼
         ┌────────────────────┐         ┌────────────────────────────────┐
         │ Resolvida pelo bot │         │  abandona? (por arquétipo)     │
         │ fecho do cliente + │         │  ├─ SIM ──► Abandonada         │
         │ fecho da Kenzie    │         │  │          (resolvida =       │
         └────────────────────┘         │  │           Desconhecido)     │
                                        │  ├─ escala p/ humano (~72%)    │
                                        │  └─ desiste s/ humano ──►      │
                                        │       Encerrada sem resolução  │
                                        └──────────────┬─────────────────┘
                                                       ▼
                                        ┌──────────────────────────────┐
                                        │  TRANSFERÊNCIA               │
                                        │  transferencia_iniciada=True │
                                        │  ├─ 10%: some na fila ──►    │
                                        │  │   Abandonada (humano      │
                                        │  │   nunca atendeu)          │
                                        │  └─ humano_atendeu=True      │
                                        └──────────────┬───────────────┘
                                                       ▼
                                        ┌──────────────────────────────┐
                                        │  ATENDIMENTO HUMANO          │
                                        │  1 a 3 rodadas de trabalho   │
                                        │  ├─ 84% ► Resolvida por      │
                                        │  │        humano             │
                                        │  └─ 16% ► Transferida sem    │
                                        │           resolução (abre    │
                                        │           chamado p/ área)   │
                                        └──────────────────────────────┘
```

---

## 4. Desfechos (`status_conversa` × `resolvida`)

| status_conversa | resolvida | Significado |
|---|---|---|
| Resolvida pelo bot | Sim | A Kenzie resolveu sozinha |
| Resolvida por humano | Sim | Escalou e o especialista resolveu |
| Transferida - sem resolução | Não | Humano atendeu mas abriu chamado para outra área |
| Encerrada sem resolução | Não | Bot não resolveu e o cliente desistiu sem escalar |
| Abandonada pelo cliente | **Desconhecido** | Cliente sumiu — não é possível afirmar o desfecho |
| Opt-out / descadastro | Não aplicável | Resposta a disparo ativo |
| Sem resposta (disparo ativo) | Não aplicável | Cliente ignorou a campanha |
| Ruído (engano / já resolveu / sem contexto) | Não aplicável | Não é atendimento |

**Regra de ouro:** só conversas de **abandono ou ruído** terminam numa fala do cliente.
Todas as demais são encerradas pelo agente (Kenzie ou Humano).

**Duas flags distintas, propositalmente:**
- `transferencia_iniciada` — a Kenzie disse "vou transferir" (mede escalonamento).
- `humano_atendeu` — um humano efetivamente falou (mede atendimento e alimenta o SLA de fila).
A diferença entre as duas é a **fila abandonada**.

---

## 5. Encaminhamento entre áreas

Quando o caso exige outra área, `area_encaminhada` e `motivo_transferencia` são
preenchidos (Cadastro/Onboarding, Prevenção a Fraude, Câmbio/Backoffice, Suporte
Técnico, Cartões, Mesa de Limites, Investimentos, Atendimento PJ). Serve para medir
a qualidade da triagem — dor conhecida da operação e alvo da V2.

---

## 6. Sentimento

Cada fala **do cliente** recebe um rótulo (`Negativo` / `Neutro` / `Positivo`)
**derivado do próprio texto**: a expressão emocional escrita é que define o rótulo.
A dificuldade do assunto e o arquétipo alteram apenas a *probabilidade* de o cliente
estar irritado — nunca o rótulo diretamente. Mensagens do bot e do humano não têm
sentimento. `sentimento_geral` da conversa = sentimento da **última** fala do cliente.

Isso evita *data leakage* e permite treinar um classificador de sentimento legítimo
na Fase 4 (validado: ~90% das falas negativas e ~99% das positivas contêm a expressão
correspondente, nos três idiomas).

---

## 7. Mídia

O cliente pode mandar **texto** (81%), **imagem** (12%, prefixo `[foto anexada]`)
ou **áudio** (7%, prefixo `[audio transcrito]`) — realidade do WhatsApp.
Bot e humano só produzem texto.

---

## 8. Tratamento de dados pessoais (LGPD by design)

Num export real, o cliente digita CPF, telefone, e-mail e número de conta dentro
do chat. O fluxo reproduz esse comportamento (~10% das falas do cliente) e aplica
um **pipeline de mascaramento na ingestão**: o valor bruto **nunca é persistido**,
apenas o marcador.

```
Cliente digita:  "Meu CPF e 123.456.789-01."
Persistido:      "Meu CPF e [CPF]."
```

Marcadores usados: `[CPF]`, `[TELEFONE]`, `[EMAIL]`, `[CONTA]`.
Rastreabilidade: `contem_dado_mascarado` (mensagem) e `qtd_dados_mascarados` (conversa).
O `id_cliente` é um **pseudônimo** (hash estável, ex.: `CLI-69A2E37F315A`) — liga as
tabelas sem carregar ordem de cadastro nem qualquer vínculo com identificador real.

> Reforço: a base é **100% sintética**. O mascaramento existe para reproduzir com
> fidelidade o formato de um log real já anonimizado e para demonstrar a governança
> aplicada — não porque haja qualquer dado real envolvido.

---

## 9. Formato padronizado da transcrição

`transcricao_completa` segue sempre o mesmo padrão, com índice e remetente explícitos:

```
[01] Cliente: ... || [02] Kenzie: ... || [03] Atendente Humano: ...
```

Separador: ` || ` · Índice: `[NN]` com dois dígitos · Remetente: `Cliente` | `Kenzie` | `Atendente Humano`.

---

## 10. Pesquisa de satisfação (CSAT)

Disparada tanto no atendimento **do bot** quanto **do humano**. Apenas ~30% respondem
(o restante fica em branco — comportamento real de baixa adesão). Conversas
abandonadas e de ruído praticamente não recebem avaliação.
