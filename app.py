import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ---------------------------------------------------------
# 1. Page Config + Professional Dark/Gold Theme
# ---------------------------------------------------------
st.set_page_config(
    page_title="Expire Situation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Main */
    .stApp {
        background-color: #0a0a0a;
        color: #FFD700;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #111111;
        border-right: 1px solid #333333;
    }
    [data-testid="stSidebar"] * {
        color: #FFD700 !important;
    }
    /* Headers */
    h1, h2, h3, h4 {
        color: #FFD700 !important;
        font-weight: 700;
        letter-spacing: 1px;
    }
    /* Metric cards */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #1a1a1a, #111111);
        border: 1.5px solid #FFD700;
        border-radius: 14px;
        padding: 18px 22px;
        box-shadow: 0 4px 20px rgba(255, 215, 0, 0.12);
    }
    [data-testid="stMetricLabel"] {
        color: #FFD700 !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-size: 1.7rem !important;
        font-weight: 700 !important;
    }
    /* Buttons */
    .stButton > button {
        background-color: #FFD700 !important;
        color: #000000 !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        border: none !important;
    }
    .stButton > button:hover {
        background-color: #e6c200 !important;
        color: #000000 !important;
    }
    /* Select / Multiselect */
    .stSelectbox label, .stMultiSelect label {
        color: #FFD700 !important;
    }
    /* Divider */
    hr {
        border-color: #333333 !important;
    }
    /* Dataframe – force dark + gold */
    .stDataFrame, [data-testid="stDataFrame"] {
        background-color: #0a0a0a !important;
    }
    .stDataFrame table {
        background-color: #0a0a0a !important;
        color: #FFD700 !important;
    }
    .stDataFrame th {
        background-color: #1a1a1a !important;
        color: #FFD700 !important;
        font-weight: 700 !important;
        border-bottom: 1px solid #FFD700 !important;
    }
    .stDataFrame td {
        background-color: #0a0a0a !important;
        color: #FFD700 !important;
        border-color: #222222 !important;
    }
    /* Caption */
    .stCaption {
        color: #888888 !important;
    }
</style>
""", unsafe_allow_html=True)


def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.markdown(
            "<h2 style='text-align:center; color:#FFD700; margin-top:100px;'>"
            "🔒 Please enter the password to access the dashboard</h2>",
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            password = st.text_input("Password:", type="password")
            if st.button("Login", use_container_width=True):
                if password == "123456":
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Incorrect password!")
        return False
    return True


if check_password():

    # ---------------------------------------------------------
    # 2. Data Loading – Exact Power Query steps
    # ---------------------------------------------------------
    @st.cache_data(ttl=3600, show_spinner=False)
    def load_and_transform_data():
        # Parquet
        parquet_file_id = "1xlmf0jNJ2WC27Rd88EiRLlWVsEpNELC5"
        parquet_url = f"https://drive.google.com/uc?export=download&id={parquet_file_id}"
        response = requests.get(parquet_url, timeout=90)
        df = pd.read_parquet(io.BytesIO(response.content), engine="fastparquet")

        # Remove columns (exact M list)
        cols_to_remove = [
            "CONFG_SER", "LOT_NO", "SUPP_CODE", "MANF_CODE",
            "TOTAL.COSTS", "MANF_NAME", "ST_NAME", "INV_NO",
            "ITEM_COST", "TOTAL_PROFIT",
        ]
        df = df.drop(columns=[c for c in cols_to_remove if c in df.columns])

        # STORE → Int64
        df["STORE"] = pd.to_numeric(df["STORE"], errors="coerce").astype("Int64")

        # Table1 – Supervision
        table1_sheet_id = "1kY6jzVoHCYhm_0a9uxd9sjtllNnjfFz7"
        table1_url = f"https://docs.google.com/spreadsheets/d/{table1_sheet_id}/export?format=xlsx"
        table1 = pd.read_excel(table1_url, sheet_name=0)
        table1.columns = table1.columns.astype(str).str.strip()

        store_col_t1 = next(
            (c for c in table1.columns if c.lower() in ["store code", "store_code", "storecode"]),
            "Store Code",
        )
        sup_col_t1 = next(
            (c for c in table1.columns if "supervisor" in c.lower()),
            "Supervisor",
        )
        table1[store_col_t1] = pd.to_numeric(table1[store_col_t1], errors="coerce").astype("Int64")

        df = df.merge(
            table1[[store_col_t1, sup_col_t1]],
            left_on="STORE",
            right_on=store_col_t1,
            how="left",
        )
        if store_col_t1 != "STORE":
            df = df.drop(columns=[store_col_t1], errors="ignore")
        if sup_col_t1 != "Supervisor":
            df = df.rename(columns={sup_col_t1: "Supervisor"})

        # Table2 – Branches
        table2_sheet_id = "1i_kxf7J83EDYgr2SzkYlLKjzD9uM4Gie"
        table2_url = f"https://docs.google.com/spreadsheets/d/{table2_sheet_id}/export?format=xlsx"
        table2 = pd.read_excel(table2_url, sheet_name=0)
        table2.columns = table2.columns.astype(str).str.strip()

        store_col_t2 = next(
            (c for c in table2.columns if c.lower() in ["store", "store code", "store_code"]),
            "STORE",
        )
        name_col_t2 = next(
            (c for c in table2.columns if c.lower() in ["name", "branch", "branch_name"]),
            "NAME",
        )
        table2[store_col_t2] = pd.to_numeric(table2[store_col_t2], errors="coerce").astype("Int64")

        df = df.merge(
            table2[[store_col_t2, name_col_t2]],
            left_on="STORE",
            right_on=store_col_t2,
            how="left",
            suffixes=("", "_t2"),
        )
        if store_col_t2 != "STORE":
            df = df.drop(columns=[store_col_t2], errors="ignore")

        # Renames
        df = df.rename(columns={
            name_col_t2: "BRANCH",
            "ITEM": "ITEM_CODE",
            "STORE": "STORE_CODE",
        })

        # Null → NON_SELLING_STORES
        df["Supervisor"] = df["Supervisor"].fillna("NON_SELLING_STORES")
        df["BRANCH"] = df["BRANCH"].fillna("NON_SELLING_STORES")

        # Custom EXPIRE_DATE (exact M logic)
        def format_expiry(val):
            if pd.isna(val):
                return None
            s = str(val).strip()
            if len(s) < 6:
                return s
            return s[:6] + "20" + s[6:]

        df["EXPIRE_DATE"] = df["EXPIRY_DATE"].apply(format_expiry)
        df["EXPIRE_DATE"] = pd.to_datetime(df["EXPIRE_DATE"], errors="coerce", dayfirst=True)

        # Numeric
        for col in ["TOT_SALES", "SALES_PRICE", "QTY"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df["Year-Month"] = df["EXPIRE_DATE"].dt.strftime("%Y-%m")
        df["Year"] = df["EXPIRE_DATE"].dt.year
        df["Month"] = df["EXPIRE_DATE"].dt.month

        if "CLASS_NAME" in df.columns:
            df["CLASS_NAME"] = df["CLASS_NAME"].fillna("OTHER")

        return df

    with st.spinner("Loading data and preparing dashboard..."):
        df = load_and_transform_data()

    # ---------------------------------------------------------
    # 3. Sidebar – From / To Month-Year Filter
    # ---------------------------------------------------------
    st.sidebar.markdown("## Filter Options")

    # Build available years & months from data
    available_years = sorted(df["Year"].dropna().unique().astype(int).tolist())
    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }
    month_options = list(range(1, 13))

    # Default: Current month → Current + 6 months
    today = datetime(2026, 9, 26)          # current date in the environment
    default_from = today.replace(day=1)
    default_to = default_from + relativedelta(months=6)

    default_from_year = default_from.year
    default_from_month = default_from.month
    default_to_year = default_to.year
    default_to_month = default_to.month

    # Ensure defaults exist in data
    if default_from_year not in available_years:
        default_from_year = available_years[0] if available_years else 2026
    if default_to_year not in available_years:
        default_to_year = available_years[-1] if available_years else 2027

    st.sidebar.markdown("### From")
    col_fy, col_fm = st.sidebar.columns(2)
    with col_fy:
        from_year = st.selectbox("Year", options=available_years,
                                 index=available_years.index(default_from_year)
                                 if default_from_year in available_years else 0,
                                 key="from_year")
    with col_fm:
        from_month = st.selectbox("Month", options=month_options,
                                  format_func=lambda x: month_names[x],
                                  index=default_from_month - 1,
                                  key="from_month")

    st.sidebar.markdown("### To")
    col_ty, col_tm = st.sidebar.columns(2)
    with col_ty:
        to_year = st.selectbox("Year", options=available_years,
                               index=available_years.index(default_to_year)
                               if default_to_year in available_years else len(available_years)-1,
                               key="to_year")
    with col_tm:
        to_month = st.selectbox("Month", options=month_options,
                                format_func=lambda x: month_names[x],
                                index=default_to_month - 1,
                                key="to_month")

    # Supervisor filter
    all_supervisors = sorted(df["Supervisor"].dropna().unique())
    selected_supervisors = st.sidebar.multiselect(
        "Supervisor",
        options=all_supervisors,
        default=all_supervisors,
    )

    # Category filter
    all_categories = sorted(df["CLASS_NAME"].dropna().unique()) if "CLASS_NAME" in df.columns else []
    selected_categories = st.sidebar.multiselect(
        "Category",
        options=all_categories,
        default=all_categories,
    ) if all_categories else []

    # Build date range filter
    from_period = from_year * 100 + from_month
    to_period = to_year * 100 + to_month

    mask = (
        (df["Year"] * 100 + df["Month"] >= from_period) &
        (df["Year"] * 100 + df["Month"] <= to_period)
    )
    if selected_supervisors:
        mask &= df["Supervisor"].isin(selected_supervisors)
    if selected_categories:
        mask &= df["CLASS_NAME"].isin(selected_categories)

    filtered_df = df[mask]

    # ---------------------------------------------------------
    # 4. Header + KPI Cards
    # ---------------------------------------------------------
    st.markdown(
        "<h1 style='text-align:center; color:#FFD700; letter-spacing:4px; margin-bottom:12px;'>"
        "EXPIRE SITUATION</h1>",
        unsafe_allow_html=True,
    )

    total_sales = filtered_df["TOT_SALES"].sum()
    total_qty = filtered_df["QTY"].sum()
    unique_items = filtered_df["Item_name"].nunique() if "Item_name" in filtered_df.columns else 0
    unique_branches = filtered_df["BRANCH"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Sales", f"{total_sales/1_000_000:,.1f} M SAR")
    k2.metric("Total Quantity", f"{total_qty:,.0f}")
    k3.metric("Unique Items", f"{unique_items:,}")
    k4.metric("Branches", f"{unique_branches:,}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 5. Row 1 – Monthly Bar + Branch Pie
    # ---------------------------------------------------------
    col_bar, col_pie = st.columns([1.7, 1])

    GOLD = "#FFD700"
    DARK_BG = "rgba(0,0,0,0)"
    GRID = "#2a2a2a"

    with col_bar:
        st.subheader("TOTAL SALES VALUE")
        sales_by_month = (
            filtered_df.groupby("Year-Month", as_index=False)["TOT_SALES"]
            .sum()
            .sort_values("Year-Month")
        )
        fig_bar = px.bar(
            sales_by_month,
            x="Year-Month",
            y="TOT_SALES",
            text=[f"{v/1e6:.1f}M" if v >= 1e6 else f"{v/1e3:.0f}K" for v in sales_by_month["TOT_SALES"]],
            color_discrete_sequence=[GOLD],
        )
        fig_bar.update_traces(textposition="outside", marker_line_width=0, textfont_color=GOLD)
        fig_bar.update_layout(
            template="plotly_dark",
            paper_bgcolor=DARK_BG,
            plot_bgcolor=DARK_BG,
            font_color=GOLD,
            margin=dict(t=10, b=40, l=40, r=20),
            yaxis_title="",
            xaxis_title="",
            yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, color=GOLD),
            xaxis=dict(color=GOLD, tickangle=0),
            height=380,
            showlegend=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_pie:
        st.subheader("EXP SALES Val / BRANCH")
        sales_by_branch = (
            filtered_df.groupby("BRANCH", as_index=False)["TOT_SALES"]
            .sum()
            .sort_values("TOT_SALES", ascending=False)
        )
        # Top 7 + Others
        top_n = 7
        if len(sales_by_branch) > top_n:
            top = sales_by_branch.head(top_n).copy()
            others_sum = sales_by_branch.iloc[top_n:]["TOT_SALES"].sum()
            others = pd.DataFrame({"BRANCH": ["Others"], "TOT_SALES": [others_sum]})
            sales_by_branch = pd.concat([top, others], ignore_index=True)

        # Gold-only color sequence
        gold_palette = ["#FFD700", "#E6C200", "#CCAA00", "#B39500", "#998000",
                        "#806B00", "#665500", "#4D4000"]

        fig_pie = px.pie(
            sales_by_branch,
            values="TOT_SALES",
            names="BRANCH",
            hole=0.42,
            color_discrete_sequence=gold_palette,
        )
        fig_pie.update_traces(
            textposition="outside",
            textinfo="percent+label",
            textfont_color=GOLD,
            marker=dict(line=dict(color="#0a0a0a", width=2)),
        )
        fig_pie.update_layout(
            template="plotly_dark",
            paper_bgcolor=DARK_BG,
            plot_bgcolor=DARK_BG,
            font_color=GOLD,
            margin=dict(t=10, b=20, l=10, r=10),
            height=380,
            showlegend=False,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 6. Row 2 – Supervisor | Items Table | Category
    # ---------------------------------------------------------
    col_sup, col_table, col_cat = st.columns([1.15, 1.5, 1.15])

    with col_sup:
        st.subheader("EXP SALES Val / Supervisor")
        sales_by_sup = (
            filtered_df.groupby("Supervisor", as_index=False)["TOT_SALES"]
            .sum()
            .sort_values("TOT_SALES", ascending=True)
            .tail(12)
        )
        fig_sup = px.bar(
            sales_by_sup,
            x="TOT_SALES",
            y="Supervisor",
            orientation="h",
            text=[f"{v/1e6:.1f}M" if v >= 1e6 else f"{v/1e3:.0f}K" for v in sales_by_sup["TOT_SALES"]],
            color_discrete_sequence=[GOLD],
        )
        fig_sup.update_traces(textposition="outside", cliponaxis=False, textfont_color=GOLD)
        fig_sup.update_layout(
            template="plotly_dark",
            paper_bgcolor=DARK_BG,
            plot_bgcolor=DARK_BG,
            font_color=GOLD,
            margin=dict(t=10, b=20, l=10, r=50),
            xaxis_title="",
            yaxis_title="",
            xaxis=dict(gridcolor=GRID, color=GOLD),
            yaxis=dict(color=GOLD),
            height=480,
            showlegend=False,
        )
        st.plotly_chart(fig_sup, use_container_width=True)

    with col_table:
        st.subheader("Top Expiring Items")
        item_agg = (
            filtered_df.groupby(["Item_name", "Year-Month"], as_index=False)
            .agg(
                Sum_of_QTY=("QTY", "sum"),
                Sum_of_TOT_SALES=("TOT_SALES", "sum"),
            )
            .sort_values("Sum_of_TOT_SALES", ascending=False)
        )
        total_row = pd.DataFrame({
            "Item_name": ["Total"],
            "Year-Month": [""],
            "Sum_of_QTY": [item_agg["Sum_of_QTY"].sum()],
            "Sum_of_TOT_SALES": [item_agg["Sum_of_TOT_SALES"].sum()],
        })
        display_df = pd.concat([item_agg.head(50), total_row], ignore_index=True)

        # Style the dataframe (dark bg + gold text)
        def style_table(df_style):
            return (
                df_style
                .format({
                    "Sum_of_QTY": "{:,.0f}",
                    "Sum_of_TOT_SALES": "{:,.0f}",
                })
                .set_properties(**{
                    "background-color": "#0a0a0a",
                    "color": "#FFD700",
                    "border-color": "#222222",
                })
                .set_table_styles([
                    {"selector": "th",
                     "props": [("background-color", "#1a1a1a"),
                               ("color", "#FFD700"),
                               ("font-weight", "700"),
                               ("border-bottom", "1px solid #FFD700")]},
                    {"selector": "td",
                     "props": [("background-color", "#0a0a0a"),
                               ("color", "#FFD700")]},
                ])
            )

        st.dataframe(
            style_table(display_df.style),
            use_container_width=True,
            height=460,
            hide_index=True,
        )

    with col_cat:
        st.subheader("EXP SALES Val / Category")
        if "CLASS_NAME" in filtered_df.columns:
            sales_by_cat = (
                filtered_df.groupby("CLASS_NAME", as_index=False)["TOT_SALES"]
                .sum()
                .sort_values("TOT_SALES", ascending=True)
                .tail(12)
            )
            fig_cat = px.bar(
                sales_by_cat,
                x="TOT_SALES",
                y="CLASS_NAME",
                orientation="h",
                text=[f"{v/1e6:.1f}M" if v >= 1e6 else f"{v/1e3:.0f}K" for v in sales_by_cat["TOT_SALES"]],
                color_discrete_sequence=[GOLD],
            )
            fig_cat.update_traces(textposition="outside", cliponaxis=False, textfont_color=GOLD)
            fig_cat.update_layout(
                template="plotly_dark",
                paper_bgcolor=DARK_BG,
                plot_bgcolor=DARK_BG,
                font_color=GOLD,
                margin=dict(t=10, b=20, l=10, r=50),
                xaxis_title="",
                yaxis_title="",
                xaxis=dict(gridcolor=GRID, color=GOLD),
                yaxis=dict(color=GOLD),
                height=480,
                showlegend=False,
            )
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("Category data not available")

    # ---------------------------------------------------------
    # Footer
    # ---------------------------------------------------------
    st.markdown("---")
    st.caption(
        f"Records shown: {len(filtered_df):,}   |   "
        f"Total Sales: {total_sales:,.0f} SAR   |   "
        f"Period: {month_names[from_month]} {from_year} → {month_names[to_month]} {to_year}"
    )
