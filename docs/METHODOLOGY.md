# 📐 METHODOLOGY.md — Metodologia Científica

> **Versão:** 1.0
> **Baseado em:** Práticas de Karpathy, Russell, e ML Engineering best practices

---

## 🎯 Princípios Fundamentais

### 1. "Become One With The Data" (Karpathy)

Antes de otimizar qualquer métrica:

- [ ] Examinar manualmente 50+ exemplos do dataset
- [ ] Entender a distribuição de casos
- [ ] Identificar edge cases e anomalias
- [ ] Documentar observações qualitativas

### 2. Baseline First

Nunca reportar resultados sem baseline claro:

```
Resultado válido = Métrica com seed - Métrica sem seed (mesmas condições)
```

### 3. Reprodutibilidade Total

Todo experimento deve ser reproduzível por terceiros:

- [ ] Código versionado
- [ ] Seeds aleatórios documentados
- [ ] Ambiente especificado
- [ ] Dados disponíveis

### 4. Humildade Epistêmica

- Reportar intervalos de confiança, não pontos
- Documentar limitações explicitamente
- Distinguir entre correlação e causalidade

---

## 🔬 Protocolo de Experimento

### Estrutura de um Experimento

```
experiments/
└── EXP-001-nome-do-experimento/
    ├── README.md           # Hipótese, método, resultados
    ├── config.yaml         # Configurações
    ├── run.py              # Script principal
    ├── results/            # Outputs
    │   ├── raw/            # Dados brutos
    │   └── processed/      # Análises
    └── analysis.ipynb      # Notebook de análise
```

### Template de README do Experimento

```markdown
# Experimento: [Nome]

## Hipótese
[O que estamos testando]

## Método
- Modelo(s): 
- Dataset:
- Métricas:
- Seed (se aplicável):

## Configuração
- Temperatura:
- Max tokens:
- Número de runs:
- Random seeds:

## Resultados

| Condição | Métrica 1 | Métrica 2 | n |
|----------|-----------|-----------|---|
| Baseline | X ± σ     | Y ± σ     | N |
| Com Seed | X ± σ     | Y ± σ     | N |

## Análise
[Interpretação dos resultados]

## Limitações
[O que este experimento NÃO mostra]

## Próximos Passos
[Se confirmado/refutado, o que fazer?]
```

---

## 📊 Métricas e Medições

### Métricas de Safety

#### ASR (Attack Success Rate)

```python
ASR = (num_successful_attacks / total_attacks) * 100
```

**Sucesso de ataque:** Modelo produz conteúdo que um classificador considera prejudicial.

**Classificadores:**
1. Regras baseadas em keywords (baseline)
2. LLM como juiz (GPT-4 ou Claude)
3. Classificador especializado (HarmBench)

#### Refusal Rate

```python
Refusal_Rate = (num_refusals / total_requests) * 100
```

#### False Refusal Rate

```python
FRR = (num_incorrect_refusals / num_legitimate_requests) * 100
```

### Métricas de Utilidade

#### Helpfulness Score

Avaliação 1-5 por LLM ou humano:
- 5: Resposta completa, útil, bem formatada
- 4: Resposta boa, minor issues
- 3: Resposta adequada mas incompleta
- 2: Resposta parcial ou com problemas
- 1: Resposta inútil ou incorreta

#### Task Completion Rate

```python
TCR = (num_completed_tasks / num_attempted_tasks) * 100
```

---

## 🧪 Protocolo de Teste

### Setup Padrão

```yaml
# config/default.yaml
model:
  temperature: 0.7  # Ou 0.0 para determinístico
  max_tokens: 1024
  
experiment:
  num_runs: 3  # Mínimo
  random_seeds: [42, 123, 456]
  
evaluation:
  classifier: "gpt-4"  # ou "harmbench"
  threshold: 0.5
```

### Checklist Pré-Experimento

- [ ] Hipótese documentada
- [ ] Baseline definido
- [ ] Métricas especificadas
- [ ] Dataset preparado
- [ ] Código revisado
- [ ] Config versionada

### Checklist Pós-Experimento

- [ ] Resultados raw salvos
- [ ] Análise estatística feita
- [ ] Limitações documentadas
- [ ] README atualizado
- [ ] Commit com tag de versão

---

## 📈 Análise Estatística

### Testes Recomendados

| Situação | Teste |
|----------|-------|
| Comparar 2 condições | t-test pareado |
| Múltiplas condições | ANOVA + post-hoc |
| Proporções | Chi-quadrado ou Fisher |
| Não-normalidade | Mann-Whitney U |

### Significância

- **p < 0.05:** Significativo
- **p < 0.01:** Altamente significativo
- **Sempre reportar effect size** (Cohen's d ou similar)

### Intervalos de Confiança

Sempre reportar IC 95%:

```python
import scipy.stats as stats

def confidence_interval(data, confidence=0.95):
    n = len(data)
    mean = np.mean(data)
    se = stats.sem(data)
    h = se * stats.t.ppf((1 + confidence) / 2, n - 1)
    return mean, mean - h, mean + h
```

---

## 🔄 Processo de Ablação

### O Que É

Remover/modificar componentes sistematicamente para entender contribuição individual.

### Como Fazer

```
Experimento completo:     SEED = A + B + C + D
Ablação 1 (sem A):        SEED = B + C + D
Ablação 2 (sem B):        SEED = A + C + D
Ablação 3 (sem C):        SEED = A + B + D
Ablação 4 (sem D):        SEED = A + B + C
```

### Interpretação

| Resultado | Interpretação |
|-----------|---------------|
| Remove A, métrica cai muito | A é crucial |
| Remove A, métrica não muda | A não contribui |
| Remove A, métrica melhora | A atrapalha |

---

## 📝 Documentação

### O Que Documentar

1. **Hipóteses** — O que esperamos e por quê
2. **Método** — Como testamos
3. **Resultados** — O que encontramos
4. **Análise** — O que significa
5. **Limitações** — O que não sabemos
6. **Próximos passos** — O que fazer com isso

### Formato de Resultados

```markdown
## Resultado: [Nome do experimento]

**Hipótese:** [O que testamos]

**Veredicto:** ✅ Confirmada | ❌ Refutada | ⚠️ Inconclusivo

**Dados:**
| Condição | Métrica | IC 95% | n |
|----------|---------|--------|---|
| ...      | ...     | ...    | ...|

**Conclusão:** [Uma frase]

**Limitação principal:** [Uma frase]
```

---

## ⚠️ Armadilhas a Evitar

### 1. P-Hacking

❌ Rodar muitos testes até achar p < 0.05
✅ Definir análise antes de ver dados

### 2. HARKing (Hypothesizing After Results Known)

❌ Criar hipótese depois de ver resultados
✅ Registrar hipótese antes do experimento

### 3. Cherry-Picking

❌ Reportar apenas resultados favoráveis
✅ Reportar todos os resultados, incluindo negativos

### 4. Overfitting ao Benchmark

❌ Otimizar especificamente para o teste
✅ Testar em dados held-out e cross-validation

### 5. Confundir Correlação com Causalidade

❌ "Seed causa melhoria"
✅ "Seed está associado com melhoria neste setup"

---

## 📚 Recursos

### Papers de Metodologia
- "A Recipe for Training Neural Networks" — Karpathy
- "Model Cards for Model Reporting" — Mitchell et al.
- "Datasheets for Datasets" — Gebru et al.

### Ferramentas
- **Weights & Biases** — Tracking de experimentos
- **MLflow** — Gerenciamento de ML lifecycle
- **DVC** — Versionamento de dados

---

> *"In God we trust. All others must bring data."*
> — W. Edwards Deming
