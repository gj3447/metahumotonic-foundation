"""Two competing providers, real bounded compute, simulated HSWM token billing."""
from .contracts import digest
from .core import Market
from .runner import live_hswm_status, run


def build_demo(path):
    market = Market(path)
    market.bootstrap({"buyer": 100_000, "provider-a": 0, "provider-b": 0})
    for actor, price in [("provider-a", 3), ("provider-b", 2)]:
        market.register_resource(actor, actor + ":cpu", slots=1, memory_mib=256, usl_resource_id="usl:demo:" + actor)
        market.grant(actor, actor + ":grant", actor + ":cpu", provider=actor, expires_at_ms=market.clock() + 60_000)
        rates = {"input_tokens": [price, 1], "output_tokens": [price * 2, 1],
                 "cpu_ms": [1, 10], "memory_mib_ms": [1, 1000]}
        market.publish(actor, actor + ":offer", actor + ":grant", rates=rates, backend="fixture-hswm",
                       model="fixture-model-v1", tokenizer="fixture-tokenizer-v1", cell_id="fixture-cell",
                       configuration_sha256=digest({"profile": "explicit-local-fixture"}))
    task = {"kind": "sum", "n": 10000, "delay_ms": 0}
    limits = {"input_tokens": 100, "output_tokens": 20, "cpu_ms": 1000, "memory_mib_ms": 128000}
    quotes = market.discover("buyer", task=task, limits=limits, backend="fixture-hswm",
                             model="fixture-model-v1", tokenizer="fixture-tokenizer-v1")
    # The demo caller explicitly chooses a quote; discovery never buys resources.
    chosen = quotes[0]
    market.reserve("buyer", "demo-completed", chosen, max_budget=1000)
    receipt = run(market, "provider-b", "demo-completed")
    cancel_quote = market.quote("buyer", "provider-a:offer", task=task, limits=limits)
    market.reserve("buyer", "demo-cancelled", cancel_quote, max_budget=1000)
    market.cancel("buyer", "demo-cancelled")
    return market, {"quotes": quotes, "chosen_offer": chosen["offer_id"], "receipt": receipt,
                    "live_hswm": live_hswm_status(), "live_crypto": {"status": "NOT_CONFIGURED", "asset": None},
                    "mode": "LOCAL_SANDBOX", "model_calls": 0}
