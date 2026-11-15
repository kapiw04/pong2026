from pathlib import Path
from math import isfinite
import yaml

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "konfiguracja.yaml"
FIELDS = {
    "play": {"model": str, "demo": bool, "seed": int, "frames": (int, type(None)),
             "screenshot": (str, type(None))},
    "train": {"episodes": int, "seed": int, "output": str, "checkpoints": list,
              "validation_points": int, "shaping": bool, "agent": dict},
    "evaluate": {"model": str, "policy": str, "points": int, "seed_base": int,
                 "output": (str, type(None))},
    "experiment": {"protocol": str, "output": str, "models": str},
}
AGENT_FIELDS = {"alpha": (int, float), "gamma": (int, float), "movement_cost": (int, float),
                "distance_cost": (int, float), "cell": int}
REQUIRED = {"play": {"model"}, "train": {"episodes", "seed", "output"},
            "evaluate": {"model", "points", "seed_base"},
            "experiment": {"protocol", "output", "models"}}


class ConfigurationError(ValueError):
    pass


def read_yaml(path):
    try:
        with Path(path).open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except yaml.YAMLError as error:
        raise ConfigurationError(f"Niepoprawny YAML w {path}: {error}") from error
    if not isinstance(data, dict):
        raise ConfigurationError(f"Plik {path} musi zawierać mapę ustawień.")
    return data


def check_fields(data, schema, section):
    if not isinstance(data, dict):
        raise ConfigurationError(f"Sekcja {section} musi zawierać mapę ustawień.")
    for key, value in data.items():
        if key not in schema:
            raise ConfigurationError(f"Nieznane ustawienie: {section}.{key}")
        types = schema[key] if isinstance(schema[key], tuple) else (schema[key],)
        if type(value) not in types:
            raise ConfigurationError(f"Niepoprawny typ ustawienia: {section}.{key}")
        if isinstance(value, str) and not value.strip():
            raise ConfigurationError(f"Puste ustawienie: {section}.{key}")
        if key in {"episodes", "points", "frames", "validation_points", "cell"}:
            if value is not None and value <= 0:
                raise ConfigurationError(f"{section}.{key} musi być dodatnie.")


def load_settings(path=SETTINGS_PATH):
    data = read_yaml(path)
    unknown = set(data) - {"mode", *FIELDS}
    if unknown:
        raise ConfigurationError(f"Nieznane sekcje: {', '.join(map(str, unknown))}")
    mode = data.get("mode")
    if mode not in tuple(FIELDS):
        raise ConfigurationError("mode musi mieć wartość play, train, evaluate lub experiment.")
    for section in FIELDS:
        if section in data:
            check_fields(data[section], FIELDS[section], section)
    missing = REQUIRED[mode] - data.get(mode, {}).keys()
    if missing:
        raise ConfigurationError(f"Brak ustawień {mode}: {', '.join(sorted(missing))}")
    training = data.get("train", {})
    options = training.get("agent", {})
    check_fields(options, AGENT_FIELDS, "train.agent")
    for key, value in options.items():
        if type(value) in (int, float) and not isfinite(value):
            raise ConfigurationError(f"train.agent.{key} musi być skończoną liczbą.")
    for key in ("alpha", "gamma"):
        if key in options and not 0 < options[key] <= 1:
            raise ConfigurationError(f"train.agent.{key} musi należeć do (0, 1].")
    for key in ("movement_cost", "distance_cost"):
        if key in options and options[key] < 0:
            raise ConfigurationError(f"train.agent.{key} nie może być ujemne.")

    checkpoints = training.get("checkpoints", [])
    if any(type(n) is not int or n <= 0 or n > training.get("episodes", n) for n in checkpoints):
        raise ConfigurationError("train.checkpoints wymaga dodatnich liczb do wartości episodes.")
    if data.get("evaluate", {}).get("policy", "q") not in ("q", "random", "tracking", "untrained"):
        raise ConfigurationError("evaluate.policy musi mieć wartość q, random, tracking lub untrained.")
    return data


def resolve(value):
    if value is None:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path
