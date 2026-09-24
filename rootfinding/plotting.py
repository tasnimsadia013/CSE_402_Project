"""Headless PNG and PDF figures suitable for the project presentation."""

from pathlib import Path


def make_plots(out, rows, histories):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    destination = Path(out)/"plots"
    destination.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

    def save(fig, name):
        fig.savefig(destination/f"{name}.png", dpi=180, bbox_inches="tight")
        fig.savefig(destination/f"{name}.pdf", bbox_inches="tight")
        plt.close(fig)

    for suite in dict.fromkeys(r["suite"] for r in rows):
        group = [r for r in rows if r["suite"] == suite]
        methods = list(dict.fromkeys(r["method"] for r in group))
        names = list(dict.fromkeys(r["problem"] for r in group))
        lookup = {(r["problem"], r["method"]): r for r in group}
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        for ax, metric, title in zip(axes, ("iterations", "function_evaluations"), ("Iterations", "Function evaluations")):
            data = np.array([[lookup[n, m][metric] for n in names] for m in methods], dtype=float)
            pic = ax.imshow(np.log1p(data), aspect="auto", cmap="YlGnBu")
            ax.set_xticks(range(len(names)), names, rotation=45)
            ax.set_yticks(range(len(methods)), methods)
            for i, m in enumerate(methods):
                for j, n in enumerate(names):
                    r = lookup[n, m]
                    label = str(int(data[i, j]))+("*" if not r["converged"] else "")
                    ax.text(j, i, label, ha="center", va="center", fontsize=7,
                            color="white" if np.log1p(data[i, j]) > np.log1p(data).max()*.65 else "black")
            ax.set_title(title+" (* failed)")
            fig.colorbar(pic, ax=ax, shrink=.6, label="log(1 + count)")
        fig.suptitle(f"{suite.title()} benchmark — work counts include failed solves")
        fig.tight_layout()
        save(fig, f"{suite}_work")
        fig, ax = plt.subplots(figsize=(10, 5))
        means = [np.mean([lookup[n, m]["wall_mean_us"] for n in names]) for m in methods]
        ax.barh(methods, means, color="#34745a")
        ax.set_xlabel("Mean wall time per problem (µs), including failures")
        ax.set_title(f"{suite.title()} benchmark — execution time")
        fig.tight_layout()
        save(fig, f"{suite}_timing")

    for problem in ("P2", "P11", "S1"):
        methods = [m for m in ("false_position", "static_tf", "adaptive_threshold", "cost_aware", "stagnation_aware") if f"{problem}/{m}" in histories]
        if not methods:
            continue
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        for method in methods:
            trace = histories[f"{problem}/{method}"]["history"]
            if not trace:
                continue
            residuals = [max(h["residual"], 1e-18) for h in trace]
            axes[0].semilogy([h["iteration"] for h in trace], residuals, label=method)
            axes[1].semilogy([h["function_evaluations"] for h in trace], residuals, label=method)
        axes[0].set_xlabel("Iteration")
        axes[1].set_xlabel("Cumulative function evaluations")
        for ax in axes:
            ax.set_ylabel("Selected residual (plot floor 1e-18)")
            ax.grid(alpha=.2)
        axes[1].legend(fontsize=7)
        fig.suptitle(f"{problem} — convergence by steps and by work")
        fig.tight_layout()
        save(fig, f"{problem}_convergence")

    for problem in ("P2", "P11", "S1"):
        methods = [m for m in ("adaptive_threshold", "cost_aware", "stagnation_aware") if f"{problem}/{m}" in histories]
        if not methods:
            continue
        fig, ax = plt.subplots(figsize=(11, 3))
        for i, method in enumerate(methods):
            trace = histories[f"{problem}/{method}"]["history"]
            for kind, color, marker in (("false_position", "#2878ad", "o"), ("trisection", "#e77e22", "s")):
                xs = [h["iteration"] for h in trace if h["selected"] == kind]
                ax.scatter(xs, [i]*len(xs), c=color, marker=marker, s=30, label=kind if i == 0 else None)
        ax.set_yticks(range(len(methods)), methods)
        ax.set_xlabel("Iteration")
        ax.set_title(f"{problem} — policy decisions")
        ax.legend(loc="upper right", fontsize=8)
        ax.margins(y=.5)
        fig.tight_layout()
        save(fig, f"{problem}_switches")
