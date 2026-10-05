"""Deterministic illustrative inputs; no initial distribution policy is implied."""
from copy import deepcopy

from .simulator import EconomySimulator, SimulationError


ALLOWED_ACTIONS = {
    "propose", "assent", "fund", "start", "submit", "accept", "settle",
    "cancel", "dispute", "propose_resolution", "assent_resolution", "resolve",
}


def replay_commands(initial_balances, commands):
    simulator = EconomySimulator(initial_balances)
    for command in commands:
        if set(command) != {"action", "args"} or command["action"] not in ALLOWED_ACTIONS:
            raise SimulationError("unsupported simulation command")
        if not isinstance(command["args"], list):
            raise SimulationError("simulation command arguments must be a list")
        getattr(simulator, command["action"])(*command["args"])
    return simulator


def demo():
    """Normal settlement, pre-work cancellation, and bilateral dispute resolution."""
    initial = {"alice": "100", "bob": "0", "carol": "0"}
    simulator = EconomySimulator(initial)
    commands = []

    def call(action, *args):
        result = getattr(simulator, action)(*args)
        commands.append({"action": action, "args": list(args)})
        return result

    def agreement(agreement_id, provider, price, cap):
        digest = call("propose", agreement_id, "alice", provider, "demo-compute-unit", price, cap)
        call("assent", agreement_id, "alice", digest)
        call("assent", agreement_id, provider, digest)
        call("fund", agreement_id, "alice")

    agreement("work-success", "bob", "2", "5")
    call("start", "work-success", "bob")
    call("submit", "work-success", "bob", "3", "sim:meter/success", "sim:result/success")
    call("accept", "work-success", "alice")
    call("settle", "work-success", "alice", "settlement-success")
    # A retry must not pay again or append another event.
    call("settle", "work-success", "alice", "settlement-success")

    agreement("work-cancelled", "carol", "4", "2")
    call("cancel", "work-cancelled", "alice")

    agreement("work-disputed", "bob", "3", "4")
    call("start", "work-disputed", "bob")
    call("submit", "work-disputed", "bob", "3", "sim:meter/disputed", "sim:result/disputed")
    call("dispute", "work-disputed", "alice", "simulated result disagreement")
    digest = call("propose_resolution", "work-disputed", "alice", "4", "simulated negotiated payment")
    call("assent_resolution", "work-disputed", "alice", digest)
    call("assent_resolution", "work-disputed", "bob", digest)
    call("resolve", "work-disputed", "alice", "resolution-disputed")
    return simulator, deepcopy(initial), deepcopy(commands)
