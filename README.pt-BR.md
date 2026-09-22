# Além da implicação pelas citações

[English](README.md) · **Português brasileiro**

[![validate](https://github.com/sergiofigueras/causal-evidence-audit/actions/workflows/validate.yml/badge.svg)](https://github.com/sergiofigueras/causal-evidence-audit/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Este repositório contém o artigo em [inglês](main.pdf) e em [português brasileiro](main_pt_br.pdf), suas fontes LaTeX e os artefatos completos de reprodutibilidade do estudo piloto da Auditoria Causal da Evidência (CEA, do inglês *Causal Evidence Audit*) com 32 itens. A tradução preserva fórmulas, dados, referências e conclusões da versão em inglês; não constitui um novo experimento.

- Repositório público: <https://github.com/sergiofigueras/causal-evidence-audit>
- Versão imutável do piloto original: <https://github.com/sergiofigueras/causal-evidence-audit/releases/tag/v0.1.0>

## Resumo rápido

**Pergunta de pesquisa:** Se um sistema RAG responde corretamente e cita trechos que sustentam a resposta, isso demonstra que esses trechos determinaram a resposta?

**Resposta curta:** Não necessariamente. Uma resposta observada mostra compatibilidade entre a resposta e as fontes citadas, mas não demonstra dependência causal. O sistema pode recorrer à memória paramétrica, a um atalho ou a um rascunho anterior e acrescentar depois uma citação adequada. A CEA propõe testar a mesma pergunta com as evidências originais, com uma alteração mínima de um fato decisivo que muda a resposta correta e com a remoção de uma fonte indispensável. Para passar, o sistema deve acertar nas duas condições com evidência suficiente, abster-se quando a evidência restante é insuficiente e citar a cadeia completa de prova.

**Relação com avaliações existentes:** Abordagens atuais cobrem partes do problema: [Ragas](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/) mede a fidelidade da resposta ao contexto recuperado; [ContextCite](https://proceedings.neurips.cc/paper_files/paper/2024/hash/adbea136219b64db96a9941e4249a857-Abstract-Conference.html) e [RAGONITE](https://arxiv.org/abs/2412.10571) removem contexto para avaliar atribuição; [SURE-RAG](https://arxiv.org/abs/2605.03534) avalia suficiência da evidência e abstenção seletiva com trocas contrafactuais. Entre as abordagens examinadas no artigo, nenhuma reúne, numa única condição de aprovação por item, respostas corretas em dois mundos de evidências minimamente diferentes, abstenção após a remoção de uma evidência indispensável e citações da cadeia completa de prova determinada pelo oráculo. A contribuição da CEA é esse protocolo conjunto.

**Resultado do piloto:** Em 32 itens fictícios, dois modelos e dois regimes de instrução, a taxa de aprovação observacional em uma única condição, exigindo resposta correta e citações completas, variou de 59,4% a 78,1%. A pontuação causal conjunta baseada em cobertura variou de 0% a 31,3%. A diferença revela falhas que uma verificação isolada pode não detectar, sobretudo respostas quando falta um elemento essencial da prova. O estudo forneceu as evidências diretamente aos modelos: não testou a recuperação de documentos nem estabeleceu como os modelos funcionam internamente.

## CEA-Extended (esquema de dados v2): protocolo proposto

A extensão aborda casos nos quais mudar apenas um fato ou usar apenas um conjunto de prova considerado correto pode produzir uma avaliação enganosa. Um caso do esquema v2 contém a condição de referência, pelo menos duas alterações decisivas independentes, uma perturbação que preserva a resposta, uma ablação que elimina todas as provas válidas, outra que preserva uma prova alternativa e uma condição com política explícita de resolução de conflitos.

Em cada mundo no qual é possível responder, os anotadores registram **todos os conjuntos mínimos de prova admissíveis**. A métrica de cobertura aceita citações de documentos presentes que incluam qualquer um desses conjuntos completos; a métrica estrita exige que as citações correspondam exatamente a um deles. Uma remoção só exige abstenção depois que um oráculo independente confirma que não resta nenhuma prova alternativa. Fontes conflitantes seguem uma política estabelecida antes da avaliação; se o conflito não puder ser resolvido por ela, a resposta correta é abster-se. Uma auditoria separada da recuperação refaz a indexação e a busca após alterações coerentes no corpus e distingue ausência de evidência no corpus, falha de recuperação e erro de geração. Modelos de enunciado, domínios, formatos de prova e estilos de redação das fontes reservados para teste avaliam a generalização.

Este é um **protocolo prospectivo**, acompanhado de um exemplo determinístico e de verificações executáveis da construção. Ele ainda não apresenta novas pontuações de modelos. O piloto original, seus 32 itens, as 384 gerações brutas e as métricas publicadas permanecem inalterados. Passar numa auditoria finita de caixa-preta é evidência de comportamento nos mundos testados, não uma prova de que o sistema sempre depende das evidências; o artigo apresenta um contraexemplo formal.

Os intervalos de Wilson do executor v2 descrevem apenas a variação entre itens tratados como independentes. Modelos de enunciado ou domínios correlacionados exigem uma análise agrupada antes de sustentar conclusões sobre uma população maior.

## Arquivos principais

- `main.tex` e `main.pdf`: artigo original em inglês e PDF compilado.
- `main_pt_br.tex` e `main_pt_br.pdf`: tradução integral em português brasileiro e PDF compilado.
- `references.bib`: referências bibliográficas e URLs das fontes.
- `reproducibility/causal_audit_core.py`: benchmark, analisador de respostas, pontuação e métricas, usando apenas a biblioteca padrão do Python.
- `reproducibility/run_causal_grounding_pilot.py`: execução local com MLX e registro de proveniência.
- `reproducibility/benchmark.json`: os 32 itens e seus mundos de evidências usados no artigo.
- `reproducibility/qwen3-4b_responses.jsonl`: 192 gerações brutas do Qwen.
- `reproducibility/llama3.2-3b_responses.jsonl`: 192 gerações brutas do Llama.
- `reproducibility/summary.json`: métricas agregadas e intervalos de Wilson.
- `reproducibility/run_manifest.json`: versões, parâmetros de geração e hashes dos artefatos.
- `reproducibility/validate_artifacts.py`: validação dos artefatos e comparação com uma reprodução.
- `reproducibility/validate_manuscript.py`: conferência de referências, metadados e correspondência estrutural das duas versões do artigo.
- `reproducibility/extended_fixture.json`: exemplo determinístico do esquema v2; não contém respostas de modelos.
- `reproducibility/validate_extended_fixture.py`: verificações estruturais e lógicas desse exemplo.
- `requirements.in` e `requirements.txt`: dependências diretas e ambiente Python com hashes fixados.
- `Makefile`: comandos de compilação, validação e reprodução.
- `CITATION.cff`: metadados de citação do artigo e dos artefatos.

## Validar os artefatos

A validação usa apenas a biblioteca padrão do Python. Ela regenera o benchmark, reanalisa as 384 respostas brutas, recalcula as pontuações e resumos, verifica os hashes, as referências e os metadados dos dois textos, e valida o exemplo da extensão.

```bash
make validate
```

## Compilar os artigos

```bash
make paper
make paper-pt-br
```

As fontes também podem ser compiladas com uma instalação convencional de LaTeX/BibTeX que inclua os pacotes declarados nos arquivos `.tex`.

## Reproduzir o piloto

O ambiente experimental com hashes fixados exige um Mac com Apple Silicon, Python 3.12 ou superior e aproximadamente 4 GB para os pesos dos modelos. Neste Mac, `/usr/bin/python3` é antigo demais; o exemplo seleciona explicitamente o Python instalado pelo Homebrew.

```bash
PYTHON=/opt/homebrew/bin/python3 make setup
make reproduce-and-validate
```

`make setup` recria `.venv`. `make reproduce` grava uma nova execução com a mesma organização dos arquivos publicados. `make validate-reproduced` valida essa execução; `make compare` exige benchmark e métricas agregadas idênticos, mas informa diferenças no texto bruto ou nos campos analisados, em vez de pressupor reprodução byte a byte.

Os dois regimes completos de instrução e as revisões imutáveis dos modelos estão em `reproducibility/causal_audit_core.py`. A geração usa decodificação gulosa com temperatura zero. Isso elimina a aleatoriedade da amostragem, mas não garante saída idêntica após mudanças de kernel, ambiente de execução, formato de conversa ou hardware.

## Ambiente registrado na versão original

- Data: 2026-09-12
- macOS 26.5.2
- Apple M4 Pro, 14 núcleos de CPU, 48 GB de memória unificada
- Python 3.14.6
- MLX-LM 0.31.3
- MLX 0.32.2
- Transformers 5.17.0
- NumPy 2.5.3
- `mlx-community/Qwen3-4B-4bit`, revisão `4dcb3d101c2a062e5c1d4bb173588c54ea6c4d25`
- `mlx-community/Llama-3.2-3B-Instruct-4bit`, revisão `7f0dc925e0d0afb0322d96f9255cfddf2ba5636e`

Uma verificação com `pip-audit` em 2026-09-12 não encontrou vulnerabilidades conhecidas no conjunto de dependências daquela data. Isso não garante ausência de divulgações futuras; o Dependabot está configurado para acompanhar atualizações.

## Licença

O repositório é distribuído sob a [licença MIT](LICENSE). Os pesos de modelos de terceiros não são redistribuídos e continuam sujeitos às respectivas licenças.
