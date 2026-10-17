"""Text charts built from plain lists of numbers. Pure functions → easy to test."""

from tradesim import config

SPARK_LEVELS = "▁▂▃▄▅▆▇█"
MARKERS = "*o+x"
OVERLAP = "#"
LABEL_WIDTH = 9


def scale(value: float, low: float, high: float, steps: int) -> int:
    """Map `value` in [low, high] to a whole step 0..steps-1 (flat ranges map to the middle)."""
    if high == low:
        return steps // 2
    return round((value - low) / (high - low) * (steps - 1))


def sparkline(values: list[float]) -> str:
    """One character per value, from ▁ (lowest) to █ (highest)."""
    low, high = min(values), max(values)
    return "".join(SPARK_LEVELS[scale(v, low, high, len(SPARK_LEVELS))] for v in values)


def resample(values: list[float], width: int) -> list[float]:
    """Stretch or shrink to exactly `width` evenly spaced points, keeping first and last."""
    if len(values) == 1:
        return values * width
    step = (len(values) - 1) / (width - 1)
    return [values[round(i * step)] for i in range(width)]


def line_chart(series: dict[str, list[float]], height: int = config.CHART_HEIGHT,
               width: int = config.CHART_WIDTH) -> list[str]:
    """Draw every series on one grid; returns `height` plot rows + axis + day labels.

    Each series gets its own marker (*, o, …); where two land on the same cell we draw #.
    """
    days = len(next(iter(series.values()))) - 1
    columns = {name: resample(values, width) for name, values in series.items()}
    every_value = [v for values in columns.values() for v in values]
    low, high = min(every_value), max(every_value)
    grid = [[" "] * width for _ in range(height)]
    for marker, values in zip(MARKERS, columns.values()):
        for x, value in enumerate(values):
            row = height - 1 - scale(value, low, high, height)  # row 0 is the top
            grid[row][x] = marker if grid[row][x] in (" ", marker) else OVERLAP
    return add_axes(grid, low, high, days)


def add_axes(grid: list[list[str]], low: float, high: float, days: int) -> list[str]:
    """Label the top, middle and bottom rows with values and add a day axis underneath."""
    height = len(grid)
    labels = {0: high, height // 2: (high + low) / 2, height - 1: low}
    lines = []
    for row, cells in enumerate(grid):
        label = f"{labels[row]:,.2f}" if row in labels else ""
        lines.append(f"{label:>{LABEL_WIDTH}} ┤" + "".join(cells))
    plot_width = len(grid[0])
    lines.append(" " * LABEL_WIDTH + " └" + "─" * plot_width)
    end_label = f"day {days}"
    lines.append(" " * (LABEL_WIDTH + 2) + "day 0".ljust(plot_width - len(end_label)) + end_label)
    return lines
