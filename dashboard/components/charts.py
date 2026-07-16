# Graphiques Plotly réutilisables, charte visuelle du projet dataBank CI
# Reusable Plotly charts, dataBank CI's visual identity

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COULEUR_SIDEBAR = "#1A1A2E"

# Couleurs de marque (violet/rose), inspirées de la charte Artefact — jamais
# réutilisées comme couleurs de statut (voir RAG ci-dessous)
# Brand colors (purple/pink), inspired by the Artefact visual identity — never
# reused as status colors (see RAG below)
COULEUR_ACCENT = "#EC0868"
COULEUR_PREMIER = "#8B5CF6"
COULEUR_MASS = "#2E86C1"
COULEUR_TEAL = "#17A398"

# Couleurs RAG (statut de risque uniquement) : jamais réutilisées comme
# identité de segment ou de catégorie, pour ne jamais mélanger les deux sens
# RAG colors (risk status only): never reused as segment/category identity,
# so the two meanings are never conflated
COULEUR_POSITIF = "#1E8449"
COULEUR_ATTENTION = "#F39C12"
COULEUR_CRITIQUE = "#E74C3C"

# Validée par le script six-checks du skill dataviz (lisibilité clair/sombre,
# séparation CVD) : violet, rose, bleu, sarcelle — jamais le navy (illisible
# comme couleur de marque catégorielle, réservé aux fonds/en-têtes)
# Validated by the dataviz skill's six-checks script (light/dark legibility,
# CVD separation): purple, pink, blue, teal — never navy (illegible as a
# categorical brand color, reserved for backgrounds/headers)
PALETTE_CATEGORIELLE = [COULEUR_PREMIER, COULEUR_ACCENT, COULEUR_MASS, COULEUR_TEAL]

# Mapping fixe segment -> couleur, partagé par tous les graphiques qui distinguent les segments
# Fixed segment -> color mapping, shared by every chart that breaks down by segment
SEGMENT_COLOR_MAP = {
    "Mass": COULEUR_MASS,
    "Affluent": COULEUR_TEAL,
    "Premier": COULEUR_PREMIER,
    "Youth": COULEUR_ACCENT,
}

# Mapping fixe niveau de risque -> couleur RAG, pour que High soit toujours
# rouge et jamais une couleur de marque tirée au hasard dans l'ordre des données
# Fixed risk level -> RAG color mapping, so High is always red and never a
# brand color picked arbitrarily from the data's row order
RISK_COLOR_MAP = {
    "Low": COULEUR_POSITIF,
    "Medium": COULEUR_ATTENTION,
    "High": COULEUR_CRITIQUE,
}


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


def graphique_camembert(
    df: pd.DataFrame, labels: str, values: str, titre: str = "", color_col: str = None, color_map: dict = None,
) -> go.Figure:
    # Diagramme circulaire pour une répartition catégorielle ; color_col + color_map
    # permettent de fixer une couleur par valeur exacte (ex: RISK_COLOR_MAP sur la
    # colonne brute risk_band) plutôt que sur l'ordre des données ou un libellé
    # d'affichage qui inclut le décompte (ex: "High (38)")
    # Pie chart for a categorical breakdown; color_col + color_map let the caller fix
    # a color per exact value (e.g. RISK_COLOR_MAP on the raw risk_band column) rather
    # than the data's row order or a display label that includes the count (e.g. "High (38)")
    if color_map:
        fig = px.pie(
            df, names=labels, values=values, title=titre,
            color=color_col or labels, color_discrete_map=color_map,
        )
    else:
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


def graphique_nuage_valeur_engagement(
    df: pd.DataFrame, x: str, y: str, couleur: str, taille: str, titre: str = "", labels: dict = None,
) -> go.Figure:
    # Nuage de points valeur vs engagement, coloré par segment (palette fixe), taille = NBI ;
    # les zones annotées (VIP inactifs, à surveiller, actifs) sont ajoutées par l'appelant
    # via fig.add_shape/add_annotation, propres au contexte métier de chaque page
    # Value vs engagement scatter, colored by segment (fixed palette), size = NBI;
    # annotated zones (inactive VIP, to watch, active) are added by the caller via
    # fig.add_shape/add_annotation, specific to each page's business context
    fig = px.scatter(
        df, x=x, y=y, color=couleur, size=taille, title=titre,
        color_discrete_map=SEGMENT_COLOR_MAP, labels=labels or {},
    )
    return _theme_transparent(fig)


def graphique_pyramide_valeur(
    df: pd.DataFrame, segment_col: str, solde_col: str, nbi_col: str, titre: str = "", labels: dict = None,
) -> go.Figure:
    # Pyramide de valeur : solde et NBI par segment, deux barres horizontales groupées
    # Value pyramid: balance and NBI by segment, two grouped horizontal bars
    df_long = df.melt(
        id_vars=[segment_col], value_vars=[solde_col, nbi_col], var_name="metrique", value_name="valeur",
    )
    fig = px.bar(
        df_long, x="valeur", y=segment_col, color="metrique", orientation="h", barmode="group", title=titre,
        color_discrete_map={solde_col: COULEUR_PREMIER, nbi_col: COULEUR_ACCENT}, labels=labels or {},
    )
    return _theme_transparent(fig)
