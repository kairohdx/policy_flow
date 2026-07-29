# PolicyFlow

PolicyFlow is a typed Python engine for contextual rules, explicit
conflict-resolution strategies, and explainable execution traces.

```python
from dataclasses import dataclass

from policyflow import FirstMatch, PolicyEngine, RuleResult, rule


@dataclass(frozen=True)
class Context:
    message: str


@rule(id="say-hello")
def say_hello(ctx: Context):
    if ctx.message.lower() != "hello":
        return RuleResult.pass_(reason="not_a_greeting")
    return RuleResult.consume(effect="Hello!", reason="greeting_detected")


engine = PolicyEngine[Context, str](name="greeting")
engine.add_scope("default", rules=[say_hello], strategy=FirstMatch())

execution = engine.run(Context("hello"), scopes=["default"])

assert execution.decision is not None
assert execution.decision.effect == "Hello!"
```

The application owns its domain context, effects, state transitions, and scope
selection. PolicyFlow owns rule execution, resolution, and tracing.

The project is currently an early implementation based on a real extraction
from a conversational commerce engine.

