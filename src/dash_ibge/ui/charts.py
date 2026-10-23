from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import polars as pl

from dash_ibge.ui.common import apply_layout
from dash_ibge.ui.theme import COLORWAY


def bar(frame: pl.DataFrame, x: str, y: str, title: str, horizontal: bool = False) -> go.Figure:
    data = frame.drop_nulls([x, y])
    labels = data.get_column(x).to_list()
    values = data.get_column(y).to_list()
    height = max(420, 26 * data.height + 90) if horizontal else 420
    if horizontal:
        fig = go.Figure(go.Bar(y=labels, x=values, orientation="h", marker_color=COLORWAY[0]))
        fig.update_layout(yaxis=dict(autorange="reversed"))
    else:
        fig = go.Figure(go.Bar(x=labels, y=values, marker_color=COLORWAY[0]))
    fig.update_layout(title=title)
    return apply_layout(fig, height)


def line(frame: pl.DataFrame, x: str, y: str, title: str) -> go.Figure:
    data = frame.drop_nulls([x, y]).sort(x)
    fig = go.Figure(go.Scatter(x=data.get_column(x).to_list(), y=data.get_column(y).to_list(), mode="lines+markers", line=dict(color=COLORWAY[0], width=3)))
    fig.update_layout(title=title)
    return apply_layout(fig, 420)


def grouped(frame: pl.DataFrame, x: str, y: str, color: str, title: str) -> go.Figure:
    fig = go.Figure()
    data = frame.drop_nulls([x, y, color])
    categories = data.get_column(color).unique(maintain_order=True).to_list()
    for index, name in enumerate(categories):
        part = data.filter(pl.col(color) == name)
        fig.add_bar(
            x=part.get_column(x).to_list(),
            y=part.get_column(y).to_list(),
            name=str(name),
            marker_color=COLORWAY[index % len(COLORWAY)],
        )
    fig.update_layout(barmode="group", title=title)
    return apply_layout(fig, 440)


def pyramid(frame: pl.DataFrame, age_order: list[str]) -> go.Figure:
    homens = frame.filter(pl.col("sexo_id") == "4").group_by("idade").agg(pl.col("valor_num").sum().alias("homens"))
    mulheres = frame.filter(pl.col("sexo_id") == "5").group_by("idade").agg(pl.col("valor_num").sum().alias("mulheres"))
    merged = (
        pl.DataFrame({"idade": age_order})
        .join(homens, on="idade", how="left")
        .join(mulheres, on="idade", how="left")
    )
    labels = merged.get_column("idade").to_list()
    male = [-float(value or 0) for value in merged.get_column("homens").to_list()]
    female = [float(value or 0) for value in merged.get_column("mulheres").to_list()]
    fig = go.Figure()
    fig.add_bar(y=labels, x=male, name="Homens", orientation="h", marker_color="#1f4e79")
    fig.add_bar(y=labels, x=female, name="Mulheres", orientation="h", marker_color="#c4552a")
    fig.update_layout(barmode="relative", title="População por sexo e grupo de idade")
    return apply_layout(fig, 640)


def bubbles(frame: pl.DataFrame) -> go.Figure:
    data = frame.drop_nulls(["lat", "lon", "populacao", "densidade"])
    population = np.asarray(data.get_column("populacao").to_list(), dtype=float)
    density = np.asarray(data.get_column("densidade").to_list(), dtype=float)
    scale = np.sqrt(np.clip(population, 1, None))
    span = float(scale.max() - scale.min()) or 1.0
    sizes = 10 + 36 * (scale - scale.min()) / span
    fig = go.Figure(
        go.Scattergeo(
            lat=data.get_column("lat").to_list(),
            lon=data.get_column("lon").to_list(),
            text=data.get_column("sigla").to_list(),
            mode="markers+text",
            textposition="top center",
            marker=dict(
                size=sizes,
                color=density,
                colorscale=[[0, "#e7e1d4"], [1, "#0f6e56"]],
                showscale=True,
                colorbar=dict(title="hab/km²"),
                line=dict(width=0.4, color="#1c2834"),
            ),
            customdata=np.column_stack([data.get_column("nome").to_list(), population, density]),
            hovertemplate="%{customdata[0]}<br>População: %{customdata[1]:,.0f}<br>Densidade: %{customdata[2]:,.1f}<extra></extra>",
        )
    )
    fig.update_geos(
        scope="south america",
        showcountries=True,
        showland=True,
        landcolor="#f7f3ea",
        countrycolor="#d9d0c0",
        lataxis_range=[-34, 6],
        lonaxis_range=[-75, -32],
        bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(
        title="Posição aproximada das UFs",
        height=520,
        margin=dict(l=0, r=0, t=48, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Source Sans 3, sans-serif", color="#1c2834"),
    )
    return fig


def scatter(frame: pl.DataFrame, x: str, y: str, color: str, text: str, title: str) -> go.Figure:
    fig = go.Figure()
    data = frame.drop_nulls([x, y, color])
    groups = data.get_column(color).unique(maintain_order=True).to_list()
    for index, name in enumerate(groups):
        part = data.filter(pl.col(color) == name)
        fig.add_scatter(
            x=part.get_column(x).to_list(),
            y=part.get_column(y).to_list(),
            mode="markers+text",
            text=part.get_column(text).to_list(),
            textposition="top center",
            name=f"Grupo {name}",
            marker=dict(size=12, color=COLORWAY[index % len(COLORWAY)]),
        )
    fig.update_layout(title=title)
    return apply_layout(fig, 480)


def heatmap(matrix: np.ndarray, labels: list[str], title: str) -> go.Figure:
    fig = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=labels,
            y=labels,
            colorscale=[[0, "#c4552a"], [0.5, "#f7f3ea"], [1, "#0f6e56"]],
            zmin=-1,
            zmax=1,
            hovertemplate="%{y} × %{x}: %{z:.2f}<extra></extra>",
        )
    )
    fig.update_layout(title=title)
    return apply_layout(fig, 560)
