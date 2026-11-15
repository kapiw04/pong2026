import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time
import numpy as np
from .agents import QAgent, RandomAgent, Tracker
from .config import Config
from .physics import Pong
from .settings import read_yaml


ROOT = Path(__file__).resolve().parents[2]


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def wilson(wins, total):
    if not total:
        return [0.0, 1.0]
    z = 1.95996398454
    p = wins / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** .5) / denominator
    return [center - half, center + half]


def evaluate(policy, config=None, points=300, seed_base=2000000, label="q", run_seed=0,
             reaction_steps=4):
    if points <= 0:
        raise ValueError("points must be positive")
    cfg = config or Config()
    env = Pong(cfg)
    opponent = Tracker(reaction_steps=reaction_steps)
    rows = []
    for i in range(points):
        obs = env.reset(seed=seed_base + i)
        moves = changes = 0
        previous_action = 0

        if isinstance(policy, RandomAgent):
            policy.rng.seed(seed_base + i + 10000000)
        while True:
            action = policy.action(env) if isinstance(policy, Tracker) else policy.action(obs)
            moves += abs(action)
            changes += action != previous_action
            previous_action = action
            result = env.step(action, opponent.action(env))
            obs = env.observe()
            if result.done:
                break
        rows.append({"policy": label, "run_seed": run_seed, "point": i,
                     "environment_seed": seed_base + i, "winner": result.winner,
                     "truncated": int(result.truncated), "hits": env.hits,
                     "agent_hits": env.right_hits, "seconds": round(env.elapsed, 6)})
        rows[-1].update({"decisions": env.steps, "moves": moves, "action_changes": changes})
    return rows


def summarize(rows):
    n = len(rows)
    wins = sum(r["winner"] == 1 for r in rows)
    losses = sum(r["winner"] == -1 for r in rows)
    draws = n - wins - losses

    match_wins = match_losses = match_draws = 0
    for start in range(0, n - 8, 9):
        score = sum(r["winner"] for r in rows[start:start + 9])
        match_wins += score > 0
        match_losses += score < 0
        match_draws += score == 0
    return {"points": n, "wins": wins, "losses": losses, "draws": draws,
            "win_rate": wins / n, "win_ci95": wilson(wins, n),
            "mean_hits": statistics.mean(r["hits"] for r in rows),
            "mean_seconds": statistics.mean(r["seconds"] for r in rows),
            "move_rate": sum(r.get("moves", 0) for r in rows) / max(1, sum(r.get("decisions", 0) for r in rows)),
            "matches": match_wins + match_losses + match_draws,
            "match_wins": match_wins, "match_losses": match_losses,
            "match_draws": match_draws}


def train(episodes, seed, checkpoints, eval_points, shaping=True, out=None,
          agent_options=None, variant="q"):
    cfg = Config()
    env = Pong(cfg, seed=seed)
    agent = QAgent(seed=seed, config=cfg, shaping=shaping, **(agent_options or {}))
    opponent = Tracker()
    history = []
    training = []
    start = time.perf_counter()

    def checkpoint(episode):
        rows = evaluate(agent, cfg, eval_points, 1000000, run_seed=seed)
        summary = summarize(rows)
        history.append({"variant": variant, "seed": seed, "shaping": int(shaping), "episode": episode,
                        "win_rate": summary["win_rate"], "mean_hits": summary["mean_hits"],
                        "draws": summary["draws"]})
        print(f"{variant} seed={seed} episode={episode}: "
              f"validation={summary['win_rate']:.3f}", flush=True)

    checkpoint(0)
    for episode in range(1, episodes + 1):
        obs = env.reset()
        epsilon = .05 + .85 * max(0, 1 - (episode - 1) / (episodes * .85))
        total_reward = 0.0
        while True:
            action = agent.action(obs, epsilon)
            result = env.step(action, opponent.action(env))
            next_obs = env.observe()

            agent.update(obs, action, result.reward, next_obs, result.terminated)
            total_reward += result.reward
            obs = next_obs
            if result.done:
                break
        training.append({"episode": episode, "epsilon": round(epsilon, 6),
                         "winner": result.winner, "truncated": int(result.truncated),
                         "hits": env.hits, "steps": env.steps,
                         "base_reward": round(total_reward, 6)})
        if episode in checkpoints:
            checkpoint(episode)
    agent.metadata = {"training_seed": seed, "episodes": episodes,
                      "epsilon_start": .9, "epsilon_end": .05,
                      "training_seconds": round(time.perf_counter() - start, 3),
                      "validation_seed_base": 1000000}
    if out:
        out = Path(out)
        agent.save(out)
        write_csv(out.with_suffix(".training.csv"), training)
    return agent, history


def _train_job(spec, variant, seed, models):
    options = dict(variant.get("options", {}))
    name = variant["name"]
    path = Path(models) / f"{name}_seed_{seed}.npz"
    _, history = train(spec["episodes"], seed, spec["checkpoints"],
                       spec["validation_points"], variant.get("shaping", True), path,
                       options, name)
    return name, seed, path, history


def run_experiment(spec_path, output=None, models=None):
    spec_path = Path(spec_path)
    spec = read_yaml(spec_path)
    output = Path(output or ROOT / "wyniki")
    models = Path(models or ROOT / "modele")
    output.mkdir(parents=True, exist_ok=True)
    models.mkdir(parents=True, exist_ok=True)
    all_rows, history, summaries = [], [], {}
    started = time.perf_counter()
    cfg = Config()
    scenarios = {"standard": cfg,
                 "fast": replace(cfg, ball_speed=516.0, max_ball_speed=960.0),
                 "simple_physics": replace(cfg, advanced=False),
                 "fast_reaction": cfg}
    jobs = [(v, s) for v in spec["variants"] for s in v.get("seeds", spec["training_seeds"])]
    with ProcessPoolExecutor(max_workers=spec.get("workers", 3)) as pool:
        futures = [pool.submit(_train_job, spec, variant, seed, models) for variant, seed in jobs]
        for future in as_completed(futures):
            variant, seed, model_path, learning = future.result()
            history.extend(learning)
            agent = QAgent.load(model_path)
            for scenario, eval_cfg in scenarios.items():
                if variant != "q" and scenario != "standard":
                    continue
                agent.cfg = eval_cfg
                rows = evaluate(agent, eval_cfg, spec["test_points"],
                                spec["test_seed_base"], variant, seed,
                                reaction_steps=1 if scenario == "fast_reaction" else 4)
                for row in rows:
                    row["scenario"] = scenario
                all_rows.extend(rows)
                summaries[f"{variant}/{seed}/{scenario}"] = summarize(rows)
    for name, policy in [("random", RandomAgent()), ("untrained", QAgent()),
                         ("tracking", Tracker(side="right"))]:
        for scenario, eval_cfg in scenarios.items():
            rows = evaluate(policy, eval_cfg, spec["test_points"], spec["test_seed_base"], name,
                            reaction_steps=1 if scenario == "fast_reaction" else 4)
            for row in rows:
                row["scenario"] = scenario
            all_rows.extend(rows)
            summaries[f"{name}/0/{scenario}"] = summarize(rows)

    primary = models / f"q_seed_{spec['demo_seed']}.npz"
    (models / "pong_q.npz").write_bytes(primary.read_bytes())
    history.sort(key=lambda r: (r["variant"], r["seed"], r["episode"]))
    all_rows.sort(key=lambda r: (r["policy"], r["run_seed"], r["scenario"], r["point"]))
    write_csv(output / "learning.csv", history)
    write_csv(output / "evaluation.csv", all_rows)
    (output / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    manifest = {"protocol": spec, "protocol_file": spec_path.name,
                "protocol_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
                "python": sys.version, "numpy": np.__version__, "platform": platform.platform(),
                "config": cfg.to_dict(), "total_seconds": round(time.perf_counter() - started, 3),
                "models": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(models.glob("*.npz"))}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Experiment completed in {manifest['total_seconds']:.1f}s", flush=True)
    return summaries
