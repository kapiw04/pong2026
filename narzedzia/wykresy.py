import csv
import json
import os
from pathlib import Path
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / "tmp/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "wyniki"
COLORS = ["#148a76", "#d96e4d", "#517eb8"]


def main():
    summary = json.loads((OUT / "summary.json").read_text())
    history = list(csv.DictReader((OUT / "learning.csv").open()))
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.labelcolor": "#243746", "text.color": "#243746",
                         "axes.titleweight": "bold", "savefig.dpi": 180})
    fig, ax = plt.subplots(figsize=(8.6, 3.6), layout="constrained")
    for variant, label, color in [("q", "Wskazówki i koszt ruchu", COLORS[0]),
                                   ("q_no_shaping", "Bez wskazówek", COLORS[1])]:
        runs = []
        for seed in (7, 19, 41):
            rows = [r for r in history if r["variant"] == variant and int(r["seed"]) == seed]
            x = np.array([int(r["episode"]) for r in rows])
            runs.append([float(r["win_rate"]) * 100 for r in rows])
        data = np.array(runs)
        ax.plot(x, data.mean(axis=0), "o-", color=color, label=label, linewidth=2)
        ax.fill_between(x, data.min(axis=0), data.max(axis=0), color=color, alpha=.12)
    ax.set(xlabel="Epizody uczenia (jeden epizod = jeden punkt)",
           ylabel="Wygrane punkty [%]", ylim=(0, 100), xticks=[0, 5000, 10000, 20000])
    ax.grid(axis="y", alpha=.18)
    ax.legend(frameon=False, loc="lower right")
    fig.savefig(OUT / "uczenie.png")
    for label in fig.findobj(match=matplotlib.text.Text):
        label.set_fontsize(14)
    fig.savefig(OUT / "uczenie_slajd.png")
    plt.close(fig)

    keys = ["untrained/0/standard", "random/0/standard", "tracking/0/standard", "q/7/standard",
            "grid50/7/standard", "grid100/7/standard", "alpha035/7/standard",
            "no_movement_cost/7/standard"]
    labels = ["Przed nauką", "Losowy", "Reguła", "Q, względny", "Siatka 50 px",
              "Siatka 100 px", "Q, alfa 0,35", "Bez kosztu ruchu"]
    fig, ax = plt.subplots(figsize=(8.6, 3.8), layout="constrained")
    values = np.array([summary[k]["win_rate"] * 100 for k in keys])
    low = np.array([summary[k]["win_ci95"][0] * 100 for k in keys])
    high = np.array([summary[k]["win_ci95"][1] * 100 for k in keys])
    ax.barh(labels[::-1], values[::-1], color=[COLORS[0]] * 5 + ["#8395a3"] * 3,
            xerr=np.array([values - low, high - values])[:, ::-1], capsize=3,
            error_kw={"ecolor": "#243746", "elinewidth": 1})
    for y, value in enumerate(values[::-1]):
        ax.text(min(value + 5.5, 94), y, f"{value:.1f}%", va="center", fontsize=9)
    ax.set(xlabel="Wygrane punkty [%], test 450 punktów", xlim=(0, 105))
    ax.grid(axis="x", alpha=.15)
    fig.savefig(OUT / "porownanie.png")
    for label in fig.findobj(match=matplotlib.text.Text):
        label.set_fontsize(14)
    fig.savefig(OUT / "porownanie_slajd.png")
    plt.close(fig)

    scenarios = ["standard", "fast", "simple_physics", "fast_reaction"]
    labels = ["Standard", "Szybsza piłka", "Prosta fizyka", "Szybka reakcja reguły"]
    fig, ax = plt.subplots(figsize=(8.6, 3.4), layout="constrained")
    x = np.arange(4)
    q = np.array([[summary[f"q/{s}/{scene}"]["win_rate"] * 100 for scene in scenarios]
                  for s in (7, 19, 41)])
    tracking = [summary[f"tracking/0/{scene}"]["win_rate"] * 100 for scene in scenarios]
    ax.bar(x - .18, q.mean(axis=0), .35, yerr=q.std(axis=0, ddof=1),
           color=COLORS[0], label="Q: średnia i SD z 3 treningów", capsize=4)
    ax.bar(x + .18, tracking, .35, color=COLORS[1], label="Reguła: jeden przebieg oceny")
    ax.set(xticks=x, xticklabels=labels, ylabel="Wygrane punkty [%]", ylim=(0, 100))
    ax.grid(axis="y", alpha=.18)
    ax.legend(frameon=False, fontsize=9)
    fig.savefig(OUT / "odpornosc.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
