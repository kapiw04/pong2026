import argparse
import csv
import os
from pathlib import Path
import statistics
import yaml
from pong.agents import QAgent, Tracker
from pong.physics import Pong

ROOT = Path(__file__).resolve().parents[1]


def settings():
    return yaml.safe_load((ROOT / 'config.yaml').read_text())


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def evaluate(agent, name, points, seed):
    env, opponent = Pong(agent.cfg), Tracker()
    rows = []
    for point in range(points):
        obs = env.reset(seed + point)
        while not env.done:
            result = env.step(agent.action(obs), opponent.action(env))
            obs = env.observe()
        rows.append({'model': name, 'point': point, 'seed': seed + point,
                     'winner': result.winner, 'hits': env.hits, 'seconds': round(env.elapsed, 6)})
    return rows


def summarize(rows):
    return {'win_rate': sum(r['winner'] == 1 for r in rows) / len(rows),
            'loss_rate': sum(r['winner'] == -1 for r in rows) / len(rows),
            'draw_rate': sum(r['winner'] == 0 for r in rows) / len(rows),
            'mean_hits': statistics.mean(r['hits'] for r in rows),
            'mean_seconds': statistics.mean(r['seconds'] for r in rows)}


def train(data):
    cfg = data['training']
    agent = QAgent(cfg['cell'], cfg['alpha'], cfg['gamma'], seed=data['seed'])
    env, opponent = Pong(seed=data['seed']), Tracker()
    best, history = (-1, -1), []
    checkpoint = ROOT / 'tmp/checkpoint.npz'
    for episode in range(cfg['episodes']):
        obs = env.reset()
        high, low = cfg['epsilon']
        epsilon = low + (high - low) * max(0, 1 - episode / cfg['epsilon_decay'])
        while not env.done:
            action = agent.action(obs, epsilon)
            result = env.step(action, opponent.action(env))
            next_obs = env.observe()
            agent.update(obs, action, result.reward, next_obs, result.terminated)
            obs = next_obs
        if (episode + 1) % cfg['checkpoint'] == 0 or episode + 1 == cfg['episodes']:
            metrics = summarize(evaluate(agent, 'best', cfg['validation_points'], cfg['validation_seed']))
            history.append({'seed': data['seed'], 'episodes': episode + 1,
                            'win_rate': metrics['win_rate'], 'selected': 0})
            score = metrics['win_rate'], -metrics['loss_rate']
            if score > best:
                best = score
                for row in history:
                    row['selected'] = 0
                history[-1]['selected'] = 1
                agent.save(checkpoint, {'episodes': episode + 1, 'seed': data['seed']})
            write_csv(ROOT / 'results/training.csv', history)
            print(history[-1], flush=True)
    agent = QAgent.load(checkpoint)
    rows = evaluate(agent, 'candidate', data['points'], data['test_seed'])
    metrics = summarize(rows)
    print(metrics)
    if metrics['win_rate'] > metrics['loss_rate']:
        agent.save(ROOT / data['model'], {**agent.metadata, 'test': metrics})


def matches(data):
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    from pong.gui import Game, Scene, pygame
    game = Game(ROOT / data['model'], demo=True)
    rows = []
    for match in range(data['matches']):
        seed = data['match_seed'] + match
        game.env.rng.seed(seed)
        game.new_match(True)
        pygame.event.pump()
        for decision in range(60000):
            game.point_delay = 0
            game.update(game.env.cfg.decision_dt)
            if game.scene == Scene.FINISHED:
                break
        rows.append({'seed': seed, 'tracker_points': game.score[0], 'agent_points': game.score[1],
                     'winner': 1 if game.score[1] == 7 else -1 if game.score[0] == 7 else 0,
                     'decisions': decision + 1})
    pygame.quit()
    write_csv(ROOT / 'results/matches.csv', rows)
    print({name: sum(r['winner'] == value for r in rows)
           for name, value in (('ai_wins', 1), ('tracker_wins', -1), ('unfinished', 0))})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pong')
    parser.add_argument('mode', choices=('play', 'train', 'evaluate', 'matches'), nargs='?', default='play')
    mode = parser.parse_args().mode
    data = settings()
    if mode == 'play':
        from pong.gui import run
        run(ROOT / data['model'], data['demo'], data['seed'])
    elif mode == 'train':
        train(data)
    elif mode == 'matches':
        matches(data)
    else:
        summary = []
        for path in (data['model'], data['baseline']):
            result = evaluate(QAgent.load(ROOT / path), Path(path).stem, data['points'], data['test_seed'])
            metrics = summarize(result)
            summary.append({'model': Path(path).stem, **metrics})
            print(path, metrics)
        write_csv(ROOT / 'results/summary.csv', summary)
