# Graphiques Plotly réutilisables, charte visuelle du projet dataBank CI
# Reusable Plotly charts, dataBank CI's visual identity

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COULEUR_SIDEBAR = "#1A1A2E"
COULEUR_ACCENT = "#FF4500"
COULEUR_POSITIF = "#1E8449"
COULEUR_ATTENTION = "#F39C12"
COULEUR_CRITIQUE = "#E74C3C"
COULEUR_PREMIER = "#6C3483"

PALETTE_CATEGORIELLE = [COULEUR_SIDEBAR, COULEUR_ACCENT, COULEUR_PREMIER, COULEUR_POSITIF, COULEUR_ATTENTION]


def _theme_transparent(fig: go.Figure) -> go.Figure:
    # Applique un fond transparent pour s'adapter au thème clair/sombre de Streamlit
    # Applies a transparent background to adapt to Streamlit's light/dark theme
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def graphique_barres(df: pd.DataFrame, x: str, y: str, titre: str = "") -> go.Figure:
    # Diagramme en barres verticales, couleur d'accent du projet
    # Vertical bar chart, project accent color
    fig = px.bar(df, x=x, y=y, title=titre, color_discrete_sequence=[COULEUR_ACCENT])
    return _theme_transparent(fig)


def graphique_camembert(df: pd.DataFrame, labels: str, values: str, titre: str = "") -> go.Figure:
    # Diagramme circulaire pour une répartition catégorielle
    # Pie chart for a categorical breakdown
    fig = px.pie(df, names=labels, values=values, title=titre, color_discrete_sequence=PALETTE_CATEGORIELLE)
    return _theme_transparent(fig)


def graphique_histogramme(df: pd.DataFrame, colonne: str, titre: str = "") -> go.Figure:
    # Histogramme de distribution d'une variable numérique
    # Distribution histogram of a numeric variable
    fig = px.histogram(df, x=colonne, title=titre, color_discrete_sequence=[COULEUR_SIDEBAR])
    return _theme_transparent(fig)


def graphique_ligne(df: pd.DataFrame, x: str, y: str, titre: str = "") -> go.Figure:
    # Courbe d'évolution dans le temps
    # Time trend line chart
    fig = px.line(df, x=x, y=y, title=titre, color_discrete_sequence=[COULEUR_ACCENT])
    return _theme_transparent(fig)


def graphique_jauge_score(score: float, titre: str = "") -> go.Figure:
    # Jauge colorée RAG (rouge/ambre/vert) pour un score 0-100
    # RAG-colored gauge (red/amber/green) for a 0-100 score
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": titre},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": COULEUR_SIDEBAR},
            "steps": [
                {"range": [0, 33], "color": COULEUR_POSITIF},
                {"range": [33, 66], "color": COULEUR_ATTENTION},
                {"range": [66, 100], "color": COULEUR_CRITIQUE},
            ],
        },
    ))
    return _theme_transparent(fig)


def graphique_barres_horizontales(df: pd.DataFrame, x: str, y: str, titre: str = "") -> go.Figure:
    # Diagramme en barres horizontales, utile pour les classements
    # Horizontal bar chart, useful for rankings
    fig = px.bar(df, x=x, y=y, title=titre, orientation="h", color_discrete_sequence=[COULEUR_ACCENT])
    return _theme_transparent(fig)
