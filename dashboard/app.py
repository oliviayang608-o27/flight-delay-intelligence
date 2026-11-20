"""Flight Delay Intelligence - Streamlit dashboard (reads MongoDB Atlas, read-only)."""
import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from pymongo import MongoClient

st.set_page_config(page_title="Flight Delay Intelligence", layout="wide")


def get_uri():
    """Read-only URI from Streamlit secrets, an environment variable, or a local .env file (never hard-coded)."""
    try:
        if "ATLAS_URI_RO" in st.secrets:
            return st.secrets["ATLAS_URI_RO"], st.secrets.get("ATLAS_DB", "flightdelay")
    except Exception:
        pass
    if os.environ.get("ATLAS_URI_RO"):
        return os.environ["ATLAS_URI_RO"], os.environ.get("ATLAS_DB", "flightdelay")
    for p in (Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"):
        if p.exists():
            env = dict(l.split("=", 1) for l in p.read_text().splitlines() if "=" in l and not l.startswith("#"))
            env = {k.strip(): v.strip().strip('"').strip("'") for k, v in env.items()}
            if env.get("ATLAS_URI_RO"):
                return env["ATLAS_URI_RO"], env.get("ATLAS_DB", "flightdelay")
    return None, None


@st.cache_resource
def get_db():
    uri, name = get_uri()
    if not uri:
        st.error("No ATLAS_URI_RO found. Add it to Streamlit secrets or to .env (read-only user).")
        st.stop()
    return MongoClient(uri, serverSelectionTimeoutMS=15000)[name]


@st.cache_data(ttl=600)
def load(coll, pipeline=None):
    db = get_db()
    cur = db[coll].aggregate(pipeline) if pipeline else db[coll].find({}, {"_id": 0})
    return pd.DataFrame(list(cur))


@st.cache_data(ttl=30)
def load_live():
    return pd.DataFrame(list(get_db()["live_status"].find({}, {"_id": 0})))


st.title("Flight Delay Intelligence")
st.caption("US flights 2010 - Aug 2026 (105.6M flights, 50 airports with hourly weather). A delay cascade starts with a flight "
           "departing 15+ min late whose lateness is passed on to later flights of the same aircraft. Data: BTS, NOAA, FAA.")

tab1, tab2, tab3, tab4 = st.tabs(["Where & when", "Weather & causes", "Search", "Live FAA status"])

# ---------- Tab 1 ----------
with tab1:
    by_year = load("by_year")
    airports = load("airports")
    total = int(airports["cascades"].sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Cascades found", f"{total:,}")
    c2.metric("Worst year (per 1,000 deps)", str(int(by_year.loc[by_year.per_1000.idxmax(), "Year"])))
    c3.metric("Airports with cascades", len(airports))

    left, right = st.columns(2)
    with left:
        st.subheader("Top cascade-starting airports")
        n = st.slider("How many airports", 5, 25, 10)
        metric = st.radio("Rank by", ["cascades", "cascades_per_1000_departures"], horizontal=True,
                          format_func=lambda x: "Count" if x == "cascades" else "Rate per 1,000 departures")
        top = airports[airports.departures >= 100_000].nlargest(n, metric)
        st.altair_chart(alt.Chart(top).mark_bar().encode(
            x=alt.X(f"{metric}:Q", title=None), y=alt.Y("iata:N", sort="-x", title=None),
            tooltip=["iata", "name", "cascades", "departures", "cascades_per_1000_departures"]), width="stretch")
    with right:
        st.subheader("Cascades by year")
        st.altair_chart(alt.Chart(by_year).mark_line(point=True).encode(
            x=alt.X("Year:O"), y=alt.Y("per_1000:Q", title="Cascades per 1,000 departures"),
            tooltip=["Year", "cascades", "departures", alt.Tooltip("per_1000:Q", format=".1f")]), width="stretch")
        st.caption("2020 is the low point; 2026 covers Jan-Aug only.")

    st.subheader("When do cascades start? (local hour at the origin airport)")
    top_ap = airports.nlargest(15, "cascades")["iata"].tolist()
    pick = st.multiselect("Airports", sorted(airports["iata"]), default=top_ap[:8])
    hh = load("summary_airport_hour", [{"$match": {"airport": {"$in": pick or top_ap}}},
                                       {"$project": {"_id": 0, "airport": 1, "local_hour": 1, "cascades": 1}}])
    if not hh.empty:
        hh = hh.groupby(["airport", "local_hour"], as_index=False)["cascades"].sum()
        st.altair_chart(alt.Chart(hh).mark_rect().encode(
            x=alt.X("local_hour:O", title="Local hour"), y=alt.Y("airport:N", title=None),
            color=alt.Color("cascades:Q", scale=alt.Scale(scheme="orangered")),
            tooltip=["airport", "local_hour", "cascades"]), width="stretch")

# ---------- Tab 2 ----------
with tab2:
    a, b = st.columns(2)
    with a:
        st.subheader("Weather vs. cascades")
        ws = load("weather_split")
        st.altair_chart(alt.Chart(ws).mark_bar().encode(
            x=alt.X("pct_bad_weather:Q", title="% of flights departing in bad weather"), y=alt.Y("grp:N", sort=None, title=None),
            tooltip=["grp", "flights", alt.Tooltip("pct_bad_weather:Q", format=".1f")]), width="stretch")
        st.caption("Cascades start in bad weather ~1.8x more often than all flights, but about 89% still start in good weather.")
    with b:
        st.subheader("Why flights are delayed (top-50 airports)")
        dc = load("delay_classes")
        st.altair_chart(alt.Chart(dc).mark_bar().encode(
            x=alt.X("share_of_minutes_pct:Q", title="% of delay minutes"), y=alt.Y("delay_class:N", sort="-x", title=None),
            tooltip=["delay_class", "delayed_flights", alt.Tooltip("share_of_flights_pct:Q", format=".1f"),
                     alt.Tooltip("share_of_minutes_pct:Q", format=".1f")]), width="stretch")
    st.subheader("BTS-reported causes")
    bc = load("bts_cause")
    st.altair_chart(alt.Chart(bc).mark_bar().encode(x=alt.X("pct:Q", title="% of delay minutes"),
                                                    y=alt.Y("cause:N", sort="-x", title=None)), width="stretch")

# ---------- Tab 3 ----------
with tab3:
    st.subheader("Search airports and cascades (Atlas Search)")
    qtxt = st.text_input("Try 'dallas', 'Chicago 2019', 'ORD'", "dallas")
    if qtxt.strip():
        db = get_db()
        try:
            ap_hits = list(db.airports.aggregate([
                {"$search": {"index": "default", "text": {"query": qtxt, "path": ["name", "city", "iata"], "fuzzy": {"maxEdits": 1}}}},
                {"$limit": 8},
                {"$project": {"_id": 0, "iata": 1, "name": 1, "city": 1, "cascades": 1, "cascades_per_1000_departures": 1,
                              "score": {"$meta": "searchScore"}}}]))
            cs_hits = list(db.cascade_sample.aggregate([
                {"$search": {"index": "default", "text": {"query": qtxt, "path": ["description", "root_origin"]}}},
                {"$limit": 10},
                {"$project": {"_id": 0, "description": 1, "chain_len": 1, "Year": 1, "score": {"$meta": "searchScore"}}}]))
        except Exception as e:
            st.error(f"Search failed: {type(e).__name__}")
            ap_hits, cs_hits = [], []
        st.markdown("**Airports**")
        st.dataframe(pd.DataFrame(ap_hits), width="stretch", hide_index=True)
        st.markdown("**Cascade examples** (50,000-cascade random sample)")
        st.dataframe(pd.DataFrame(cs_hits), width="stretch", hide_index=True)

# ---------- Tab 4 ----------
with tab4:
    st.subheader("Live FAA airport status joined to cascade history")
    live = load_live()
    if live.empty:
        st.info("No live snapshot yet. Run notebook 07_faa_live_stream.ipynb.")
    else:
        st.caption(f"FAA feed update: {live['feed_update_utc'].iloc[0]} UTC  |  fetched: {live['fetched_at_utc'].iloc[0]} UTC")
        real = live[~live["ga_only"]]
        w = real[real["watch"]]
        m1, m2, m3 = st.columns(3)
        m1.metric("Airports with active events", real["airport"].nunique())
        m2.metric("Cascade-prone airports affected", w["airport"].nunique())
        m3.metric("Ground stops / GDPs", int(real["event_type"].isin(["ground_stop", "ground_delay"]).sum()))
        cols = ["airport", "event_type", "category", "reason", "direction", "min_min", "max_min", "avg_min", "trend",
                "cascades", "cascade_rank", "per_1000"]
        cols = [c for c in cols if c in live.columns]
        st.markdown("**Cascade-prone airports with a live event** (expect knock-on delays later today)")
        st.dataframe(w[cols].sort_values("cascade_rank"), width="stretch", hide_index=True)
        st.markdown("**All airline-relevant events**")
        st.dataframe(real[cols].sort_values("cascade_rank", na_position="last"), width="stretch", hide_index=True)
        st.caption("Closures to non-scheduled transient GA are excluded: they do not affect airline flights.")
