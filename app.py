import io
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم الظاهري (Dark/Gold Custom CSS)
# ---------------------------------------------------------
st.set_page_config(
    page_title="EXPIRE SITUATION",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded",
)

# تطبيق تنسيقات CSS مطابقة لتصميمك الأصلي
st.markdown(
    """
    <style>
    /* خلفية الصفحة الرئيسية والجوانب */
    .stApp {
        background-color: #080B11;
        color: #FFD700;
    }
    [data-testid="stSidebar"] {
        background-color: #0D111A;
        border-right: 1px solid #FFD700;
    }
    
    /* تصميم البطاقات والعناوين */
    .kpi-card {
        background-color: #0D111A;
        border: 2px solid #FFD700;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 0 10px rgba(255, 215, 0, 0.2);
    }
    .kpi-title {
        color: #FFFFFF;
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .kpi-value {
        color: #FFD700;
        font-size: 38px;
        font-weight: bold;
    }
    
    /* إخفاء الهيدر الافتراضي لـ Streamlit */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* حدود العلب والحاويات */
    div[data-element-container] {
        color: #FFFFFF;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# 2. نظام التحقق من كلمة السر
# ---------------------------------------------------------
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.markdown(
            """
            <div style="display: flex; justify-content: center; align-items: center; height: 70vh;">
                <div style="background-color: #0D111A; border: 2px solid #FFD700; padding: 40px; border-radius: 15px; text-align: center; width: 400px;">
                    <h2 style="color: #FFD700; margin-bottom: 20px;">EXPIRE SITUATION</h2>
                    <p style="color: #FFFFFF;">🔒 يرجى إدخال كلمة السر للدخول</p>
            """,
            unsafe_allow_html=True,
        )
        password = st.text_input("", type="password", placeholder="Password")
        if st.button("LOGIN", use_container_width=True):
            if password == "123456":  # كلمة السر الموحدة
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("كلمة السر غير صحيحة!")
        st.markdown("</div></div>", unsafe_allow_html=True)
        return False
    return True


if check_password():
    # ---------------------------------------------------------
    # 3. جلب وتحويل البيانات بنفس منطق Power Query
    # ---------------------------------------------------------
    @st.cache_data(ttl=3600)
    def load_data():
        # أ. Parquet File
        parquet_id = "1xlmf0jNJ2WC27Rd88EiRLlWVsEpNELC5"
        parquet_url = (
            f"https://drive.google.com/uc?export=download&id={parquet_id}"
        )
        res = requests.get(parquet_url)
        df = pd.read_parquet(io.BytesIO(res.content))

        # حذف الأعمدة المحددة في Power Query
        remove_cols = [
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
        df = df.drop(columns=[c for c in remove_cols if c in df.columns])
        df.columns = df.columns.str.strip()

        # تحويل STORE لرقم صحيح
        df["STORE"] = pd.to_numeric(df["STORE"], errors="coerce").astype(
            "Int64"
        )

        # ب. Table1 (Supervision Data)
        t1_id = "1kY6jzVoHCYhm_0a9uxd9sjtllNnjfFz7"
        t1_url = (
            f"https://docs.google.com/spreadsheets/d/{t1_id}/export?format=xlsx"
        )
        t1 = pd.read_excel(t1_url, sheet_name=0)
        t1.columns = t1.columns.astype(str).str.strip()

        store_col1 = next(
            (
                c
                for c in t1.columns
                if c.lower() in ["store code", "store_code", "store"]
            ),
            t1.columns[0],
        )
        sup_col = next(
            (c for c in t1.columns if "supervisor" in c.lower()), "Supervisor"
        )

        t1[store_col1] = pd.to_numeric(
            t1[store_col1], errors="coerce"
        ).astype("Int64")
        df = df.merge(
            t1[[store_col1, sup_col]],
            left_on="STORE",
            right_on=store_col1,
            how="left",
        )

        # ج. Table2 (Branches Data)
        t2_id = "1i_kxf7J83EDYgr2SzkYlLKjzD9uM4Gie"
        t2_url = (
            f"https://docs.google.com/spreadsheets/d/{t2_id}/export?format=xlsx"
        )
        t2 = pd.read_excel(t2_url, sheet_name=0)
        t2.columns = t2.columns.astype(str).str.strip()

        store_col2 = next(
            (
                c
                for c in t2.columns
                if c.lower() in ["store", "store code", "store_code"]
            ),
            t2.columns[0],
        )
        branch_col = next(
            (c for c in t2.columns if c.lower() in ["name", "branch"]),
            t2.columns[1],
        )

        t2[store_col2] = pd.to_numeric(
            t2[store_col2], errors="coerce"
        ).astype("Int64")
        df = df.merge(
            t2[[store_col2, branch_col]],
            left_on="STORE",
            right_on=store_col2,
            how="left",
            suffixes=("", "_t2"),
        )

        # إعادة تسمية ومُعالجة النواقص
        df.rename(
            columns={
                branch_col: "BRANCH",
                sup_col: "Supervisor",
                "ITEM": "ITEM_CODE",
                "STORE": "STORE_CODE",
            },
            inplace=True,
        )

        df["Supervisor"] = df["Supervisor"].fillna("NON_SELLING_STORES")
        df["BRANCH"] = df["BRANCH"].fillna("NON_SELLING_STORES")

        # معالجة تاريخ الصلاحية EXPIRE_DATE
        def fix_expiry(val):
            if pd.isna(val) or not isinstance(val, str) or len(str(val)) < 6:
                return val
            s = str(val)
            return s[:6] + "20" + s[6:]

        df["EXPIRE_DATE"] = df["EXPIRY_DATE"].astype(str).apply(fix_expiry)
        df["EXPIRE_DATE"] = pd.to_datetime(
            df["EXPIRE_DATE"], errors="coerce", dayfirst=True
        )

        # الأرقام والـ Year-Month
        for c in ["TOT_SALES", "SALES_PRICE", "QTY"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        df["Year-Month"] = df["EXPIRE_DATE"].dt.strftime("%Y-%m")

        # التأكد من وجود عمود الفئة CLASS_NAME
        if "CLASS_NAME" not in df.columns and "CLASS" in df.columns:
            df["CLASS_NAME"] = df["CLASS"]
        elif "CLASS_NAME" not in df.columns:
            df["CLASS_NAME"] = "OTHER"

        return df

    with st.spinner("جاري استدعاء البيانات وتجهيز العرض..."):
        df = load_data()

    # ---------------------------------------------------------
    # 4. بناء الفلاتر والشريط الجانبي (Year-Month Filter)
    # ---------------------------------------------------------
    st.sidebar.markdown(
        "<h3 style='color:#FFD700;'>Year-Month</h3>", unsafe_allow_html=True
    )

    available_months = sorted(
        [
            m
            for m in df["Year-Month"].dropna().unique()
            if m not in ["NaT", "None"]
        ]
    )

    # وضع أشهر محددة افتراضياً مثل الداشبورد الأصلية إن وجدت
    default_selected = (
        available_months[-6:]
        if len(available_months) >= 6
        else available_months
    )

    selected_months = st.sidebar.multiselect(
        "Select Months:",
        options=available_months,
        default=default_selected,
    )

    if selected_months:
        fdf = df[df["Year-Month"].isin(selected_months)]
    else:
        fdf = df

    # ---------------------------------------------------------
    # 5. الترويسة الرئيسية والـ KPI
    # ---------------------------------------------------------
    st.markdown(
        "<h1 style='text-align: center; color: #FFD700; font-family: sans-serif; font-weight: bold; letter-spacing: 2px;'>EXPIRE SITUATION</h1>",
        unsafe_allow_html=True,
    )

    # حساب إجمالي المبيعات بالصيغة المباشرة (مثل 36M)
    total_sales_val = fdf["TOT_SALES"].sum()
    sales_display = f"{total_sales_val/1e6:.0f}M"

    top_l, top_m, top_r = st.columns([1, 2.5, 1.5])

    with top_l:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Total Sales</div>
                <div class="kpi-value">{sales_display}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---------------------------------------------------------
    # 6. الرسم البياني الأوسط (TOTAL SALES VALUE BY MONTH)
    # ---------------------------------------------------------
    with top_m:
        m_sales = fdf.groupby("Year-Month")["TOT_SALES"].sum().reset_index()
        fig_bar = px.bar(
            m_sales,
            x="Year-Month",
            y="TOT_SALES",
            title="<b>TOTAL SALES VALUE</b>",
            text_auto=".2s",
            color_discrete_sequence=["#FFD700"],
        )
        fig_bar.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0D111A",
            plot_bgcolor="#0D111A",
            font=dict(color="#FFD700"),
            title_font=dict(size=16, color="#FFD700"),
            margin=dict(l=20, r=20, t=40, b=20),
            height=280,
        )
        fig_bar.update_traces(
            textfont_color="#FFFFFF", textposition="outside"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ---------------------------------------------------------
    # 7. الرسم الدائري (Pie Chart / Branch Share)
    # ---------------------------------------------------------
    with top_r:
        b_sales = (
            fdf.groupby("BRANCH")["TOT_SALES"]
            .sum()
            .reset_index()
            .sort_values("TOT_SALES", ascending=False)
        )
        # أخذ أكبر الفروع وتجميع الباقي
        fig_pie = px.pie(
            b_sales.head(7),
            values="TOT_SALES",
            names="BRANCH",
            title="<b>BRANCHES SHARE</b>",
            color_discrete_sequence=px.colors.sequential.YlOrBr_r,
        )
        fig_pie.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0D111A",
            plot_bgcolor="#0D111A",
            font=dict(color="#FFD700"),
            title_font=dict(size=16, color="#FFD700"),
            margin=dict(l=10, r=10, t=40, b=10),
            height=280,
        )
        fig_pie.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 8. الصف السفلي (المشرفون + جدول المنتجات + الفئات)
    # ---------------------------------------------------------
    bot_l, bot_m, bot_r = st.columns([1.2, 2, 1.2])

    # أ. EXP SALES Val / Supervisor
    with bot_l:
        sup_sales = (
            fdf.groupby("Supervisor")["TOT_SALES"]
            .sum()
            .reset_index()
            .sort_values("TOT_SALES", ascending=True)
            .tail(15)
        )
        fig_sup = px.bar(
            sup_sales,
            x="TOT_SALES",
            y="Supervisor",
            orientation="h",
            title="<b>EXP SALES Val / Supervisor</b>",
            text_auto=".2s",
            color_discrete_sequence=["#FFD700"],
        )
        fig_sup.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0D111A",
            plot_bgcolor="#0D111A",
            font=dict(color="#FFD700"),
            title_font=dict(size=15, color="#FFD700"),
            margin=dict(l=10, r=10, t=40, b=10),
            height=450,
        )
        st.plotly_chart(fig_sup, use_container_width=True)

    # ب. الجدول المركزي التفصيلي (Item_name | Year-Month | Sum of QTY | Sum of TOT_SALES)
    with bot_m:
        st.markdown(
            "<h4 style='color:#FFD700; text-align:center;'>Detailed Expire Items</h4>",
            unsafe_allow_html=True,
        )

        item_table = (
            fdf.groupby(["Item_name", "Year-Month"])[["QTY", "TOT_SALES"]]
            .sum()
            .reset_index()
            .sort_values("TOT_SALES", ascending=False)
        )

        item_table.rename(
            columns={
                "Item_name": "Item_name",
                "Year-Month": "Year-Month",
                "QTY": "Sum of QTY",
                "TOT_SALES": "Sum of TOT_SALES",
            },
            inplace=True,
        )

        # تنسيق المبالغ المالية
        item_table["Sum of TOT_SALES"] = item_table[
            "Sum of TOT_SALES"
        ].apply(lambda x: f"{x:,.0f}")
        item_table["Sum of QTY"] = item_table["Sum of QTY"].apply(
            lambda x: f"{x:,.0f}"
        )

        st.dataframe(
            item_table,
            use_container_width=True,
            height=400,
            hide_index=True,
        )

    # ج. EXP SALES Val / Category
    with bot_r:
        cat_sales = (
            fdf.groupby("CLASS_NAME")["TOT_SALES"]
            .sum()
            .reset_index()
            .sort_values("TOT_SALES", ascending=True)
            .tail(12)
        )
        fig_cat = px.bar(
            cat_sales,
            x="TOT_SALES",
            y="CLASS_NAME",
            orientation="h",
            title="<b>EXP SALES Val / Category</b>",
            text_auto=".2s",
            color_discrete_sequence=["#FFD700"],
        )
        fig_cat.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0D111A",
            plot_bgcolor="#0D111A",
            font=dict(color="#FFD700"),
            title_font=dict(size=15, color="#FFD700"),
            margin=dict(l=10, r=10, t=40, b=10),
            height=450,
        )
        st.plotly_chart(fig_cat, use_container_width=True)
