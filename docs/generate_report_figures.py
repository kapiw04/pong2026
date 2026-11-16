import csv
import io
import json
import os
from pathlib import Path
import statistics
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "tmp/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / "tmp/cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator
import numpy as np


OUTPUT = ROOT / "docs/figures"
DATA = ROOT / "docs/data/experiments.zip"
COLORS = ("#245d80", "#56824b", "#b46c3c")


def read_csv(name):
    with ZipFile(DATA) as archive:
        return list(csv.DictReader(io.StringIO(archive.read(name).decode("utf-8"))))


def main():
    history = read_csv("training.csv")
    selection = {row["name"]: row for row in read_csv("selection.csv")}
    summary = {row["model"]: row for row in read_csv("summary.csv")}
    with ZipFile(DATA) as archive:
        metadata = json.loads(archive.read("model_metadata.json"))
    chosen = metadata["test"]["model"]
    family = chosen.rsplit("_s", 1)[0]
    names = sorted((name for name in summary if name.startswith(family + "_s")),
                   key=lambda name: int(name.rsplit("_s", 1)[1]))
    OUTPUT.mkdir(exist_ok=True)
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9,
        "axes.labelsize": 9, "legend.fontsize": 8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#71808b", "axes.labelcolor": "#26323a",
        "xtick.color": "#43505a", "ytick.color": "#43505a",
        "pdf.fonttype": 42, "savefig.facecolor": "white",
    })

    fig, ax = plt.subplots(figsize=(6.25, 2.6), layout="constrained")
    for index, (name, color) in enumerate(zip(names, COLORS), 1):
        points = sorted((r for r in history if r["model"] == name),
                        key=lambda r: int(r["episodes"]))
        if not points:
            raise ValueError(f"Missing training history for {name}.")
        ax.plot([int(r["episodes"]) / 1e6 for r in points],
                [100 * float(r["win_rate"]) for r in points],
                color=color, linewidth=1.5, marker="o", markersize=2.6,
                label=f"Trening {index}")
        checkpoint = int(selection[name]["episodes"])
        point = next(r for r in points if int(r["episodes"]) == checkpoint)
        ax.plot(checkpoint / 1e6, 100 * float(point["win_rate"]), "s",
                color=color, markersize=6, markeredgecolor="white", markeredgewidth=0.8)
    ax.set(xlabel="Liczba epizodów treningu [mln]", ylabel="Wygrane w walidacji [%]",
           xlim=(0, 2.05), ylim=(0, 60))
    ax.xaxis.set_major_locator(MultipleLocator(0.5))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.1f}".replace(".", ",")))
    ax.grid(axis="y", color="#dce2e6", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", ncol=3, frameon=False)
    fig.savefig(OUTPUT / "improved_learning.pdf", metadata={"CreationDate": None})
    plt.close(fig)

    models = [chosen, "poprzedni_w32", "tracker"]
    fig, ax = plt.subplots(figsize=(6.25, 1.85), layout="constrained")
    left = np.zeros(len(models))
    for key, label, color in (("win_rate", "Wygrane", "#56824b"),
                              ("loss_rate", "Straty", "#b36652"),
                              ("draw_rate", "Remisy po limicie", "#c0c9d1")):
        values = np.array([100 * float(summary[name][key]) for name in models])
        ax.barh(range(len(models)), values, left=left, height=0.55, color=color, label=label)
        for i, value in enumerate(values):
            ax.text(left[i] + value / 2, i, f"{value:.2f}%".replace(".", ","),
                    ha="center", va="center", fontsize=8,
                    color="#1e2c36" if key == "draw_rate" else "white")
        left += values
    ax.set(yticks=range(len(models)), yticklabels=["Usprawniony", "Bazowy W32", "Tracker"],
           xlabel="Udział wszystkich 5000 serwisów [%]", xlim=(0, 100))
    ax.invert_yaxis()
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1), ncol=3, frameon=False)
    fig.savefig(OUTPUT / "improved_comparison.pdf", metadata={"CreationDate": None})
    plt.close(fig)

    wins = [100 * float(summary[name]["win_rate"]) for name in names]
    print(f"{chosen}: {float(summary[chosen]['win_rate']):.2%} wins; "
          f"three seeds: {statistics.mean(wins):.2f} +/- {statistics.stdev(wins):.2f} pp")
    matches = read_csv("matches.csv")
    print("Matches:", len(matches), "wins:", sum(int(r["winner"]) == 1 for r in matches),
          "losses:", sum(int(r["winner"]) == -1 for r in matches),
          "unfinished:", sum(int(r["winner"]) == 0 for r in matches))
    print("Figures:", OUTPUT)


if __name__ == "__main__":
    main()
