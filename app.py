import io
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ---------------------------------------------------------
# 1. إعدادات الصفحة وكلمة السر
# ---------------------------------------------------------
st.set_page_config(
    page_title="EXPIRE SITUATION DASHBOARD", page_icon="📊", layout="wide"
)


def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.markdown(
            "<h2 style='text-align: center;'>🔒 يرجى إدخال كلمة السر للدخول للداشبورد</h2>",
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            password = st.text_input("كلمة السر / Password:", type="password")
            if st.button("تسجيل الدخول / Login", use_container_width=True):
                if password == "123456":  # <--- يمكنك تغيير كلمة السر من هنا
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("كلمة السر غير صحيحة!")
        return False
    return True


if check_password():
    # ---------------------------------------------------------
    # 2. تحميل البيانات من الروابط مباشرة وتطبيق Power Query Logic
    # ---------------------------------------------------------
    @st.cache_data(ttl=3600)
    def load_and_transform_data():
        # --- أ. تحميل وقراءة ملف Parquet من Google Drive ---
        parquet_file_id = "1xlmf0jNJ2WC27Rd88EiRLlWVsEpNELC5"
        parquet_url = (
            f"https://drive.google.com/uc?export=download&id={parquet_file_id}"
        )

        response = requests.get(parquet_url)
        df_raw = pd.read_parquet(io.BytesIO(response.content))

        # 1. Removed Columns (تطبيق حذف الأعمدة مثل Power Query)
        cols_to_remove = [
            "CONFG_SER",
            "LOT_NO",
            "SUPP_CODE",
            "MANF_CODE",
            "TOTAL.COSTS",
            "MANF_NAME",
            "ST_NAME",
            "INV_NO",
            "ITEM_COST",
            "TOTAL_PROFIT",
        ]
        df = df_raw.drop(
            columns=[c for c in cols_to_remove if c in df_raw.columns]
        )

        # 2. Changed Type STORE to Int
        df["STORE"] = pd.to_numeric(df["STORE"], errors="coerce").astype(
            "Int64"
        )

        # --- ب. قراءة شيت Supervision Data (Table1) ---
        table1_sheet_id = "1kY6jzVoHCYhm_0a9uxd9sjtllNnjfFz7"
        table1_url = f"https://docs.google.com/spreadsheets/d/{table1_sheet_id}/export?format=xlsx"
        table1 = pd.read_excel(table1_url, sheet_name="Table1")
        table1["Store Code"] = pd.to_numeric(
            table1["Store Code"], errors="coerce"
        ).astype("Int64")

        # Merged Queries & Expanded Table1
        df = df.merge(
            table1[["Store Code", "Supervisor"]],
            left_on="STORE",
            right_on="Store Code",
            how="left",
        )
        df.drop(columns=["Store Code"], inplace=True, errors="ignore")

        # --- ج. قراءة شيت Branches Data (Table2) ---
        table2_sheet_id = "1i_kxf7J83EDYgr2SzkYlLKjzD9uM4Gie"
        table2_url = f"https://docs.google.com/spreadsheets/d/{table2_sheet_id}/export?format=xlsx"
        table2 = pd.read_excel(table2_url, sheet_name="Table2")
        table2["STORE"] = pd.to_numeric(
            table2["STORE"], errors="coerce"
        ).astype("Int64")

        # Merged Queries1 & Expanded Table2
        df = df.merge(
            table2[["STORE", "NAME"]], on="STORE", how="left", suffixes=("", "_t2")
        )

        # Renamed Columns
        df.rename(
            columns={
                "NAME": "BRANCH",
                "ITEM": "ITEM_CODE",
                "STORE": "STORE_CODE",
            },
            inplace=True,
        )

        # Replaced Value null -> "NON_SELLING_STORES"
        df["Supervisor"] = df["Supervisor"].fillna("NON_SELLING_STORES")
        df["BRANCH"] = df["BRANCH"].fillna("NON_SELLING_STORES")

        # Added Custom Column & Convert to Date
        # المماثل لخطوة: Text.Combine({Text.Start([EXPIRY_DATE], 6), "20", Text.Middle([EXPIRY_DATE], 6)})
        def format_expiry(val):
            if pd.isna(val) or not isinstance(val, str) or len(val) < 6:
                return val
            return val[:6] + "20" + val[6:]

        df["EXPIRE_DATE"] = df["EXPIRY_DATE"].astype(str).apply(format_expiry)
        df["EXPIRE_DATE"] = pd.to_datetime(
            df["EXPIRE_DATE"], errors="coerce", dayfirst=True
        )

        # Changed Type numeric
        for col in ["TOT_SALES", "SALES_PRICE", "QTY"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # إضافة عمود Year-Month للفلترة
        df["Year-Month"] = df["EXPIRE_DATE"].dt.strftime("%Y-%m")

        return df

    with st.spinner("جاري تحميل البيانات وتحليلها..."):
        df = load_and_transform_data()

    # ---------------------------------------------------------
    # 3. تصميم الداشبورد (Dashboard Visuals)
    # ---------------------------------------------------------
    st.markdown(
        "<h1 style='text-align: center; color: #FFD700;'>EXPIRE SITUATION</h1>",
        unsafe_allow_html=True,
    )

    # الشريط الجانبي للفلاتر (Sidebar Filters)
    st.sidebar.header("Filter Options")
    available_months = sorted(
        [m for m in df["Year-Month"].dropna().unique() if m != "NaT"]
    )

    selected_months = st.sidebar.multiselect(
        "Select Year-Month:", options=available_months, default=available_months
    )

    if selected_months:
        filtered_df = df[df["Year-Month"].isin(selected_months)]
    else:
        filtered_df = df

    # الصف الأول: KPI Cards
    total_sales = filtered_df["TOT_SALES"].sum()
    total_qty = filtered_df["QTY"].sum()

    kpi1, kpi2 = st.columns(2)
    kpi1.metric("Total Sales", f"{total_sales:,.0f} EGP")
    kpi2.metric("Total Quantity", f"{total_qty:,.0f}")

    st.markdown("---")

    # الصف الثاني: الرسومات البيانية
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("TOTAL SALES VALUE BY MONTH")
        sales_by_month = (
            filtered_df.groupby("Year-Month")["TOT_SALES"].sum().reset_index()
        )
        fig_bar = px.bar(
            sales_by_month,
            x="Year-Month",
            y="TOT_SALES",
            text_auto=".2s",
            color_discrete_sequence=["#FFD700"],
        )
        fig_bar.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        st.subheader("EXP SALES Val / BRANCH")
        sales_by_branch = (
            filtered_df.groupby("BRANCH")["TOT_SALES"].sum().reset_index()
        )
        fig_pie = px.pie(
            sales_by_branch,
            values="TOT_SALES",
            names="BRANCH",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Gold,
        )
        fig_pie.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # الصف الثالث: المشرفين والجدول التفصيلي
    col_sup, col_table = st.columns([1, 1])

    with col_sup:
        st.subheader("EXP SALES Val / Supervisor")
        sales_by_sup = (
            filtered_df.groupby("Supervisor")["TOT_SALES"]
            .sum()
            .reset_index()
            .sort_values(by="TOT_SALES", ascending=True)
        )
        fig_sup = px.bar(
            sales_by_sup,
            x="TOT_SALES",
            y="Supervisor",
            orientation="h",
            text_auto=".2s",
            color_discrete_sequence=["#FFD700"],
        )
        fig_sup.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_sup, use_container_width=True)

    with col_table:
        st.subheader("Item Expiry Table")
        display_cols = [
            col
            for col in [
                "Item_name",
                "Year-Month",
                "QTY",
                "TOT_SALES",
                "Supervisor",
                "BRANCH",
            ]
            if col in filtered_df.columns
        ]
        st.dataframe(
            filtered_df[display_cols].head(100), use_container_width=True
        )
