"""Streamlit app: extract genera from PDFs, track presence across papers, plot Venn/UpSet."""

import io
from itertools import combinations

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from lib.extractor import extract_genera_from_pdf
from lib.matching import match_extraction
from lib.storage import (
    add_paper_column,
    load_matrix,
    load_warnings,
    merge_uploaded_csv,
    save_matrix,
    save_warnings,
    unique_column_name,
)

st.set_page_config(page_title="Ethno-Balkan Genus Extractor", layout="wide")

# ---------- Session init ----------
if "matrix" not in st.session_state:
    st.session_state.matrix = load_matrix()
if "warnings" not in st.session_state:
    st.session_state.warnings = load_warnings()


def persist() -> None:
    save_matrix(st.session_state.matrix)
    save_warnings(st.session_state.warnings)


# ---------- Sidebar: uploads ----------
st.sidebar.header("Upload")

uploaded_csv = st.sidebar.file_uploader("Existing CSV (merge)", type=["csv"])
if uploaded_csv is not None:
    if st.sidebar.button("Merge CSV into table"):
        try:
            uploaded_df = pd.read_csv(uploaded_csv)
            st.session_state.matrix = merge_uploaded_csv(
                st.session_state.matrix, uploaded_df
            )
            persist()
            st.sidebar.success("Merged.")
        except Exception as e:
            st.sidebar.error(f"Failed to merge CSV: {e}")

uploaded_pdfs = st.sidebar.file_uploader(
    "PDF paper(s)", type=["pdf"], accept_multiple_files=True
)

if uploaded_pdfs and st.sidebar.button(f"Extract from {len(uploaded_pdfs)} PDF(s)"):
    progress = st.sidebar.progress(0.0)
    status = st.sidebar.empty()
    total_cost = 0.0

    for i, pdf in enumerate(uploaded_pdfs, start=1):
        col_name = unique_column_name(
            st.session_state.matrix, pdf.name.rsplit(".", 1)[0]
        )
        status.write(f"Extracting: {pdf.name}")
        try:
            result = extract_genera_from_pdf(pdf.read(), filename=pdf.name)
            matched = match_extraction(result["lines"])
            st.session_state.matrix = add_paper_column(
                st.session_state.matrix, col_name, matched["present"]
            )
            if matched["unknown"]:
                st.session_state.warnings[col_name] = matched["unknown"]
            total_cost += result["cost_usd"]
            persist()
        except Exception as e:
            st.sidebar.error(f"{pdf.name}: {e}")
        progress.progress(i / len(uploaded_pdfs))

    status.write(f"Done. Total cost: ${total_cost:.4f}")

# Download current state
st.sidebar.divider()
csv_buf = st.session_state.matrix.to_csv(index=False).encode("utf-8")
st.sidebar.download_button(
    "Download CSV", csv_buf, file_name="genus_matrix.csv", mime="text/csv"
)

# ---------- Main: editable table ----------
st.title("Genus Presence Across Papers")

paper_cols = [c for c in st.session_state.matrix.columns if c != "Genus"]

if paper_cols:
    edited = st.data_editor(
        st.session_state.matrix,
        num_rows="dynamic",
        width='content',
        height=600,
        column_config={
            "Genus": st.column_config.TextColumn("Genus", disabled=False),
            **{
                c: st.column_config.CheckboxColumn(c, default=False)
                for c in paper_cols
            },
        },
        key="editor",
    )
    if not edited.equals(st.session_state.matrix):
        st.session_state.matrix = edited
        persist()
else:
    st.info("No papers yet. Upload PDFs or a CSV from the sidebar.")
    st.dataframe(st.session_state.matrix, width='content', height=600)

# Manual column add/remove
with st.expander("Add / remove a paper column manually"):
    c1, c2 = st.columns(2)
    with c1:
        new_col = st.text_input("New column name")
        if st.button("Add empty column") and new_col:
            name = unique_column_name(st.session_state.matrix, new_col)
            st.session_state.matrix[name] = False
            persist()
            st.rerun()
    with c2:
        if paper_cols:
            to_drop = st.selectbox("Column to remove", paper_cols, key="drop_sel")
            if st.button("Remove column"):
                st.session_state.matrix = st.session_state.matrix.drop(columns=[to_drop])
                st.session_state.warnings.pop(to_drop, None)
                persist()
                st.rerun()

# ---------- Warnings ----------
if st.session_state.warnings:
    st.subheader("⚠️ Typo / unknown-genus warnings")
    st.caption("Genera the LLM returned that don't match the canonical list. Review and fix manually.")
    for paper, items in st.session_state.warnings.items():
        with st.expander(f"{paper} ({len(items)} flagged)"):
            for item in items:
                sug = f" → suggested: **{item['suggestion']}**" if item["suggestion"] else " → no close match"
                st.write(f"- `{item['raw']}`{sug}")
            if st.button(f"Dismiss warnings for {paper}", key=f"dismiss_{paper}"):
                st.session_state.warnings.pop(paper, None)
                persist()
                st.rerun()

# ---------- Venn / UpSet ----------
st.divider()
st.subheader("Set diagram")

if not paper_cols:
    st.info("Need at least one paper column to plot.")
else:
    selected = st.multiselect(
        "Pick 1–6 papers", paper_cols, default=paper_cols[: min(3, len(paper_cols))]
    )

    if 1 <= len(selected) <= 6:
        sets = {
            p: set(st.session_state.matrix.loc[st.session_state.matrix[p], "Genus"])
            for p in selected
        }

        if len(selected) == 1:
            (p,) = selected
            st.write(f"**{p}**: {len(sets[p])} genera")
            st.write(", ".join(sorted(sets[p])) or "_(none)_")

        elif len(selected) in (2, 3):
            from matplotlib_venn import venn2, venn3

            fig, ax = plt.subplots(figsize=(5, 3))
            if len(selected) == 2:
                venn2([sets[selected[0]], sets[selected[1]]],
                      set_labels=selected, ax=ax)
            else:
                venn3([sets[s] for s in selected], set_labels=selected, ax=ax)
            st.pyplot(fig)

        else:  # 4–6: UpSet plot
            from upsetplot import UpSet, from_contents

            data = from_contents(sets)
            fig = plt.figure(figsize=(10, 5))
            UpSet(data, subset_size="count", show_counts=True).plot(fig=fig)
            st.pyplot(fig)

        # Intersection breakdown
        with st.expander("Intersections breakdown"):
            rows = []
            for r in range(1, len(selected) + 1):
                for combo in combinations(selected, r):
                    inter = set.intersection(*(sets[c] for c in combo))
                    only = inter.copy()
                    for other in selected:
                        if other not in combo:
                            only -= sets[other]
                    rows.append({
                        "papers": " ∩ ".join(combo),
                        "in all of these": len(inter),
                        "exclusively these": len(only),
                    })
            st.dataframe(pd.DataFrame(rows), width='content')
    elif len(selected) > 6:
        st.warning("Pick at most 6 papers.")
