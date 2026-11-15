import json
import sys
from .agents import QAgent, RandomAgent, Tracker
from .experiments import evaluate, run_experiment, summarize, train, write_csv
from .settings import ConfigurationError, load_settings, resolve


def run(settings):
    mode = settings["mode"]
    options = settings[mode]
    if mode == "play":
        from .gui import run as play
        play(resolve(options["model"]), options.get("demo", False), options.get("seed", 2026),
             options.get("frames"), resolve(options.get("screenshot")))
    elif mode == "train":
        episodes = options["episodes"]
        train(episodes, options["seed"], options.get("checkpoints", [episodes]),
              options.get("validation_points", 180), options.get("shaping", True),
              resolve(options["output"]), options.get("agent", {}))
    elif mode == "evaluate":
        name = options.get("policy", "q")
        policy = {"q": lambda: QAgent.load(resolve(options["model"])),
                  "random": RandomAgent, "tracking": lambda: Tracker(side="right"),
                  "untrained": QAgent}[name]()
        rows = evaluate(policy, points=options["points"], seed_base=options["seed_base"], label=name)
        output = resolve(options.get("output"))
        if output:
            write_csv(output, rows)
        print(json.dumps(summarize(rows), indent=2))
    elif mode == "experiment":
        run_experiment(resolve(options["protocol"]), resolve(options["output"]),
                       resolve(options["models"]))


def main():
    if len(sys.argv) > 1:
        raise SystemExit("Uruchom bez argumentów. Ustawienia zmień w konfiguracja.yaml.")
    try:
        run(load_settings())
    except (ConfigurationError, FileNotFoundError, ValueError) as error:
        raise SystemExit(f"Błąd konfiguracji: {error}") from None
