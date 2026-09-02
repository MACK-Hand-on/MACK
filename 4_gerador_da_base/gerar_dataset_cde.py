# -*- coding: utf-8 -*-
"""
=============================================================================
 PROJETO KENZIE 360 - HANDS-ON MBA MACKENZIE (ENGENHARIA DE DADOS)
 GERADOR v7 - "GEMEO ESTATISTICO" (calibrado + realismo avancado)
=============================================================================
 Dados 100% SINTETICOS (sem dado pessoal - LGPD) que reproduzem com fidelidade
 os padroes reais do atendimento (fonte real: Take Blip / WhatsApp).

 v7 acrescenta:
 - 9 ARQUETIPOS (inclui Expat Code-Switcher, Alta Renda/Private, Risco de Churn,
   Empresario PJ ~3%).
 - ORIGEM: Receptivo x Ativo (disparo do banco via Blip): opt-out, sem resposta, engajado.
 - MIDIA: texto / imagem / audio (realidade do WhatsApp).
 - RECORRENCIA: contatos_previos e reabertura (volume por cliente em lei de potencia).
 - BOT QUE ERRA (NLU miss) + correcao do cliente.
 - CHURN: falas de risco (encerrar conta, concorrente, Reclame Aqui).
 - CODE-SWITCHING: expats misturando PT+EN.
 - Ruido em 5%; conversas longas; CSAT no bot e no humano (com brancos).

 SAIDA: dataset_kenzie360_atendimentos.csv e dataset_kenzie360_mensagens.csv
 RODAR: pip install pandas numpy ; python gerar_dataset_cde.py
=============================================================================
"""
import pandas as pd
import numpy as np
import random
import hashlib
from datetime import datetime, timedelta
from pathlib import Path as _Path

# Saida na estrutura de pastas do projeto: 4_gerador_da_base -> 2_dados
_SAIDA = _Path(__file__).resolve().parent.parent / "2_dados" / "historico_v7"
_SAIDA.mkdir(parents=True, exist_ok=True)

SEED = 42
random.seed(SEED); np.random.seed(SEED)

CONFIG = {
    "n_clientes": 15000,
    "n_conversas": 36000,          # opcao A: mais tickets -> recorrencia (churn)
    "prop_recorrente": 0.40,       # ~40% dos clientes concentram contatos repetidos
    "cap_contatos": 45,            # teto de contatos por cliente (evita outlier extremo)
    "meses": 6,
    "prop_segmento": {"CDE": 0.70, "Correntista Nacional": 0.27, "PJ": 0.03},
    "arq_por_segmento": {
        "CDE": {"Expat Digital": 0.40, "Expat Code-Switcher": 0.12, "Nao Residente Senior": 0.25,
                "Alta Renda/Private": 0.10, "Risco de Churn": 0.08, "Formal/Premium": 0.05},
        "Correntista Nacional": {"Nacional Pratico": 0.38, "Nacional Jovem Digital": 0.34,
                "Alta Renda/Private": 0.08, "Risco de Churn": 0.10, "Formal/Premium": 0.10},
        "PJ": {"Empresario PJ": 1.0},
    },
    "p_ruido": 0.05,
    "p_ativo": 0.18,       # % de conversas iniciadas por disparo ativo do banco
    "p_nlu_miss": 0.15,    # % de conversas em que o bot entende errado
    "p_midia_imagem": 0.12,
    "p_midia_audio": 0.07,
    "p_pii": 0.10,         # % de falas do cliente que trazem dado pessoal (sera mascarado)
}
DATA_FIM = datetime(2026, 8, 18)
DATA_INICIO = DATA_FIM - timedelta(days=CONFIG["meses"] * 30 + 2)

ARQUETIPOS = {
 "Expat Digital":        {"tech":"alto","idade":"jovem","ab":1.5,"idioma_cde":{"EN":0.5,"ES":0.2,"PT":0.3},
                          "canal_hum":{"WhatsApp":0.70,"Telefone":0.15,"E-mail":0.15}},
 "Expat Code-Switcher":  {"tech":"alto","idade":"jovem","ab":1.4,"idioma_cde":{"PT":0.5,"EN":0.3,"ES":0.2},"code_switch":True,
                          "canal_hum":{"WhatsApp":0.75,"Telefone":0.10,"E-mail":0.15}},
 "Nao Residente Senior": {"tech":"baixo","idade":"idoso","ab":0.9,"idioma_cde":{"PT":0.4,"EN":0.4,"ES":0.2},
                          "canal_hum":{"WhatsApp":0.30,"Telefone":0.45,"E-mail":0.25}},
 "Alta Renda/Private":   {"tech":"medio","idade":"adulto","ab":0.6,"exigente":True,"idioma_cde":{"EN":0.45,"PT":0.40,"ES":0.15},
                          "canal_hum":{"WhatsApp":0.40,"Telefone":0.45,"E-mail":0.15}},
 "Risco de Churn":       {"tech":"medio","idade":"adulto","ab":1.6,"churn":True,"idioma_cde":{"PT":0.5,"EN":0.35,"ES":0.15},
                          "canal_hum":{"WhatsApp":0.50,"Telefone":0.30,"E-mail":0.20}},
 "Formal/Premium":       {"tech":"medio","idade":"adulto","ab":0.8,"idioma_cde":{"EN":0.4,"PT":0.4,"ES":0.2},
                          "canal_hum":{"WhatsApp":0.50,"Telefone":0.25,"E-mail":0.25}},
 "Nacional Pratico":     {"tech":"medio","idade":"adulto","ab":1.0,"idioma_cde":None,
                          "canal_hum":{"WhatsApp":0.55,"Telefone":0.30,"E-mail":0.15}},
 "Nacional Jovem Digital":{"tech":"alto","idade":"jovem","ab":1.3,"idioma_cde":None,
                          "canal_hum":{"WhatsApp":0.80,"Telefone":0.10,"E-mail":0.10}},
 "Empresario PJ":        {"tech":"medio","idade":"adulto","ab":0.7,"exigente":True,"idioma_cde":None,
                          "canal_hum":{"WhatsApp":0.50,"Telefone":0.35,"E-mail":0.15}},
}

# ------- lexico / frases por idioma -------
EXPR_NEG = {
 "PT":["Estou muito frustrado com isso.","Isso e um absurdo.","Que servico pessimo, decepcionante.","Ja e a terceira vez que tento, perdendo a paciencia.","Estou muito insatisfeito com o banco.","Preciso disso resolvido com urgencia."],
 "EN":["I'm really frustrated with this.","This is unacceptable.","Terrible service, very disappointed.","Third time I try, losing my patience.","I'm very unhappy with the bank.","I need this solved urgently."],
 "ES":["Estoy muy frustrado con esto.","Esto es un absurdo.","Pesimo servicio, decepcionante.","Es la tercera vez que lo intento, pierdo la paciencia.","Estoy muy insatisfecho con el banco.","Necesito resolver esto con urgencia."]}
EXPR_POS = {
 "PT":["Muito obrigado, excelente!","Perfeito, era isso que eu precisava.","Otimo atendimento, muito rapido!","Show, muito obrigado mesmo!","Fiquei muito satisfeito, parabens."],
 "EN":["Thank you so much, excellent!","Perfect, exactly what I needed.","Great service, very fast!","Awesome, thanks a lot!","I'm very satisfied, great support."],
 "ES":["Muchas gracias, excelente!","Perfecto, era justo lo que necesitaba.","Muy buen servicio, muy rapido!","Genial, muchas gracias!","Quede muy satisfecho, gran soporte."]}
NUCLEO_FUP = {
 "PT":{"Negativo":["Continua sem funcionar.","Ainda estou com o mesmo problema.","Isso nao resolveu, continua igual."],"Neutro":["E agora, como prosseguimos?","Certo, qual o proximo passo?","Entendi, e depois disso?"],"Positivo":["Obrigado, deu certo!","Funcionou, muito bom!","Consegui resolver, valeu!"]},
 "EN":{"Negativo":["It still doesn't work.","I still have the same problem.","That didn't solve it."],"Neutro":["And how do we proceed now?","Ok, what's the next step?","I see, and then?"],"Positivo":["Thanks, it worked!","It worked, great!","Solved, thank you!"]},
 "ES":{"Negativo":["Sigue sin funcionar.","Sigo con el mismo problema.","Eso no lo resolvio."],"Neutro":["Y ahora como seguimos?","Bien, cual es el proximo paso?","Entiendo, y despues?"],"Positivo":["Gracias, funciono!","Funciono, muy bien!","Resuelto, gracias!"]}}
# ---- IDENTIDADE CANONICA DA KENZIE (padronizada: 1 saudacao oficial por idioma) ----
# Regra: o bot SEMPRE se apresenta da mesma forma. Variacao de texto so em
# mensagens de conteudo, nunca na saudacao/identidade.
BOT_SAUD={"PT":["Ola! Sou a Kenzie, assistente virtual do banco. Como posso ajudar?"],
          "EN":["Hello! I'm Kenzie, the bank's virtual assistant. How can I help?"],
          "ES":["Hola! Soy Kenzie, asistente virtual del banco. Como puedo ayudar?"]}
BOT_FUP={"PT":["Certo, deixa eu verificar isso para voce.","Ja localizei seu cadastro, um instante.","Estou checando os detalhes aqui.","Consegui puxar a informacao, so um momento."],"EN":["Sure, let me check that for you.","I found your profile, one moment.","I'm checking the details here.","Got the info, just a second."],"ES":["Claro, dejame verificar eso.","Ya encontre tu registro, un momento.","Estoy revisando los detalles aqui.","Ya tengo la informacion, un segundo."]}
# falas de fechamento do cliente (encerram a conversa de verdade)
NUCLEO_FECHO={
 "PT":{"Positivo":["Obrigado, deu certo!","Perfeito, resolvido!","Otimo, muito obrigado!"],"Neutro":["Ok, obrigado.","Entendi, obrigado pela ajuda.","Certo, obrigado."],"Negativo":["Ok... vou aguardar entao.","Certo, mas continuo insatisfeito.","Ta, obrigado mesmo assim."]},
 "EN":{"Positivo":["Thanks, it worked!","Perfect, all resolved!","Great, thank you!"],"Neutro":["Ok, thank you.","Got it, thanks for the help.","Alright, thanks."],"Negativo":["Ok... I'll wait then.","Fine, but I'm still unhappy.","Alright, thanks anyway."]},
 "ES":{"Positivo":["Gracias, funciono!","Perfecto, resuelto!","Genial, muchas gracias!"],"Neutro":["Ok, gracias.","Entendido, gracias por la ayuda.","Bien, gracias."],"Negativo":["Ok... esperare entonces.","Bien, pero sigo insatisfecho.","Esta bien, gracias igual."]}}
HUM_FECHA={"PT":["Fico a disposicao. Tenha um otimo dia!","Precisa de mais alguma coisa?","Qualquer duvida, e so voltar a falar comigo."],"EN":["I'm at your disposal. Have a great day!","Anything else you need?","If you have questions, just reach out again."],"ES":["Quedo a disposicion. Que tengas buen dia!","Necesitas algo mas?","Cualquier duda, vuelve a escribirme."]}
BOT_FECHA={"PT":["Fico feliz em ajudar! Mais alguma coisa?","Resolvido! Qualquer coisa, e so chamar."],"EN":["Glad to help! Anything else?","All set! Reach out anytime."],"ES":["Con gusto! Algo mas?","Listo! Cualquier cosa, avisame."]}
BOT_ESCALA={"PT":["Vou te transferir para um atendente humano, um momento.","Esse caso precisa de um especialista humano, ja vou transferir."],"EN":["I'll transfer you to a human agent, one moment.","This needs a human specialist, transferring now."],"ES":["Te transfiero a un agente humano, un momento.","Este caso necesita un especialista humano, transfiriendo."]}
BOT_SEM={"PT":["Sinto muito por nao resolver por aqui. Estou a disposicao.","Lamento nao solucionar agora. Tente novamente mais tarde."],"EN":["Sorry I couldn't solve it here. I'm available if needed.","Sorry I couldn't fix it now. Please try again later."],"ES":["Lamento no resolverlo aqui. Quedo a disposicion.","Lamento no solucionarlo ahora. Intenta mas tarde."]}
BOT_ERRO={"PT":["Desculpe, acho que nao entendi. Voce quer falar sobre cartao de credito?","Hmm, nao tenho certeza. Seria sobre uma transferencia?"],"EN":["Sorry, I don't think I understood. Do you want to talk about your credit card?","Hmm, I'm not sure. Is it about a transfer?"],"ES":["Perdon, creo que no entendi. Quieres hablar de la tarjeta de credito?","Hmm, no estoy seguro. Es sobre una transferencia?"]}
CLI_CORRIGE={"PT":["Nao era isso, minha duvida e outra.","Nao, nao e sobre isso.","Voce entendeu errado, e sobre o que eu disse."],"EN":["That's not it, my question is different.","No, it's not about that.","You got it wrong, it's about what I said."],"ES":["No era eso, mi duda es otra.","No, no es sobre eso.","Entendiste mal, es sobre lo que dije."]}
HUM_SAUD={"PT":["Ola, aqui e o atendimento humano. Assumi seu caso e vou ajudar.","Oi, sou do time de especialistas, vou cuidar disso."],"EN":["Hello, this is human support. I've taken over your case.","Hi, I'm from the specialist team, I'll handle this."],"ES":["Hola, soy atencion humana. Tome tu caso y te ayudo.","Hola, soy del equipo de especialistas, me encargo."]}
HUM_TRAB={"PT":["Deixa eu checar isso no sistema, um instante.","Estou analisando o seu caso agora.","Ja verifiquei parte, so mais um momento.","Consultando a area responsavel aqui."],"EN":["Let me check that in the system, one moment.","I'm reviewing your case now.","I've checked part of it, one more moment.","Consulting the responsible team here."],"ES":["Dejame revisar eso en el sistema, un momento.","Estoy analizando tu caso ahora.","Ya verifique parte, un momento mas.","Consultando al area responsable aqui."]}
HUM_RESOLVE={"PT":["Consegui resolver aqui no sistema, tudo certo.","Regularizei seu caso manualmente, resolvido."],"EN":["I've solved it in the system, all set.","Fixed your case manually, resolved."],"ES":["Lo resolvi en el sistema, todo listo.","Regularice tu caso manualmente, resuelto."]}
HUM_NAO={"PT":["Encaminhei para a area de {a}; retornaremos em ate 48h.","Precisa de analise da area de {a}; abri um chamado."],"EN":["I've forwarded it to the {a} team; we'll get back within 48h.","This needs {a} analysis; I've opened a ticket."],"ES":["Lo derive al area de {a}; responderemos en 48h.","Necesita analisis del area de {a}; abri un ticket."]}
MOTIVOS_TRANSF=["Fora do escopo do bot","Necessita acao em sistema interno","Validacao de seguranca","Analise manual/documental","Excecao de regra de negocio"]
CHURN_FRASES={"PT":["Assim vou encerrar minha conta.","Vi condicoes melhores no concorrente.","Vou reclamar no Reclame Aqui."],"EN":["I might close my account over this.","I've seen better offers at a competitor.","I'll complain publicly about this."],"ES":["Voy a cerrar mi cuenta por esto.","Vi mejores condiciones en la competencia.","Voy a reclamar publicamente."]}

# --- disparo ativo (outbound) ---
# Disparo ativo: identidade padronizada + conteudo da campanha
ATIVO={"PT":["Ola! Sou a Kenzie, assistente virtual do banco. Temos novidades sobre o seu CDB, quer saber mais?","Ola! Sou a Kenzie, assistente virtual do banco. Lembrete: atualize seu cadastro para manter sua conta ativa.","Ola! Sou a Kenzie, assistente virtual do banco. Sua fatura do cartao fechou, posso ajudar com algo?","Ola! Sou a Kenzie, assistente virtual do banco. Temos uma condicao especial de cambio hoje para voce!"],
       "EN":["Hello! I'm Kenzie, the bank's virtual assistant. We have news about your CDB, want to know more?","Hello! I'm Kenzie, the bank's virtual assistant. Reminder: please update your registration to keep your account active.","Hello! I'm Kenzie, the bank's virtual assistant. Your card statement is ready, can I help with anything?","Hello! I'm Kenzie, the bank's virtual assistant. We have a special FX rate for you today!"],
       "ES":["Hola! Soy Kenzie, asistente virtual del banco. Tenemos novedades sobre tu CDB, quieres saber mas?","Hola! Soy Kenzie, asistente virtual del banco. Recordatorio: actualiza tu registro para mantener la cuenta activa.","Hola! Soy Kenzie, asistente virtual del banco. Tu factura de la tarjeta esta lista, te ayudo con algo?","Hola! Soy Kenzie, asistente virtual del banco. Tenemos una condicion especial de cambio hoy para ti!"]}
OPTOUT={"PT":["Nao quero mais receber essas mensagens.","Parem de me mandar isso, por favor.","Descadastra meu numero dessas ofertas."],"EN":["I don't want to receive these messages anymore.","Please stop sending me this.","Unsubscribe my number from these offers."],"ES":["No quiero recibir mas estos mensajes.","Dejen de enviarme esto, por favor.","Den de baja mi numero de estas ofertas."]}
BOT_OPTOUT={"PT":"Sem problemas, vou remover voce dos disparos. Desculpe o incomodo.","EN":"No problem, I'll remove you from our messages. Sorry for the inconvenience.","ES":"Sin problema, te quito de los envios. Disculpa la molestia."}

# ------- ruido -------
NOISE={"engano":{"status":"Ruido - contato por engano","PT":["Ops, chamei sem querer, desculpe.","Foi engano, pode ignorar."],"EN":["Oops, wrong chat, sorry.","Sent by mistake, please ignore."],"ES":["Ups, me equivoque, disculpa.","Fue un error, ignoralo."]},
 "autoresolvido":{"status":"Cliente ja havia resolvido","PT":["Deixa pra la, ja resolvi sozinho.","Ja deu certo, obrigado!"],"EN":["Never mind, I already solved it.","It worked out, thanks!"],"ES":["Dejalo, ya lo resolvi solo.","Ya se soluciono, gracias!"]},
 "semcontexto":{"status":"Contato sem contexto (oi/teste)","PT":["Oi","Ola?","Testando","?"],"EN":["Hi","Hello?","Testing","?"],"ES":["Hola","Hola?","Probando","?"]}}
BOT_RUIDO={"PT":["Sem problemas! Se precisar de algo, e so chamar.","Tudo bem! Estou por aqui se precisar."],"EN":["No problem! If you need anything, just reach out.","All good! I'm here if you need me."],"ES":["Sin problema! Si necesitas algo, avisame.","Todo bien! Estoy por aqui si necesitas."]}

# ------- assuntos (trilingue) -------
ASSUNTOS = {
 "Onboarding - Documentacao":{"peso_cde":0.18,"peso_nac":0.07,"produto":"Conta Corrente","p_bot":0.18,"area":"Cadastro/Onboarding",
  "openings":{"PT":["Meu comprovante de residencia no exterior foi recusado.","Nao consigo enviar meu passaporte no app.","Enviei os documentos ha 3 dias e nao aprovaram."],"EN":["My proof of address abroad was rejected.","I can't upload my passport in the app.","I sent my documents 3 days ago and they're not approved yet."],"ES":["Rechazaron mi comprobante de domicilio en el exterior.","No puedo subir mi pasaporte en la app.","Envie los documentos hace 3 dias y no los aprueban."]},
  # variantes por segmento (evita nacional/PJ falando como expatriado)
  "openings_nac":{"PT":["Meu comprovante de residencia foi recusado no cadastro.","Nao consigo enviar meu RG pelo aplicativo.","Enviei os documentos ha 3 dias e nao aprovaram."],"EN":["My proof of address was rejected in the registration.","I can't upload my ID in the app.","I sent my documents 3 days ago and they're not approved yet."],"ES":["Rechazaron mi comprobante de domicilio en el registro.","No puedo subir mi documento en la app.","Envie los documentos hace 3 dias y no los aprueban."]},
  "openings_pj":{"PT":["O contrato social da empresa foi recusado no cadastro.","Nao consigo enviar o cartao CNPJ pelo aplicativo.","Enviei a documentacao da empresa ha 3 dias e nao aprovaram."],"EN":["The company's articles of incorporation were rejected.","I can't upload the company registration document.","I sent the company documents 3 days ago and they're not approved."],"ES":["Rechazaron el contrato social de la empresa.","No puedo subir el documento de la empresa en la app.","Envie la documentacion de la empresa hace 3 dias y no la aprueban."]},
  "bot":{"PT":"Para o cadastro aceitamos documento oficial com foto e comprovante recente. Posso verificar seu envio.","EN":"For onboarding we accept a photo ID and a recent proof of address. I can check your submission.","ES":"Para el registro aceptamos documento con foto y comprobante reciente. Puedo revisar tu envio."}},
 "Termos e Documentacao BR":{"peso_cde":0.10,"peso_nac":0.02,"produto":"Conta Corrente","p_bot":0.30,"area":"Cadastro/Onboarding",
  "openings":{"PT":["O que e CPF e por que preciso dele?","Nao entendo o que e um PIX, como funciona?","Pediram meu numero de identificacao fiscal, o que e isso?","Moro fora ha anos, meu CPF ainda vale?"],"EN":["What is CPF and why do I need it?","I don't understand what PIX is, how does it work?","They asked for my tax ID number, what is that?","I've lived abroad for years, is my CPF still valid?"],"ES":["Que es el CPF y por que lo necesito?","No entiendo que es PIX, como funciona?","Me pidieron mi numero de identificacion fiscal, que es eso?","Vivo fuera hace anos, mi CPF sigue valido?"]},
  "openings_nac":{"PT":["Como faco para cadastrar minha chave PIX?","Nao entendi a diferenca entre TED e PIX.","Preciso atualizar meu CPF no cadastro?"],"EN":["How do I register my PIX key?","I didn't understand the difference between TED and PIX.","Do I need to update my tax ID in the registration?"],"ES":["Como registro mi clave PIX?","No entendi la diferencia entre TED y PIX.","Necesito actualizar mi CPF en el registro?"]},
  "bot":{"PT":"O CPF e o cadastro fiscal usado no Brasil; o PIX e o pagamento instantaneo. Posso explicar passo a passo.","EN":"CPF is the Brazilian tax ID; PIX is the instant payment system. I can explain step by step.","ES":"El CPF es el registro fiscal de Brasil; PIX es el pago instantaneo. Te explico paso a paso."}},
 "Cambio":{"peso_cde":0.20,"peso_nac":0.03,"produto":"Cambio","p_bot":0.25,"area":"Cambio/Backoffice",
  "openings":{"PT":["Qual a cotacao do dolar para minha conta hoje?","Quanto o banco cobra de taxa no cambio?","Quanto tempo demora o cambio cair na conta?","Como faco uma remessa internacional para o Brasil?"],"EN":["What's today's USD rate for my account?","How much does the bank charge on FX?","How long until the FX lands in my account?","How do I send an international remittance to Brazil?"],"ES":["Cual es la cotizacion del dolar hoy?","Cuanto cobra el banco de tasa en el cambio?","Cuanto demora en acreditarse el cambio?","Como hago una remesa internacional a Brasil?"]},
  "openings_nac":{"PT":["Qual a cotacao do dolar turismo hoje?","Consigo comprar moeda estrangeira pela conta?","Como faco uma remessa para o exterior?"],"EN":["What's today's tourism USD rate?","Can I buy foreign currency through my account?","How do I send a remittance abroad?"],"ES":["Cual es la cotizacion del dolar turismo hoy?","Puedo comprar moneda extranjera por la cuenta?","Como hago una remesa al exterior?"]},
  "openings_pj":{"PT":["Preciso fechar cambio comercial para pagar um fornecedor no exterior.","Qual a taxa de cambio para importacao da empresa?","Como envio o contrato de cambio da operacao?"],"EN":["I need a commercial FX contract to pay a supplier abroad.","What's the FX rate for the company's imports?","How do I submit the FX contract for this operation?"],"ES":["Necesito cerrar cambio comercial para pagar un proveedor en el exterior.","Cual es la tasa de cambio para la importacion de la empresa?","Como envio el contrato de cambio de la operacion?"]},
  "bot":{"PT":"As cotacoes e taxas ficam no app em Cambio > Cotacoes, em tempo real.","EN":"Rates and fees are in the app under FX > Rates, in real time.","ES":"Las cotizaciones y tasas estan en la app en Cambio > Cotizaciones, en tiempo real."}},
 "Primeiro Acesso":{"peso_cde":0.14,"peso_nac":0.10,"produto":"Conta Corrente","p_bot":0.32,"area":"Suporte Tecnico",
  "openings":{"PT":["Nao consigo fazer o primeiro acesso na conta.","O codigo de verificacao nao chega no meu numero de fora do Brasil.","Como cadastro minha senha pela primeira vez?","O aplicativo nao abre aqui no exterior."],"EN":["I can't complete my first login.","The verification code doesn't arrive on my foreign number.","How do I set my password for the first time?","The app doesn't open here abroad."],"ES":["No puedo hacer el primer acceso a la cuenta.","El codigo de verificacion no llega a mi numero del exterior.","Como registro mi contrasena por primera vez?","La app no abre aqui en el exterior."]},
  "openings_nac":{"PT":["Nao consigo fazer o primeiro acesso na conta.","O codigo de verificacao por SMS nao esta chegando.","Como cadastro minha senha pela primeira vez?","O aplicativo trava quando tento entrar."],"EN":["I can't complete my first login.","The SMS verification code isn't arriving.","How do I set my password for the first time?","The app crashes when I try to log in."],"ES":["No puedo hacer el primer acceso a la cuenta.","El codigo de verificacion por SMS no llega.","Como registro mi contrasena por primera vez?","La app se traba cuando intento entrar."]},
  "bot":{"PT":"Vamos resolver seu acesso. Posso reenviar o codigo e te guiar no cadastro da senha.","EN":"Let's fix your access. I can resend the code and guide your password setup.","ES":"Vamos a resolver tu acceso. Puedo reenviar el codigo y guiarte con la contrasena."}},
 "Bloqueio TED/PIX":{"peso_cde":0.12,"peso_nac":0.20,"produto":"Conta Corrente","p_bot":0.15,"area":"Prevencao a Fraude",
  "openings":{"PT":["Meu PIX foi bloqueado sem aviso!","Fiz uma TED e o valor nao caiu no destino.","Minha transferencia foi marcada como suspeita."],"EN":["My PIX was blocked without notice!","I made a transfer and it didn't arrive.","My transfer was flagged as suspicious."],"ES":["Bloquearon mi PIX sin aviso!","Hice una transferencia y no llego.","Marcaron mi transferencia como sospechosa."]},
  "bot":{"PT":"Sinto muito pelo transtorno. Bloqueios ocorrem por seguranca. Ja estou verificando.","EN":"Sorry for the trouble. Blocks happen for security. I'm checking it now.","ES":"Lamento el inconveniente. Los bloqueos son por seguridad. Ya lo estoy revisando."}},
 "Alteracao de Limites":{"peso_cde":0.09,"peso_nac":0.15,"produto":"Conta Corrente","p_bot":0.28,"area":"Mesa de Limites",
  "openings":{"PT":["Meu limite de PIX caiu de repente.","Preciso aumentar meu limite de transferencia.","Qual e o meu limite atual?"],"EN":["My PIX limit dropped suddenly.","I need to increase my transfer limit.","What's my current limit?"],"ES":["Mi limite de PIX bajo de repente.","Necesito aumentar mi limite de transferencia.","Cual es mi limite actual?"]},
  "bot":{"PT":"Posso mostrar seus limites atuais e registrar um pedido de ajuste.","EN":"I can show your current limits and file an adjustment request.","ES":"Puedo mostrar tus limites actuales y registrar una solicitud de ajuste."}},
 "Cartao de Credito":{"peso_cde":0.08,"peso_nac":0.20,"produto":"Cartao de Credito","p_bot":0.35,"area":"Cartoes",
  "openings":{"PT":["Minha compra no cartao foi negada.","Quando vence a fatura do meu cartao?","Como solicito o cartao de credito?"],"EN":["My card purchase was declined.","When is my card bill due?","How do I request the credit card?"],"ES":["Rechazaron una compra con mi tarjeta.","Cuando vence la factura de mi tarjeta?","Como solicito la tarjeta de credito?"]},
  "bot":{"PT":"Sobre o cartao de credito, consigo consultar fatura, vencimento e limite agora.","EN":"About your credit card, I can check the bill, due date and limit now.","ES":"Sobre la tarjeta de credito, puedo consultar factura, vencimiento y limite ahora."}},
 "Investimentos CDB":{"peso_cde":0.06,"peso_nac":0.13,"produto":"CDB","p_bot":0.50,"area":"Investimentos",
  "openings":{"PT":["Qual a diferenca entre CDB prefixado e pos-fixado?","Quanto rende o CDB no IPCA?","Como invisto no CDB pelo app?"],"EN":["What's the difference between fixed and floating CDB?","How much does the IPCA CDB yield?","How do I invest in CDB via the app?"],"ES":["Cual es la diferencia entre CDB prefijado y posfijado?","Cuanto rinde el CDB en IPCA?","Como invierto en CDB desde la app?"]},
  "bot":{"PT":"Oferecemos CDB Prefixado, Pos-fixado e IPCA. Posso comparar os rendimentos.","EN":"We offer fixed, floating and IPCA CDB. I can compare the yields.","ES":"Ofrecemos CDB prefijado, posfijado e IPCA. Puedo comparar los rendimientos."}},
 "Saldo e Extrato":{"peso_cde":0.05,"peso_nac":0.10,"produto":"Conta Corrente","p_bot":0.60,"area":"Backoffice",
  "openings":{"PT":["Como vejo meu saldo atualizado?","Preciso do extrato dos ultimos 3 meses.","Onde baixo o comprovante da transferencia?"],"EN":["How do I see my updated balance?","I need the statement for the last 3 months.","Where do I download the transfer receipt?"],"ES":["Como veo mi saldo actualizado?","Necesito el extracto de los ultimos 3 meses.","Donde descargo el comprobante de la transferencia?"]},
  "bot":{"PT":"Saldo e extrato ficam na tela inicial em Conta > Extrato. Posso gerar o PDF.","EN":"Balance and statement are on the home screen under Account > Statement. I can generate the PDF.","ES":"Saldo y extracto estan en la pantalla inicial en Cuenta > Extracto. Puedo generar el PDF."}},
 # ---- tema exclusivo de PJ ----
 "Operacoes PJ - Folha e Pagamentos":{"peso_cde":0.0,"peso_nac":0.0,"produto":"Conta PJ","p_bot":0.22,"area":"Atendimento PJ",
  "openings":{"PT":["Preciso cadastrar a folha de pagamento da empresa.","O pagamento em lote dos fornecedores nao processou.","Como incluo um novo socio como usuario da conta PJ?"],"EN":["I need to set up the company payroll.","The batch payment to suppliers didn't process.","How do I add a new partner as a user of the business account?"],"ES":["Necesito registrar la nomina de la empresa.","El pago por lote a proveedores no se proceso.","Como agrego un nuevo socio como usuario de la cuenta PJ?"]},
  "bot":{"PT":"Sobre a conta PJ, consigo verificar folha, pagamentos em lote e usuarios cadastrados.","EN":"For the business account, I can check payroll, batch payments and registered users.","ES":"Sobre la cuenta PJ, puedo verificar nomina, pagos por lote y usuarios registrados."}},
}

# Pesos de assunto EXCLUSIVOS de PJ (perfil corporativo, nao pessoa fisica).
# 'Termos e Documentacao BR' fica de fora: um CNPJ brasileiro nao pergunta o que e CPF.
PESOS_PJ = {
 "Operacoes PJ - Folha e Pagamentos": 0.24,
 "Cambio": 0.22,
 "Bloqueio TED/PIX": 0.18,
 "Alteracao de Limites": 0.15,
 "Cartao de Credito": 0.09,
 "Saldo e Extrato": 0.07,
 "Onboarding - Documentacao": 0.05,
}

ABREV={"PT":{" voce":" vc"," você":" vc"," por favor":" pfv"," porque":" pq"," tambem":" tb"," esta":" ta"},"EN":{" you":" u"," please":" pls"," because":" bc"," are":" r"},"ES":{" por favor":" xfa"," porque":" xq"," tambien":" tb"}}
CS_SWAPS={" urgente":" ASAP"," por favor":" please"," acesso":" access"," problema":" issue"," conta":" account"," obrigado":" thanks"}
EMOJI_POS=["🙏","😊","👍"]; EMOJI_NEG=["😤","😠","😞"]

def wsel(d):
    ks=list(d.keys()); return np.random.choice(ks,p=[d[k] for k in ks])
def sortear(op,pe): return np.random.choice(op,p=pe)
def pesos_por_segmento(seg):
    """Mix de assuntos por segmento. PJ tem perfil proprio (corporativo)."""
    if seg=="PJ":
        cats=list(PESOS_PJ.keys()); pesos=list(PESOS_PJ.values()); tot=sum(pesos)
        return cats,[p/tot for p in pesos]
    ch="peso_cde" if seg=="CDE" else "peso_nac"
    cats=list(ASSUNTOS.keys()); pesos=[ASSUNTOS[c][ch] for c in cats]; tot=sum(pesos)
    return cats,[p/tot for p in pesos]

def aberturas_por_segmento(info,idioma,seg):
    """Escolhe o pool de aberturas coerente com o segmento do cliente.
    PJ -> openings_pj; Nacional -> openings_nac; CDE -> openings (padrao).
    Se a variante nao existir, cai no pool mais proximo (nac -> padrao)."""
    if seg=="PJ":
        for k in ("openings_pj","openings_nac","openings"):
            if k in info: return info[k][idioma]
    if seg=="Correntista Nacional":
        for k in ("openings_nac","openings"):
            if k in info: return info[k][idioma]
    return info["openings"][idioma]
def aplica_typo(t):
    if len(t)<12: return t
    i=random.randint(0,len(t)-2); return t[:i]+t[i]+t[i:]
def estilizar(texto,tech,idioma,sent,primeira=False,code_switch=False):
    t=texto
    if code_switch:
        for k,v in CS_SWAPS.items():
            if k in t and random.random()<0.5: t=t.replace(k,v)
    if tech=="baixo":
        pref={"PT":"Bom dia. ","EN":"Good morning. ","ES":"Buen dia. "}[idioma]
        return (pref+t) if (primeira and random.random()<0.6) else t
    if tech=="alto":
        for k,v in ABREV[idioma].items(): t=t.replace(k,v)
        if random.random()<0.5: t=t.lower()
        if random.random()<0.2: t=aplica_typo(t)
        if random.random()<0.45:
            t+=" "+(random.choice(EMOJI_POS) if sent=="Positivo" else (random.choice(EMOJI_NEG) if sent=="Negativo" else "🙂"))
        return t
    if random.random()<0.2: t=t.replace(" voce"," vc").replace(" você"," vc")
    return t
def escolher_sentimento(p_bot,est,churn=False):
    dif=1-p_bot
    if est=="fim_ok": pn,pp=0.05,0.80
    elif est=="fim_ruim": pn,pp=0.75,0.03
    elif est=="insistencia": pn,pp=0.70,0.02
    elif est=="abertura": pn,pp=0.35*dif+0.10,0.0
    else: pn,pp=0.45*dif,0.0
    if churn and est!="fim_ok": pn=min(pn+0.20,0.92)  # churn nao contamina o fecho positivo
    r=random.random()
    return "Negativo" if r<pn else ("Positivo" if r<pn+pp else "Neutro")
def EXPR_POR_SENT(idioma,s):
    if s=="Negativo": return EXPR_NEG[idioma]
    if s=="Positivo": return EXPR_POS[idioma]
    return [""]
def fala_cliente(est,info,idioma,tech,churn=False,code_switch=False,seg="CDE"):
    s=escolher_sentimento(info["p_bot"],est,churn)
    if est=="abertura": nuc=random.choice(aberturas_por_segmento(info,idioma,seg))
    elif est in ("fim_ok","fim_ruim"): nuc=random.choice(NUCLEO_FECHO[idioma][s])
    else: nuc=random.choice(NUCLEO_FUP[idioma][s])
    cauda="" if est=="fim_ok" else random.choice(EXPR_POR_SENT(idioma,s))
    base=(nuc+" "+cauda).strip() if cauda else nuc
    if churn and s=="Negativo" and random.random()<0.4:
        base=(base+" "+random.choice(CHURN_FRASES[idioma])).strip()
    return estilizar(base,tech,idioma,s,primeira=(est=="abertura"),code_switch=code_switch),s

# ------- carteira de clientes (com peso de volume em lei de potencia) -------
print("Gerando carteira de clientes (arquetipos)...")
clientes=[]
for i in range(1,CONFIG["n_clientes"]+1):
    seg=wsel(CONFIG["prop_segmento"]); arq=wsel(CONFIG["arq_por_segmento"][seg]); a=ARQUETIPOS[arq]
    if seg=="CDE":
        idioma=wsel(a["idioma_cde"]) if a.get("idioma_cde") else wsel({"EN":0.4,"PT":0.4,"ES":0.2})
    elif seg=="PJ":
        idioma=wsel({"PT":0.9,"EN":0.08,"ES":0.02})
    else:
        idioma=wsel({"PT":0.97,"EN":0.02,"ES":0.01})
    if a.get("code_switch"): idioma="PT"
    # id PSEUDONIMIZADO (hash estavel): nao carrega ordem de cadastro nem
    # qualquer vinculo com identificador real - so serve para ligar as tabelas.
    _pid = hashlib.sha256(f"kenzie360|{SEED}|{i}".encode()).hexdigest()[:12].upper()
    clientes.append({"id_cliente":f"CLI-{_pid}","segmento_cliente":seg,"arquetipo":arq,
                     "perfil_tecnologico":a["tech"],"faixa_etaria":a["idade"],"idioma":idioma,
                     "code_switch":bool(a.get("code_switch")),"churn":bool(a.get("churn"))})
# pesos de volume: ~40% dos clientes sao "recorrentes" e concentram os contatos
# extras (lei de potencia entre eles); os demais tendem a 1 unico contato.
_is_rec = np.random.random(len(clientes)) < CONFIG["prop_recorrente"]
_w = np.where(_is_rec, np.random.pareto(1.8, size=len(clientes)) + 1.0, 0.04)
PESO_CLIENTE = _w / _w.sum()

# ================== DESCARACTERIZACAO / LGPD ============================
# Em um export real (Take Blip), o cliente digita dados pessoais no meio da
# conversa: CPF, telefone, e-mail, numero da conta. Aqui reproduzimos esse
# comportamento e aplicamos um PIPELINE DE MASCARAMENTO: o valor bruto NUNCA e
# persistido no dataset - apenas o marcador ([CPF], [TELEFONE], ...).
# Resultado: base com o MESMO teor e completude de um log real, porem
# descaracterizada por design (LGPD by design / minimizacao de dados).
import re as _re

def _dig(n): return "".join(random.choice("0123456789") for _ in range(n))

def gerar_pii(tipo):
    """Gera um valor ficticio no formato real (sera mascarado antes de persistir)."""
    if tipo=="CPF":      return f"{_dig(3)}.{_dig(3)}.{_dig(3)}-{_dig(2)}"
    if tipo=="TELEFONE": return f"+55 {_dig(2)} 9{_dig(4)}-{_dig(4)}"
    if tipo=="EMAIL":    return f"cliente{_dig(4)}@exemplo.com"
    if tipo=="CONTA":    return f"{_dig(5)}-{_dig(1)}"
    return ""

PII_FRASES={
 "PT":{"CPF":"Meu CPF e {v}.","TELEFONE":"Meu telefone e {v}.","EMAIL":"Meu e-mail e {v}.","CONTA":"Minha conta e {v}."},
 "EN":{"CPF":"My tax ID is {v}.","TELEFONE":"My phone number is {v}.","EMAIL":"My email is {v}.","CONTA":"My account number is {v}."},
 "ES":{"CPF":"Mi CPF es {v}.","TELEFONE":"Mi telefono es {v}.","EMAIL":"Mi correo es {v}.","CONTA":"Mi cuenta es {v}."},
}
# Ordem importa: telefone antes de conta (evita casar pedaco do telefone).
REGEX_PII=[
 (_re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "[CPF]"),
 (_re.compile(r"\b[\w.\-]+@[\w\-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
 (_re.compile(r"\+?\d{2}\s?\d{2}\s?9?\d{4}-?\d{4}\b"), "[TELEFONE]"),
 (_re.compile(r"\b\d{5}-\d\b"), "[CONTA]"),
]
def mascarar(texto):
    """Aplica o mascaramento. Devolve (texto_mascarado, qtd_ocorrencias)."""
    n=0
    for rx,ph in REGEX_PII:
        texto,k=rx.subn(ph,texto); n+=k
    return texto,n

# ------- simulacao de uma conversa -------
def simular_conversa(n,cli,categoria,info,inicio,origem):
    idioma=cli["idioma"]; tech=cli["perfil_tecnologico"]; arq=cli["arquetipo"]
    churn=cli["churn"]; cs=cli["code_switch"]; seg=cli["segmento_cliente"]
    turnos,tempos=[],[]; estado={"cursor":inicio}; sent_cli=[]
    def midia_cli():
        r=random.random()
        if r<CONFIG["p_midia_imagem"]: return "imagem"
        if r<CONFIG["p_midia_imagem"]+CONFIG["p_midia_audio"]: return "audio"
        return "texto"
    def push(rem,texto,sent,gap,midia="texto"):
        estado["cursor"]+=timedelta(seconds=gap)
        if rem=="Cliente" and midia=="imagem": texto="[foto anexada] "+texto
        elif rem=="Cliente" and midia=="audio": texto="[audio transcrito] "+texto
        # PIPELINE DE MASCARAMENTO: nenhum dado pessoal bruto e persistido
        texto,nmask=mascarar(texto)
        estado["mask"]=estado.get("mask",0)+nmask
        turnos.append((rem,texto,sent,midia,nmask>0)); tempos.append(estado["cursor"])
        if rem=="Cliente": sent_cli.append(sent)
    def pc(est):  # push cliente: texto coerente com o segmento + eventual PII
        t,s=fala_cliente(est,info,idioma,tech,churn,cs,seg)
        if random.random()<CONFIG["p_pii"]:
            tipo=random.choice(["CPF","TELEFONE","EMAIL","CONTA"])
            t=(t+" "+PII_FRASES[idioma][tipo].format(v=gerar_pii(tipo))).strip()
        push("Cliente",t,s,random.randint(15,120),midia_cli()); return s

    def finalizar(status,transf_iniciada,humano_atendeu,resolvida,categoria_f,produto_f,canal_humano,area,motivo,ruido=False,resolvido_bot=False):
        num_msgs=len(turnos); num_cli=sum(1 for x in turnos if x[0]=="Cliente")
        dur=int((tempos[-1]-tempos[0]).total_seconds()); sg=sent_cli[-1] if sent_cli else "Neutro"
        if ruido or status.startswith(("Sem resposta","Opt-out")):
            csat=None if random.random()<0.93 else sortear([5,4,3],[0.4,0.3,0.3])
        elif status=="Abandonada pelo cliente":
            csat=None if random.random()<0.90 else sortear([1,2,3],[0.5,0.3,0.2])
        elif random.random()<0.40:
            if status=="Resolvida pelo bot": csat=sortear([5,4,3],[0.50,0.35,0.15])
            elif status=="Resolvida por humano": csat=sortear([5,4,3],[0.40,0.40,0.20])
            else: csat=sortear([3,2,1],[0.2,0.4,0.4])
        else: csat=None
        prim=next((x[1] for x in turnos if x[0]=="Cliente"),"")
        # FORMATO PADRONIZADO DA TRANSCRICAO: "[NN] Remetente: texto" separado por " || "
        transc=" || ".join(f"[{i:02d}] {r}: {tx}" for i,(r,tx,_,_,_) in enumerate(turnos,start=1))
        lc={"id_conversa":f"CONV-{n:06d}","id_cliente":cli["id_cliente"],"segmento_cliente":cli["segmento_cliente"],
            "arquetipo":arq,"perfil_tecnologico":tech,"faixa_etaria":cli["faixa_etaria"],"idioma":idioma,
            "origem":origem,"data_hora":inicio.strftime("%Y-%m-%d %H:%M:%S"),"canal_entrada":"WhatsApp","canal_humano":canal_humano,
            "categoria_assunto":categoria_f,"produto_relacionado":produto_f,"primeira_mensagem_cliente":prim,
            "sentimento_geral":sg,"resolvido_bot":resolvido_bot,"transferencia_iniciada":transf_iniciada,"humano_atendeu":humano_atendeu,
            "status_conversa":status,"resolvida":resolvida,"area_encaminhada":area,"motivo_transferencia":motivo,
            "num_mensagens":num_msgs,"num_mensagens_cliente":num_cli,"duracao_seg":dur,"csat":csat,
            "qtd_dados_mascarados":estado.get("mask",0),"transcricao_completa":transc}
        lm=[{"id_conversa":f"CONV-{n:06d}","id_cliente":cli["id_cliente"],"segmento_cliente":cli["segmento_cliente"],
             "idioma":idioma,"categoria_assunto":categoria_f,"ordem":o,"timestamp":ts.strftime("%Y-%m-%d %H:%M:%S"),
             "remetente":r,"texto":tx,"sentimento":se if se else "","tipo_midia":md,"contem_dado_mascarado":mk}
            for o,((r,tx,se,md,mk),ts) in enumerate(zip(turnos,tempos),start=1)]
        return lc,lm

    # ===== DISPARO ATIVO (o BANCO abre) =====
    if origem=="Ativo":
        push("Kenzie",random.choice(ATIVO[idioma]),None,0)
        r=random.random()
        if r<0.35:   # cliente ignora o disparo
            return finalizar("Sem resposta (disparo ativo)",False,False,"Nao aplicavel","Disparo Ativo","N/A","","","")
        if r<0.55:   # opt-out
            push("Cliente",estilizar(random.choice(OPTOUT[idioma]),tech,idioma,"Negativo",primeira=True,code_switch=cs),"Negativo",random.randint(15,120),midia_cli())
            push("Kenzie",BOT_OPTOUT[idioma],None,random.randint(3,20))
            return finalizar("Opt-out / descadastro",False,False,"Nao aplicavel","Disparo Ativo","N/A","","","")
        # engaja -> segue para o fluxo normal (cliente responde com um assunto)
    else:
        # ===== RECEPTIVO: o CLIENTE abre a conversa =====
        if random.random()<CONFIG["p_ruido"]:
            sub=random.choice(list(NOISE.keys())); nd=NOISE[sub]; s0="Positivo" if sub=="autoresolvido" else "Neutro"
            push("Cliente",estilizar(random.choice(nd[idioma]),tech,idioma,s0,primeira=True,code_switch=cs),s0,0,midia_cli())
            push("Kenzie",random.choice(BOT_SAUD[idioma])+" "+random.choice(BOT_RUIDO[idioma]),None,random.randint(3,20))
            if random.random()<0.5:
                fim={"PT":"Obrigado!","EN":"Thanks!","ES":"Gracias!"}[idioma]
                push("Cliente",estilizar(fim,tech,idioma,"Positivo",code_switch=cs),"Positivo",random.randint(10,60),midia_cli())
            return finalizar(nd["status"],False,False,"Nao aplicavel","Ruido / Nao-atendimento","N/A","","","",ruido=True)

    # ===== FLUXO NORMAL =====
    # cliente abre (receptivo) OU responde ao disparo (ativo engajado)
    pc("abertura")
    # a Kenzie sauda + responde. No receptivo ela greeta aqui (o cliente ja falou); no ativo ela ja greetou no disparo.
    saud=(random.choice(BOT_SAUD[idioma])+" ") if origem=="Receptivo" else ""
    push("Kenzie",saud+info["bot"][idioma],None,random.randint(3,20))
    # NLU miss: bot entende errado e o cliente corrige
    if random.random()<CONFIG["p_nlu_miss"]:
        push("Kenzie",random.choice(BOT_ERRO[idioma]),None,random.randint(3,15))
        push("Cliente",estilizar(random.choice(CLI_CORRIGE[idioma]),tech,idioma,"Negativo",code_switch=cs),"Negativo",random.randint(15,90),midia_cli())
        push("Kenzie",info["bot"][idioma],None,random.randint(3,20))
    # vai-e-vem com o bot
    for _ in range(random.randint(1,4)):
        pc("meio"); push("Kenzie",random.choice(BOT_FUP[idioma]),None,random.randint(3,25))

    resolvido_bot=random.random()<info["p_bot"]
    if resolvido_bot:
        pc("fim_ok"); push("Kenzie",random.choice(BOT_FECHA[idioma]),None,random.randint(3,20))
        return finalizar("Resolvida pelo bot",False,False,"Sim",categoria,info["produto"],"","","",resolvido_bot=True)

    p_ab=min(0.18*ARQUETIPOS[arq]["ab"],0.45)
    roll=random.random()
    if roll<p_ab:
        return finalizar("Abandonada pelo cliente",False,False,"Desconhecido",categoria,info["produto"],"","","")
    elif roll<0.90:
        pc("insistencia"); push("Kenzie",random.choice(BOT_ESCALA[idioma]),None,random.randint(3,15))
        canal_humano=wsel(ARQUETIPOS[arq]["canal_hum"])
        if random.random()<0.10:   # transferencia iniciada, mas cliente abandona na fila (humano nao atende)
            return finalizar("Abandonada pelo cliente",True,False,"Desconhecido",categoria,info["produto"],"","","")
        push("Atendente Humano",random.choice(HUM_SAUD[idioma]),None,random.randint(60,900))
        for _ in range(random.randint(1,3)):
            pc("meio"); push("Atendente Humano",random.choice(HUM_TRAB[idioma]),None,random.randint(30,300))
        if random.random()<0.84:
            push("Atendente Humano",random.choice(HUM_RESOLVE[idioma]),None,random.randint(30,240)); pc("fim_ok")
            push("Atendente Humano",random.choice(HUM_FECHA[idioma]),None,random.randint(3,30))
            area=motivo=""
            if random.random()<0.4: area=info["area"]; motivo=random.choice(MOTIVOS_TRANSF)
            return finalizar("Resolvida por humano",True,True,"Sim",categoria,info["produto"],canal_humano,area,motivo)
        area=info["area"]; motivo=random.choice(MOTIVOS_TRANSF)
        push("Atendente Humano",random.choice(HUM_NAO[idioma]).format(a=area),None,random.randint(30,240)); pc("fim_ruim")
        push("Atendente Humano",random.choice(HUM_FECHA[idioma]),None,random.randint(3,30))
        return finalizar("Transferida - sem resolucao",True,True,"Nao",categoria,info["produto"],canal_humano,area,motivo)
    else:
        pc("fim_ruim"); push("Kenzie",random.choice(BOT_SEM[idioma]),None,random.randint(3,15))
        return finalizar("Encerrada sem resolucao",False,False,"Nao",categoria,info["produto"],"","","")

# ------- loop -------
print(f"Gerando {CONFIG['n_conversas']:,} conversas (gemeo v7)...")
conversas,mensagens=[],[]
TOTAL_SEG=int((DATA_FIM-DATA_INICIO).total_seconds())
IDX=np.arange(len(clientes)); CAP=CONFIG["cap_contatos"]
counts=np.ones(len(clientes),dtype=int)   # cada cliente ja tem 1 (cobertura)
for n in range(1,CONFIG["n_conversas"]+1):
    if n<=len(clientes):
        cli=clientes[n-1]
    else:
        idx=int(np.random.choice(IDX,p=PESO_CLIENTE)); tries=0
        while counts[idx]>=CAP and tries<25:
            idx=int(np.random.choice(IDX,p=PESO_CLIENTE)); tries+=1
        counts[idx]+=1; cli=clientes[idx]
    seg_key=cli["segmento_cliente"]
    cats,pesos=pesos_por_segmento(seg_key)
    categoria=sortear(cats,pesos); info=ASSUNTOS[categoria]
    inicio=DATA_INICIO+timedelta(seconds=random.randint(0,TOTAL_SEG))
    if random.random()<0.80: inicio=inicio.replace(hour=random.randint(8,19),minute=random.randint(0,59))
    origem="Ativo" if random.random()<CONFIG["p_ativo"] else "Receptivo"
    lc,lm=simular_conversa(n,cli,categoria,info,inicio,origem)
    conversas.append(lc); mensagens.extend(lm)

df_conv=pd.DataFrame(conversas)
# recorrencia / reabertura (cronologico por cliente)
df_conv=df_conv.sort_values(["id_cliente","data_hora"]).reset_index(drop=True)
df_conv["contatos_previos"]=df_conv.groupby("id_cliente").cumcount()
prev_res=df_conv.groupby("id_cliente")["resolvida"].shift()
df_conv["reabertura"]=((df_conv["contatos_previos"]>0) & (prev_res.isin(["Nao","Desconhecido"])))
df_conv=df_conv.sort_values("data_hora").reset_index(drop=True)
df_msg=pd.DataFrame(mensagens)

df_conv.to_csv(_SAIDA / "dataset_kenzie360_atendimentos.csv",index=False,encoding="utf-8-sig",sep=";")
df_msg.to_csv(_SAIDA / "dataset_kenzie360_mensagens.csv",index=False,encoding="utf-8-sig",sep=";")

print("\n=== GEMEO v7 GERADO ===")
print(f"Conversas: {len(df_conv):,} x {df_conv.shape[1]} col | Mensagens: {len(df_msg):,} x {df_msg.shape[1]} col | Clientes: {df_conv['id_cliente'].nunique():,}")
print(f"Media msgs/conversa: {len(df_msg)/len(df_conv):.1f} | Resolucao bot: {100*df_conv['resolvido_bot'].mean():.1f}%")
print("\nSegmento (%):"); print((df_conv['segmento_cliente'].value_counts(normalize=True)*100).round(1).to_string())
print("\nArquetipos (%):"); print((df_conv['arquetipo'].value_counts(normalize=True)*100).round(1).to_string())
print("\nOrigem (%):"); print((df_conv['origem'].value_counts(normalize=True)*100).round(1).to_string())
print("\nStatus (%):"); print((df_conv['status_conversa'].value_counts(normalize=True)*100).round(1).to_string())
print("\nTipo de midia nas mensagens do cliente (%):")
print((df_msg[df_msg['remetente']=='Cliente']['tipo_midia'].value_counts(normalize=True)*100).round(1).to_string())
print(f"\nReaberturas: {100*df_conv['reabertura'].mean():.1f}% | Clientes recorrentes (>1 contato): {100*(df_conv['contatos_previos'].groupby(df_conv['id_cliente']).max()>0).mean():.1f}%")
print(f"CSAT geral: {df_conv['csat'].mean():.2f} | CSAT humano: {df_conv[df_conv['humano_atendeu']]['csat'].mean():.2f} | branco: {100*df_conv['csat'].isna().mean():.1f}%")
print(f"Transferencia iniciada: {100*df_conv['transferencia_iniciada'].mean():.1f}% | Humano atendeu: {100*df_conv['humano_atendeu'].mean():.1f}%")
_first=df_msg.sort_values(['id_conversa','ordem']).groupby('id_conversa')['remetente'].first()
_tmp=df_conv[['id_conversa','origem']].merge(_first.rename('primeiro'),on='id_conversa')
print("1a mensagem por origem:"); print(pd.crosstab(_tmp['origem'],_tmp['primeiro']).to_string())
