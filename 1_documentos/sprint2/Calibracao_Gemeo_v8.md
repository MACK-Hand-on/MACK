# Recalibração do Gêmeo Estatístico — v7 → v8

**Projeto Kenzie 360 · Sprint 2 · 24 de agosto de 2026**
Motivação: três limitações identificadas na Análise Exploratória (`EDA_Kenzie360.md`, Seção 6).

---

## 1. Por que refazer a base

A EDA da Sprint 2 não encontrou apenas achados sobre o negócio — encontrou também três pontos em que o gerador não reproduzia o comportamento real da operação. Como a fidelidade do gêmeo é premissa de todo o projeto, corrigi-los tem precedência sobre seguir construindo em cima deles.

**O princípio que guiou a correção:** os **níveis agregados** vieram da calibração com a operação real e precisam ser preservados. O que a v8 muda é a **distribuição interna** desses totais, não os totais.

---

## 2. As três correções

### L1 — Sazonalidade

**Problema.** A data de cada conversa era um sorteio uniforme no período:

```python
inicio = DATA_INICIO + timedelta(seconds=random.randint(0, TOTAL_SEG))
```

Resultado: 197,8 conversas por dia com desvio de 15,2 — variação de 7,7%. Segunda-feira tinha praticamente o mesmo volume que domingo (razão 0,99). Nenhuma operação de atendimento se comporta assim, e qualquer análise temporal sobre essa base produzia ruído.

**Correção.** O peso de cada dia passa a combinar quatro efeitos:

| Efeito | Implementação |
|---|---|
| Dia da semana | Pesos de 1,22 (segunda) a 0,52 (domingo) |
| Vencimento de fatura | Dias 4 a 10 do mês recebem ×1,22 |
| Virada de mês | Dias 1 a 3 recebem ×1,12 |
| Tendência | Crescimento de 22% do início ao fim do período |
| Incidentes | 5 dias aleatórios com ×1,6 (instabilidade de PIX, falha no app) |

### L3 — Fuso horário do público CDE

**Problema.** 90% do volume caía entre 8h e 19h de Brasília — o padrão de um público residente no Brasil. Mas 70% da base é CDE, domiciliada no exterior. A v7 tratava um cliente em Londres como se ele acordasse no horário de São Paulo.

**Correção.** Cada cliente CDE recebe um fuso na criação da carteira, sorteado a partir do idioma (proxy razoável da região de domicílio):

| Idioma | Regiões modeladas |
|---|---|
| EN | EUA/Canadá Leste (36%), Reino Unido (24%), Europa Continental (20%), EUA Oeste (14%), Ásia (6%) |
| ES | Espanha (46%), Colômbia/Peru (22%), Argentina/Uruguai (20%), México (12%) |
| PT | Portugal (55%), retornados ao Brasil (35%), África lusófona (10%) |

O horário comercial **local do cliente** é então convertido para horário de Brasília. Clientes nacionais e PJ permanecem no fuso de Brasília.

### L5 — Atrito acumulado

**Problema.** O desfecho dependia exclusivamente da categoria do assunto:

```python
resolvido_bot = random.random() < info["p_bot"]
```

Um cliente na quarta tentativa do mesmo bloqueio de PIX tinha exatamente a mesma chance de resolução, a mesma duração e o mesmo humor de quem chegava pela primeira vez. A reabertura era consequência, mas nunca virava causa — o ciclo de atrito era uma via de mão única.

**Correção.** Exigiu reestruturar o loop principal em duas fases, porque para o histórico influenciar o desfecho é preciso simular em ordem cronológica:

1. **Agenda** — sorteia quem fala e quando, e ordena por data
2. **Simulação** — percorre a agenda mantendo memória por cliente (`contatos_previos` e desfecho anterior)

O histórico passa a pesar em três frentes:

| Frente | Parâmetro | Efeito |
|---|---|---|
| Resolução pelo bot | `atrito_por_contato` = 0,07 | −7% relativo por contato prévio (teto: 6) |
| | `atrito_reabertura` = 0,18 | −18% adicional se for reabertura |
| | `atrito_piso` = 0,45 | A queda nunca ultrapassa 55% |
| Abandono | `abandono_por_contato` = 0,10 | +10% por contato prévio |
| | `abandono_reabertura` = 0,30 | +30% adicional em reabertura |
| Humor | `atrito_humor` | +4,5 p.p. de chance de fala negativa por contato, +10 p.p. em reabertura |

Como consequência, `contatos_previos` e `reabertura` deixam de ser calculados no pós-processamento e passam a sair da própria simulação.

---

## 3. Recalibração — preservando os níveis agregados

As correções derrubaram a resolução média para 21,4% e elevaram o abandono para 21,7%. Como 25,3% e 17,1% vêm da calibração com dados reais, foram introduzidos dois fatores de compensação:

```python
"calib_p_bot": 1.185,      # compensa a queda media causada pelo atrito
"calib_abandono": 0.80,    # compensa a elevacao media do abandono
```

O efeito é preservar os totais e redistribuir por dentro: quem chega pela primeira vez passa a ser **mais** bem atendido que na v7, e quem reincide, **menos**.

---

## 4. Resultado

### Indicadores agregados — preservados

| Indicador | v7 | v8 | Δ |
|---|---:|---:|---:|
| Resolução pelo bot | 25,3% | 25,2% | −0,1 |
| Transferência iniciada | 41,7% | 41,8% | +0,1 |
| Humano atendeu | 37,4% | 37,7% | +0,3 |
| Abandono | 17,1% | 17,3% | +0,2 |
| Reaberturas | 16,8% | 17,8% | +1,0 |
| CSAT geral | 3,72 | 3,74 | +0,02 |
| Duração média | 11,6 min | 11,7 min | +0,1 |
| Clientes recorrentes | 39,9% | 39,8% | −0,1 |

**Schema idêntico:** as mesmas 30 colunas, na mesma ordem. Nenhum script da pipeline precisa mudar.

### As correções — funcionando

**L1 · Sazonalidade**

| | v7 | v8 |
|---|---:|---:|
| Variação do volume diário | 7,7% | **30,6%** |
| Menor / maior dia | 161 / 241 | **75 / 379** |
| Razão segunda ÷ domingo | 0,99 | **2,43** |

**L3 · Fuso horário**

| Volume entre 8h e 19h (BRT) | v7 | v8 |
|---|---:|---:|
| Clientes CDE | 90,0% | **70,1%** |
| Clientes nacionais | 90,0% | 90,9% |
| Madrugada (0h–6h), geral | 4,9% | **10,1%** |

**L5 · Atrito acumulado**

| Resolução pelo bot | v7 | v8 |
|---|---:|---:|
| 1º contato | 25,3% | **29,9%** |
| 3º contato | 25,5% | **22,1%** |
| 5º contato | 27,4% | **15,3%** |
| Em reabertura | 25,3% | **17,2%** |
| Fora de reabertura | 25,3% | 27,0% |

| Outros efeitos | v7 | v8 |
|---|---:|---:|
| Sentimento negativo em reabertura | 22,9% | **34,7%** |
| CSAT em reabertura | 3,75 | **3,57** |

Na v7 as três linhas de resolução por contato eram indistinguíveis. Na v8 há um gradiente monotônico de 29,9% a 15,3% — o cliente que insiste é progressivamente pior atendido, como na operação real.

---

## 5. Como reproduzir

```bash
python3 gerar_dataset_cde_v8.py     # gera os CSVs com sufixo _v8
python3 compara_v7_v8.py            # relatório comparativo v7 x v8
```

O `SEED = 42` permanece: a v8 é tão determinística quanto a v7. Saída em `dataset_kenzie360_atendimentos_v8.csv` e `dataset_kenzie360_mensagens_v8.csv`, deixando os arquivos da v7 intactos.

### Verificação de integridade da v8

| Arquivo | Linhas | SHA-256 |
|---|---:|---|
| `dataset_kenzie360_atendimentos_v8.csv` | 36.000 | `183587592d771a8996e6de6ac0658a3c4c14f92bd1ac966af1ebd4ece3545342` |
| `dataset_kenzie360_mensagens_v8.csv` | 405.073 | `70ae0b4a13f385e92c493d1212f1888b47f947a601f7fd0155e0a859145daf41` |

Linux / WSL: `sha256sum dataset_kenzie360_atendimentos_v8.csv`
Windows (PowerShell): `Get-FileHash dataset_kenzie360_atendimentos_v8.csv -Algorithm SHA256`

*O total de mensagens sobe de 404.092 (v7) para 405.073 (v8) porque o atrito altera o número de turnos das conversas reincidentes.*

---

## 6. Auditoria da v8

A v8 foi submetida a uma verificação adversarial — procurando defeitos, não confirmações.

### 6.1 O atrito criou espiral sem saída?

**Não.** A degradação é gradual e o cliente continua tendo chance real de resolução:

| Contatos prévios | Resolução total (bot + humano) | Abandono |
|---|---:|---:|
| 0 | 61,8% | 13,9% |
| 3 | 53,9% | 17,5% |
| 5 | 51,5% | 23,1% |
| 8 | 48,2% | 23,6% |

Na v7 essa coluna era plana (56–57% em todas as faixas). Na v8 cai cerca de 13 pontos ao longo de oito contatos — degradação, não colapso. Um piso (`atrito_piso`) impede que a chance despenque.

### 6.2 Efeitos colaterais em variáveis que não deviam mudar

| Variável | Maior desvio v7 → v8 |
|---|---:|
| Mix de categorias de assunto | 0,43 p.p. |
| Mix de arquétipos | 0,83 p.p. |
| Mix de idiomas | 0,21 p.p. |
| Duração média | +0,1 min |
| Turnos médios | +0,01 |
| Taxa de resposta do CSAT | −0,1 p.p. |

Nenhum vazamento relevante. As correções atingiram o que deviam atingir.

### 6.3 Coerência dos horários por segmento

| Segmento | Hora de pico | Madrugada (0h–5h) | 8h–19h BRT |
|---|---:|---:|---:|
| CDE | 11h | 12,4% | 70,1% |
| Correntista Nacional | 14h | 4,7% | 90,9% |
| PJ | 12h | 4,2% | 91,0% |

O cliente nacional mantém o padrão comercial brasileiro; o CDE se espalha, com a madrugada quase triplicando. É exatamente o comportamento esperado de um público majoritariamente domiciliado no exterior.

### 6.4 Calibração dos picos de sazonalidade

A primeira versão da v8 produzia amplitude de 6,1× entre o menor e o maior dia — plausível em incidente grave, mas exagerado como padrão. O parâmetro `forca_pico` foi reduzido de 2,1 para 1,6, levando a amplitude a 5,1× e a variação diária a 30,6%. O efeito de dia da semana e a tendência permanecem intactos.

### 6.5 Ponto que exige decisão consciente do grupo

Com a recalibração, o **primeiro contato passa a ser melhor atendido que na v7** (29,9% contra 25,3%), enquanto o reincidente é pior. A média global permanece em 25,2%.

Isso é correto **se** os 25,3% da Sprint 1 forem a taxa agregada do período — que é o caso, conforme validado com a área de negócio. Se o número tivesse sido medido apenas sobre atendimentos típicos, a ancoragem precisaria mudar. Fica registrado porque é o tipo de premissa que uma banca pode questionar.

---

## 7. Nota sobre a Entrega 1

Os números publicados na Sprint 1 continuam válidos **para a v7**, que permanece como está — nenhum arquivo foi substituído ou apagado. A v8 é documentada como **evolução motivada pelos achados da EDA**, não como correção de erro da entrega anterior.

A narrativa, aliás, funciona a favor: a análise exploratória encontrou limitações no próprio instrumento de geração, a equipe as corrigiu, e a pipeline absorveu a mudança sem alteração de schema nem de código.

---

## 8. Achado paralelo — pacote de scripts corrompido

Durante este trabalho constatou-se que o `scripts_kenzie360.zip` da Entrega 1 estava **corrompido** (erro de CRC): o `gerar_dataset_cde.py` ficava truncado a partir da linha ~234 e não executava.

O arquivo foi restaurado a partir da cópia íntegra e a restauração foi **verificada por hash**: os dois CSVs gerados conferem byte a byte com os SHA-256 documentados na Entrega 1.

```
048da528c1995a0e27692e0e9d1e5f79dde5c64b8ed19c679c262e5935468e94  atendimentos
5537471cc8278038805f70575b8ad9803e5f0f21485e5fa68ffbe07ce12485a6  mensagens
```

O substituto é o `scripts_kenzie360_corrigido.zip`, com integridade testada. Recomenda-se conferir os demais pacotes enviados ao Drive — corrupção de CRC costuma vir de upload interrompido.
