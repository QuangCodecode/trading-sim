"""cli/charts.py: line chart and sparkline."""

from tradesim.cli import charts


def plot_rows(lines, height):
    return lines[:height]


def test_chart_has_exact_plot_rows_plus_axes():
    lines = charts.line_chart({"A": [1, 2, 3, 4]}, height=8, width=20)
    assert len(lines) == 8 + 2
    assert all("┤" in line for line in plot_rows(lines, 8))


def test_flat_series_does_not_crash():
    lines = charts.line_chart({"A": [5, 5, 5]}, height=6, width=10)
    assert len(lines) == 8


def test_max_on_top_row_min_on_bottom_row():
    lines = charts.line_chart({"A": [10, 50, 30]}, height=6, width=10)
    top, bottom = lines[0].split("┤")[1], lines[5].split("┤")[1]
    assert "*" in top[3:7] and bottom[0] == "*"


def test_two_series_overlap_draws_hash():
    lines = charts.line_chart({"A": [1, 2], "B": [1, 3]}, height=5, width=10)
    assert lines[4].split("┤")[1][0] == "#"


def test_long_and_short_series_fill_the_width():
    for values in (list(range(200)), [1, 2], [7]):
        lines = charts.line_chart({"A": values}, height=5, width=30)
        assert len(lines[0].split("┤")[1]) == 30


def test_sparkline_length_and_extremes():
    spark = charts.sparkline([3, 1, 2, 8])
    assert len(spark) == 4
    assert spark[1] == "▁" and spark[3] == "█"
