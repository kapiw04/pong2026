import argparse
from pathlib import Path
import json
from .agents import QAgent, RandomAgent, Tracker
from .experiments import ROOT, evaluate, run_experiment, summarize, train, write_csv


def positive(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Wartość musi być dodatnia.")
    return number


def main():
    parser = argparse.ArgumentParser(description="PONG: gra i odtwarzalne eksperymenty Q-learningu")
    commands = parser.add_subparsers(dest="command", required=True)
    play = commands.add_parser("play", help="Gra człowiek kontra wyuczony agent")
    play.add_argument("--model", type=Path, default=ROOT / "modele/pong_q.npz")
    play.add_argument("--demo", action="store_true", help="Reguła kontra agent")
    play.add_argument("--seed", type=int, default=2026)
    play.add_argument("--frames", type=positive, help="Zakończ po N klatkach")
    play.add_argument("--screenshot", type=Path)
    experiment = commands.add_parser("experiment", help="Pełny protokół badawczy")
    experiment.add_argument("--spec", type=Path, default=ROOT / "dane/eksperyment.json")
    experiment.add_argument("--output", type=Path)
    experiment.add_argument("--models", type=Path)
    training = commands.add_parser("train", help="Uczenie pojedynczego modelu")
    training.add_argument("--episodes", type=positive, default=20000)
    training.add_argument("--seed", type=int, default=7)
    training.add_argument("--output", type=Path, default=ROOT / "modele/wlasny.npz")
    evaluation = commands.add_parser("evaluate", help="Test modelu bez uczenia")
    evaluation.add_argument("--model", type=Path, default=ROOT / "modele/pong_q.npz")
    evaluation.add_argument("--policy", choices=["q", "random", "tracking", "untrained"], default="q")
    evaluation.add_argument("--points", type=positive, default=300)
    evaluation.add_argument("--seed-base", type=int, default=2000000)
    evaluation.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "play":
        from .gui import run
        try:
            run(args.model, args.demo, args.seed, args.frames, args.screenshot)
        except FileNotFoundError:
            parser.exit(2, f"Brak modelu: {args.model}. Użyj modelu z katalogu modele/.\n")
    elif args.command == "experiment":
        run_experiment(args.spec, args.output, args.models)
    elif args.command == "train":
        train(args.episodes, args.seed, [args.episodes], 100, out=args.output)
    else:
        policy = {"q": lambda: QAgent.load(args.model), "random": RandomAgent,
                  "tracking": lambda: Tracker(side="right"), "untrained": QAgent}[args.policy]()
        rows = evaluate(policy, points=args.points, seed_base=args.seed_base, label=args.policy)
        if args.output:
            write_csv(args.output, rows)
        print(json.dumps(summarize(rows), indent=2))
