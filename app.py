import io
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ---------------------------------------------------------
# 1. Page Config + Professional Dark/Gold Theme
# ---------------------------------------------------------
st.set_page_config(
    page_title="EXPIRE SITUATION DASHBOARD",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #e6edf3; }
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    h1, h2, h3, h4 { color: #FFD700 !important; font-weight: 700; }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #1c2128, #161b22);
        border: 1px solid #FFD700;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 15px rgba(255, 215, 0, 0.12);
    }
    [data-testid="stMetricLabel"] { color: #FFD700 !important; }
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 1.75rem !important;
        font-weight: 700 !important;
    }
    .stButton > button {
        background-color: #FFD700;
        color: #000;
        font-weight: 600;
        border-radius: 8px;
        border: none;
    }
    .stButton > button:hover { background-color: #e6c200; color: #000; }
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #FFD700 !important;
        color: #000 !important;
    }
    hr { border-color: #30363d; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.markdown(
            "<h2 style='text-align:center; color:#FFD700; margin-top:80px;'>"
            "🔒 يرجى إدخال كلمة السر للدخول للداشبورد</h2>",
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            password = st.text_input("كلمة السر / Password:", type="password")
            if st.button("تسجيل الدخول / Login", use_container_width=True):
                if password == "123456":
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("كلمة السر غير صحيحة!")
        return False
    return True


if check_password():

    # ---------------------------------------------------------
    # 2. Data Loading – Exact Power Query M steps
    # ---------------------------------------------------------
    @st.cache_data(ttl=3600, show_spinner=False)
    def load_and_transform_data():
        # === Source: Parquet (same file as offline) ===
        parquet_file_id = "1xlmf0jNJ2WC27Rd88EiRLlWVsEpNELC5"
        parquet_url = f"https://drive.google.com/uc?export=download&id={parquet_file_id}"
        response = requests.get(parquet_url, timeout=90)
        df = pd.read_parquet(io.BytesIO(response.content), engine="fastparquet")

        # Removed Columns (exactly as in M)
        cols_to_remove = [
            "CONFG_SER", "LOT_NO", "SUPP_CODE", "MANF_CODE",
            "TOTAL.COSTS", "MANF_NAME", "ST_NAME", "INV_NO",
            "ITEM_COST", "TOTAL_PROFIT",
        ]
        df = df.drop(columns=[c for c in cols_to_remove if c in df.columns])

        # Changed Type → STORE to Int64
        df["STORE"] = pd.to_numeric(df["STORE"], errors="coerce").astype("Int64")

        # === Table1 – Supervision Data ===
        table1_sheet_id = "1kY6jzVoHCYhm_0a9uxd9sjtllNnjfFz7"
        table1_url = f"https://docs.google.com/spreadsheets/d/{table1_sheet_id}/export?format=xlsx"
        table1 = pd.read_excel(table1_url, sheet_name=0)
        table1.columns = table1.columns.astype(str).str.strip()

        # Find columns robustly
        store_col_t1 = next(
            (c for c in table1.columns if c.lower() in ["store code", "store_code", "storecode"]),
            "Store Code",
        )
        sup_col_t1 = next(
            (c for c in table1.columns if "supervisor" in c.lower()),
            "Supervisor",
        )
        table1[store_col_t1] = pd.to_numeric(table1[store_col_t1], errors="coerce").astype("Int64")

        # Merged Queries + Expanded Table1 (Supervisor only)
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

        # === Table2 – Branches Data ===
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

        # Merged Queries1 + Expanded Table2 (NAME)
        df = df.merge(
            table2[[store_col_t2, name_col_t2]],
            left_on="STORE",
            right_on=store_col_t2,
            how="left",
            suffixes=("", "_t2"),
        )
        if store_col_t2 != "STORE":
            df = df.drop(columns=[store_col_t2], errors="ignore")

        # Renamed Columns
        df = df.rename(columns={
            name_col_t2: "BRANCH",
            "ITEM": "ITEM_CODE",
            "STORE": "STORE_CODE",
        })

        # Replaced Value (null → NON_SELLING_STORES)
        df["Supervisor"] = df["Supervisor"].fillna("NON_SELLING_STORES")
        df["BRANCH"] = df["BRANCH"].fillna("NON_SELLING_STORES")

        # Added Custom Column → EXPIRE_DATE
        # Text.Start([EXPIRY_DATE], 6) + "20" + Text.Middle([EXPIRY_DATE], 6)
        def format_expiry(val):
            if pd.isna(val):
                return None
            s = str(val).strip()
            if len(s) < 6:
                return s
            return s[:6] + "20" + s[6:]

        df["EXPIRE_DATE"] = df["EXPIRY_DATE"].apply(format_expiry)
        # Changed Type with Locale (ar-EG) → date
        df["EXPIRE_DATE"] = pd.to_datetime(df["EXPIRE_DATE"], errors="coerce", dayfirst=True)

        # Changed Type1 → numeric
        for col in ["TOT_SALES", "SALES_PRICE", "QTY"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Extra useful column (used in every visual)
        df["Year-Month"] = df["EXPIRE_DATE"].dt.strftime("%Y-%m")

        # Clean CLASS_NAME if present
        if "CLASS_NAME" in df.columns:
            df["CLASS_NAME"] = df["CLASS_NAME"].fillna("OTHER")

        return df

    with st.spinner("جاري تحميل البيانات وتجهيز الداشبورد..."):
        df = load_and_transform_data()

    # ---------------------------------------------------------
    # 3. Sidebar Filters
    # ---------------------------------------------------------
    st.sidebar.markdown("## 🎛️ Filter Options")

    available_months = sorted(
        [m for m in df["Year-Month"].dropna().unique() if m not in ("NaT", "None", None)]
    )

    select_all = st.sidebar.checkbox("Select all", value=True)
    default_months = available_months if select_all else available_months[-6:]

    selected_months = st.sidebar.multiselect(
        "Year-Month",
        options=available_months,
        default=default_months,
    )

    all_supervisors = sorted(df["Supervisor"].dropna().unique())
    selected_supervisors = st.sidebar.multiselect(
        "Supervisor",
        options=all_supervisors,
        default=all_supervisors,
    )

    all_categories = sorted(df["CLASS_NAME"].dropna().unique()) if "CLASS_NAME" in df.columns else []
    selected_categories = st.sidebar.multiselect(
        "Category",
        options=all_categories,
        default=all_categories,
    ) if all_categories else []

    # Apply filters
    mask = pd.Series(True, index=df.index)
    if selected_months:
        mask &= df["Year-Month"].isin(selected_months)
    if selected_supervisors:
        mask &= df["Supervisor"].isin(selected_supervisors)
    if selected_categories:
        mask &= df["CLASS_NAME"].isin(selected_categories)

    filtered_df = df[mask]

    # ---------------------------------------------------------
    # 4. Header + KPI Cards
    # ---------------------------------------------------------
    st.markdown(
        "<h1 style='text-align:center; color:#FFD700; letter-spacing:3px; margin-bottom:8px;'>"
        "EXPIRE SITUATION</h1>",
        unsafe_allow_html=True,
    )

    total_sales = filtered_df["TOT_SALES"].sum()
    total_qty = filtered_df["QTY"].sum()
    unique_items = filtered_df["Item_name"].nunique() if "Item_name" in filtered_df.columns else 0
    unique_branches = filtered_df["BRANCH"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Sales", f"{total_sales/1_000_000:,.1f} M")
    k2.metric("Total Quantity", f"{total_qty:,.0f}")
    k3.metric("Unique Items", f"{unique_items:,}")
    k4.metric("Branches", f"{unique_branches:,}")

    st.markdown("---")

    # ---------------------------------------------------------
    # 5. Row 1 – Bar (Monthly) + Pie (BRANCH / Store Type)
    # ---------------------------------------------------------
    col_bar, col_pie = st.columns([1.65, 1])

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
            color_discrete_sequence=["#FFD700"],
        )
        fig_bar.update_traces(textposition="outside", marker_line_width=0)
        fig_bar.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=40, l=40, r=20),
            yaxis_title="",
            xaxis_title="",
            yaxis=dict(gridcolor="#30363d", zerolinecolor="#30363d"),
            height=390,
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
        # Keep top 8 + Others for clean pie (matches the screenshot look)
        top_n = 8
        if len(sales_by_branch) > top_n:
            top = sales_by_branch.head(top_n).copy()
            others_sum = sales_by_branch.iloc[top_n:]["TOT_SALES"].sum()
            others = pd.DataFrame({"BRANCH": ["Others"], "TOT_SALES": [others_sum]})
            sales_by_branch = pd.concat([top, others], ignore_index=True)

        fig_pie = px.pie(
            sales_by_branch,
            values="TOT_SALES",
            names="BRANCH",
            hole=0.38,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_pie.update_traces(
            textposition="outside",
            textinfo="percent+label",
            pull=[0.04] + [0] * (len(sales_by_branch) - 1),
        )
        fig_pie.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=20, l=10, r=10),
            height=390,
            showlegend=False,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # ---------------------------------------------------------
    # 6. Row 2 – Supervisor | Item Table | Category
    # ---------------------------------------------------------
    col_sup, col_table, col_cat = st.columns([1.15, 1.5, 1.15])

    with col_sup:
        st.subheader("EXP SALES Val / Supervisor")
        sales_by_sup = (
            filtered_df.groupby("Supervisor", as_index=False)["TOT_SALES"]
            .sum()
            .sort_values("TOT_SALES", ascending=True)
            .tail(15)
        )
        fig_sup = px.bar(
            sales_by_sup,
            x="TOT_SALES",
            y="Supervisor",
            orientation="h",
            text=[f"{v/1e6:.1f}M" if v >= 1e6 else f"{v/1e3:.0f}K" for v in sales_by_sup["TOT_SALES"]],
            color_discrete_sequence=["#FFD700"],
        )
        fig_sup.update_traces(textposition="outside", cliponaxis=False)
        fig_sup.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, b=20, l=10, r=50),
            xaxis_title="",
            yaxis_title="",
            xaxis=dict(gridcolor="#30363d"),
            height=500,
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
        display_df = pd.concat([item_agg.head(60), total_row], ignore_index=True)

        st.dataframe(
            display_df.style.format({
                "Sum_of_QTY": "{:,.0f}",
                "Sum_of_TOT_SALES": "{:,.0f}",
            }),
            use_container_width=True,
            height=480,
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
                color_discrete_sequence=["#FFD700"],
            )
            fig_cat.update_traces(textposition="outside", cliponaxis=False)
            fig_cat.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=10, b=20, l=10, r=50),
                xaxis_title="",
                yaxis_title="",
                xaxis=dict(gridcolor="#30363d"),
                height=500,
                showlegend=False,
            )
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("CLASS_NAME column not available")

    # ---------------------------------------------------------
    # Footer
    # ---------------------------------------------------------
    st.markdown("---")
    st.caption(
        f"Records shown: {len(filtered_df):,}  •  "
        f"Total Sales: {total_sales:,.0f} EGP  •  "
        f"Data pipeline matches original Power Query steps"
    )
