# PolicyFlow

PolicyFlow é um motor Python tipado para regras contextuais, estratégias
explícitas de resolução de conflitos e rastreamento explicável das execuções.

```python
from dataclasses import dataclass

from policyflow import FirstMatch, PolicyEngine, RuleResult, rule


@dataclass(frozen=True)
class Context:
    message: str


@rule(id="say-hello")
def say_hello(ctx: Context):
    if ctx.message.lower() != "olá":
        return RuleResult.pass_(reason="not_a_greeting")
    return RuleResult.consume(effect="Olá!", reason="greeting_detected")


engine = PolicyEngine[Context, str](name="greeting")
engine.add_scope("default", rules=[say_hello], strategy=FirstMatch())

execution = engine.run(Context("olá"), scopes=["default"])

assert execution.decision is not None
assert execution.decision.effect == "Olá!"
```

A aplicação é responsável pelo contexto do domínio, pelos efeitos, pelas
transições de estado e pela seleção dos escopos. O PolicyFlow é responsável
pela execução das regras, pela resolução dos resultados e pelo rastreamento.

Use `CollectAll` quando mais de uma regra puder produzir uma decisão válida:

```python
from policyflow import CollectAll

engine.add_scope(
    "row.validation",
    rules=[validate_identifier, validate_price, validate_stock],
    strategy=CollectAll(),
)

execution = engine.run(row, scopes=["row.validation"])

for decision in execution.decisions:
    print(decision.effect)
```

`execution.decision` permanece como um atalho para a primeira decisão. Códigos
que utilizam estratégias de coleta devem acessar `execution.decisions`.

## Percurso entre scopes

A estratégia configurada em `add_scope()` resolve resultados de regras dentro
daquele scope. Separadamente, uma estratégia de percurso controla se o engine
encerra após um scope produzir decisões ou continua avaliando os demais.

Por padrão, `run()` e `arun()` preservam o comportamento de encerrar no
primeiro scope resolvido. Use `CollectResolvedScopes` para acumular decisões de
todos os scopes solicitados:

```python
from policyflow import CollectResolvedScopes

execution = engine.run(
    context,
    scopes=["scope-a", "scope-b"],
    traversal=CollectResolvedScopes(),
)
```

Scopes sem decisões são ignorados. As decisões são preservadas na ordem dos
scopes e, dentro de cada scope, na ordem selecionada por sua
`ResolutionStrategy`. O PolicyFlow apenas produz decisões; a aplicação continua
responsável por executar seus efeitos.

## Exemplos executáveis

Os exemplos não dependem de serviços externos:

```bash
python examples/conversational_delivery.py
python examples/spreadsheet_validation.py
python examples/crm_automation.py
python examples/freight_import.py
```

Cada exemplo demonstra um comportamento diferente:

| Exemplo | Comportamento |
|---|---|
| Entrega conversacional | Propriedade do contexto, escopos ordenados e `FirstMatch` |
| Validação de planilha | Múltiplas inconsistências com `CollectAll` |
| Automação de CRM | Múltiplos efeitos independentes a partir de uma entrada |
| Importação de frete | Nenhuma, uma ou várias regras de faixa compatíveis |

O exemplo de frete usa `CollectAll` intencionalmente e deixa o domínio
interpretar a quantidade de correspondências. Esse caso fornece evidência para
uma possível estratégia `ExclusiveMatch` no futuro, sem introduzir a abstração
prematuramente.

O projeto ainda está em uma fase inicial e nasceu da extração de problemas
reais encontrados em um motor de comércio conversacional.
