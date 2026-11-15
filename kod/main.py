import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from pathlib import Path
import statistics
import time
import yaml
from pong.agents import QAgent, Tracker
from pong.physics import Pong

ROOT = Path(__file__).resolve().parents[1]


def settings():
    with (ROOT / 'konfiguracja.yaml').open(encoding='utf-8') as stream:
        data = yaml.safe_load(stream)
    for key in ('episodes', 'validation_points', 'test_points', 'workers'):
        if type(data[key]) is not int or data[key] <= 0:
            raise ValueError(f'{key} musi być dodatnią liczbą całkowitą.')
    names = [model['name'] for model in data['models']]
    if len(set(names)) != len(names) or not all(name.isidentifier() for name in names):
        raise ValueError('Nazwy modeli muszą być unikalnymi identyfikatorami.')
    if not 0 < data['gamma'] <= 1 or not 0 <= data['epsilon'][1] <= data['epsilon'][0] <= 1:
        raise ValueError('Sprawdź gamma i epsilon w konfiguracji.')
    for model in data['models']:
        if model['cell'] <= 0 or not 0 < model['alpha'] <= 1:
            raise ValueError('Sprawdź cell i alpha w konfiguracji.')
    return data


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def evaluate(agent, name, points, seed):
    env, opponent = Pong(), Tracker()
    rows = []
    for point in range(points):
        obs = env.reset(seed=seed + point)
        while True:
            action = agent.action(env) if isinstance(agent, Tracker) else agent.action(obs)
            result = env.step(action, opponent.action(env))
            obs = env.observe()
            if result.done:
                break
        rows.append({'model': name, 'point': point, 'seed': seed + point,
                     'winner': result.winner, 'hits': env.hits,
                     'seconds': round(env.elapsed, 6)})
    return rows


def summarize(rows):
    return {'win_rate': sum(row['winner'] == 1 for row in rows) / len(rows),
            'mean_hits': statistics.mean(row['hits'] for row in rows),
            'mean_seconds': statistics.mean(row['seconds'] for row in rows)}


def train_model(job):
    data, model = job
    agent = QAgent(cell=model['cell'], alpha=model['alpha'], gamma=data['gamma'], seed=data['seed'])
    env, opponent = Pong(seed=data['seed']), Tracker()
    history = []
    started = time.perf_counter()
    for episode in range(data['episodes'] + 1):
        if episode in data['checkpoints']:
            result = summarize(evaluate(agent, model['name'], data['validation_points'], data['validation_seed']))
            history.append({'model': model['name'], 'episode': episode, **result})
            print(f"{model['name']} {episode}: {result['win_rate']:.1%}", flush=True)
        if episode == data['episodes']:
            break
        obs = env.reset()
        start, end = data['epsilon']
        epsilon = end + (start - end) * max(0, 1 - episode / (data['episodes'] * .85))
        while True:
            action = agent.action(obs, epsilon)
            result = env.step(action, opponent.action(env))
            next_obs = env.observe()
            agent.update(obs, action, result.reward, next_obs, result.terminated)
            obs = next_obs
            if result.done:
                break
    agent.save(ROOT / 'modele' / f"{model['name']}.npz",
               {'seed': data['seed'], 'episodes': data['episodes'], 'epsilon': data['epsilon'],
                'seconds': round(time.perf_counter() - started, 3)})
    return history


def evaluate_models(data):
    rows = []
    for model in data['models']:
        agent = QAgent.load(ROOT / 'modele' / f"{model['name']}.npz")
        results = evaluate(agent, model['name'], data['test_points'], data['test_seed'])
        rows.extend(results)
        print(model['name'], summarize(results))
    rows.extend(evaluate(Tracker('right'), 'regula', data['test_points'], data['test_seed']))
    write_csv(ROOT / 'wyniki/ocena.csv', rows)


def main():
    parser = argparse.ArgumentParser(description='Pong')
    parser.add_argument('mode', choices=('play', 'train', 'evaluate'), nargs='?', default='play')
    mode = parser.parse_args().mode
    data = settings()
    if mode == 'play':
        from pong.gui import run
        run(ROOT / data['model'], data['demo'], data['seed'])
    elif mode == 'train':
        with ProcessPoolExecutor(max_workers=data['workers']) as pool:
            histories = list(pool.map(train_model, [(data, model) for model in data['models']]))
        write_csv(ROOT / 'wyniki/uczenie.csv', [row for history in histories for row in history])
        evaluate_models(data)
    else:
        evaluate_models(data)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, FileNotFoundError, yaml.YAMLError) as error:
        raise SystemExit(str(error)) from None
