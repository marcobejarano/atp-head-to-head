import streamlit as st
import duckdb
from streamlit_searchbox import st_searchbox
import plotly.express as px

st.set_page_config(layout="wide")

atp_duck = duckdb.connect('atp.duckdb', read_only=True)

st.title("ATP Head to Head")

def search_players(search_term):
    query = '''
    SELECT DISTINCT winner_name AS player
    FROM matches
    WHERE player ilike '%' || $1 || '%'
    UNION
    SELECT DISTINCT loser_name AS player
    FROM matches
    WHERE player ilike '%' || $1 || '%'
    '''
    values = atp_duck.execute(query, parameters=[search_term]).fetchall()
    return [value[0] for value in values]

st.write(search_players("Novak"))

left, right = st.columns(2)
with left:
    player1 = st_searchbox(search_players, label="Player 1", key="player1_search", default="Roger Federer", placeholder="Roger Federer")
with right:
    player2 = st_searchbox(search_players, label="Player 2", key="player2_search", default="Rafael Nadal", placeholder="Rafael Nadal")

if player1 and player2:
    matches_for_players = atp_duck.execute("""
    SELECT 
        tourney_date,tourney_name, surface, round, 
        rounds.order AS roundOrder, 
        levels.name AS level, levels.rank AS levelRank, 
        winner_name, score
    FROM matches
    JOIN levels ON levels.short_name = matches.tourney_level
    JOIN rounds ON rounds.name = matches.round
    WHERE (loser_name  = $1 AND winner_name = $2) OR
          (loser_name  = $2 AND winner_name = $1)
    ORDER BY tourney_date DESC
    """, [player1, player2]).fetchdf()

    left, middle, right = st.columns(3)
    with left:
        st.markdown(f"<h2 style='text-align: left; '>{player1}</h1>", unsafe_allow_html=True)
    with right:
        st.markdown(f"<h2 style='text-align: right; '>{player2}</h1>", unsafe_allow_html=True)

    player1_wins = matches_for_players[matches_for_players.winner_name == player1].shape[0]
    player2_wins = matches_for_players[matches_for_players.winner_name == player2].shape[0]

    with middle:
        st.markdown(f"<h2 style='text-align: center; '>{player1_wins} vs {player2_wins}</h1>", unsafe_allow_html=True)

    if len(matches_for_players) == 0:
        pass
    else:        
        st.markdown(f'### Matches')
        st.dataframe(matches_for_players.drop(["roundOrder", "level", "levelRank"], axis=1))

        st.markdown(f'### Match Timeline')

        sorted_matches_for_players = atp_duck.sql("""
        FROM matches_for_players
        ORDER BY strftime(tourney_date, '%m-%d')
        """).fetchdf()

        fig = px.scatter(sorted_matches_for_players, 
            x="tourney_date", 
            y="tourney_name", 
            color="winner_name",
            size="roundOrder",
            color_discrete_sequence=["red", "green"],
            category_orders={"tourney_name": sorted_matches_for_players['tourney_name'].drop_duplicates().tolist()},
            hover_data=["score", "winner_name", "round"]
        )

        min_year = sorted_matches_for_players['tourney_date'].dt.year.min()
        max_year = sorted_matches_for_players['tourney_date'].dt.year.max()
        unique_years = list(range(min_year, max_year+2))

        # Add vertical lines for each unique year
        for year in unique_years:
            fig.add_shape(
                type="line",
                x0=f"{year}-01-01", x1=f"{year}-01-01",
                y0=0, y1=1,
                yref="paper",
                layer="below",
                line=dict(color="#efefef", width=2)
            )

        st.plotly_chart(fig, use_container_width=True)
