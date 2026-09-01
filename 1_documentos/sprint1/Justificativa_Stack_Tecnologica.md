# Justificativa da Escolha da Stack Tecnológica

*(Texto para documentação acadêmica — Seção "Escolha das ferramentas e tecnologias", Sprint 1)*

---

A definição da stack tecnológica do projeto priorizou três critérios centrais:
integração nativa entre as ferramentas, adequação ao caso de uso analítico e
viabilidade econômica para um projeto acadêmico. Optou-se pelo **Google Cloud
Platform (GCP)** como plataforma de nuvem por oferecer um ecossistema
totalmente integrado para engenharia e análise de dados — com destaque para o
BigQuery, Cloud Storage, Pub/Sub e Dataflow —, além de um generoso nível
gratuito (*Free Tier*) e uma curva de aprendizado acessível a iniciantes, o que
reduz a barreira de entrada e o custo operacional da solução. Para o
processamento e a transformação dos dados, adotaram-se **Python e SQL**, hoje
as linguagens padrão de mercado em engenharia de dados: o Python, com
bibliotecas como Pandas e frameworks de NLP, viabiliza a geração da base, a
análise exploratória e a modelagem preditiva/classificatória, enquanto o SQL
executado no BigQuery garante consultas analíticas performáticas sobre grandes
volumes. Por fim, o **Google Looker Studio** foi selecionado para a camada de
visualização por sua conexão nativa e gratuita com o BigQuery, permitindo a
construção de dashboards executivos interativos, com storytelling orientado a
diferentes perfis de stakeholders (diretoria, negócio e técnico), sem custo
adicional de licenciamento. Em conjunto, essa stack forma um pipeline coeso —
da ingestão à visualização — plenamente alinhado às necessidades do projeto e
às boas práticas de mercado, ao mesmo tempo em que respeita as restrições de
orçamento e o perfil da equipe.
