import pandas as pd
import plotly.express as px
import streamlit as st

# 1. إعداد كلمة السر
st.set_page_config(page_title="Expire Situation", layout="wide")


def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        password = st.text_input("أدخل كلمة السر لعرض الداشبورد:", type="password")
        if st.button("دخول"):
            if password == "123456":  # اكتب الباسورد العام هنا
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("كلمة السر غير صحيحة")
        return False
    return True


if check_password():
    # 2. تحميل البيانات وتطبيق التحويلات
    df = pd.read_parquet("Expire_Data_Raw.parquet")

    # تصفية وتجهيز البيانات
    st.title("EXPIRE SITUATION")

    # KPI Top Metric
    total_sales = df["TOT_SALES"].sum()
    st.metric(label="Total Sales", value=f"{total_sales:,.0f}")

    col1, col2 = st.columns(2)

    with col1:
        # رسم بياني للمبيعات حسب المفهوم
        fig_bar = px.bar(
            df.groupby("Year-Month")["TOT_SALES"].sum().reset_index(),
            x="Year-Month",
            y="TOT_SALES",
            title="TOTAL SALES VALUE",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        # رسم دائري
        fig_pie = px.pie(
            df, values="TOT_SALES", names="BRANCH", title="EXP SALES BY BRANCH"
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # الجدول التفصيلي
    st.dataframe(df[["Item_name", "Year-Month", "QTY", "TOT_SALES"]])
