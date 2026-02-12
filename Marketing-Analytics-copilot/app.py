# app.py
import streamlit as st
import pandas as pd
import altair as alt
import numpy as np

from data_utils import (
    load_marketing_data,
    load_marketing_data_from_url,
    load_from_json_api,
    fetch_meta_ads_example,
    add_basic_metrics,
    aggregate_by,
    build_text_summary,
    build_ab_test_summary,
)
from ollama_client import ask_llm
from prompts import marketing_insights_prompt, marketing_ab_test_prompt


st.set_page_config(
    page_title="Marketing Analytics Copilot",
    page_icon="📊",
    layout="wide",
)


def _safe_metric_value(value, default=0.0):
    if pd.isna(value) or np.isinf(value):
        return default
    return float(value)


def build_data_quality_table(df_input: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in ["impressions", "clicks", "spend", "conversions", "revenue"]:
        if col in df_input.columns:
            col_data = df_input[col]
            rows.append(
                {
                    "Метрика": col,
                    "Пропуски": int(col_data.isna().sum()),
                    "Нули": int((col_data == 0).sum()) if pd.api.types.is_numeric_dtype(col_data) else "—",
                    "Доля пропусков": f"{(col_data.isna().mean() * 100):.1f}%",
                }
            )

    return pd.DataFrame(rows)


def build_markdown_report(kpi_snapshot: dict, summary_text: str, insights_text: str, ab_text: str) -> str:
    return f"""# Marketing Analytics Report

## KPI Snapshot
- Spend: {kpi_snapshot['spend']:,.2f}
- Revenue: {kpi_snapshot['revenue']:,.2f}
- ROAS: {kpi_snapshot['roas']:.2f}
- CPA: {kpi_snapshot['cpa']:.2f}

## Data Summary
{summary_text}

## LLM Insights
{insights_text or 'Пока не сгенерировано.'}

## A/B Hypotheses
{ab_text or 'Пока не сгенерировано.'}
"""

# === АНИМИРОВАННЫЙ ФОН И СТИЛИ ===
st.markdown(
    """
    <style>
    /* Убираем лишние отступы у Streamlit-контейнера */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    /* Общий фон страницы */
    body {
        background: radial-gradient(circle at top left, #141629 0, #050712 45%, #02030a 100%);
        color: #f5f5f7;
    }

    /* Слой с анимированными пятнами */
    #bg-animation-layer {
        position: fixed;
        inset: 0;
        width: 100vw;
        height: 100vh;
        overflow: hidden;
        z-index: -1; /* за всем контентом */
        pointer-events: none;
    }

    .blob {
        position: absolute;
        width: 420px;
        height: 420px;
        border-radius: 50%;
        filter: blur(120px);
        opacity: 0.75;
        mix-blend-mode: screen;
        transition: transform 0.15s linear;
    }

    #blob1 {
        background: radial-gradient(circle at 30% 30%, #ff7ee5, #7f5dff);
        top: 5%;
        left: 0%;
    }

    #blob2 {
        background: radial-gradient(circle at 30% 30%, #5cf3ff, #3c73ff);
        bottom: -10%;
        right: -5%;
    }

    /* Стеклянные карточки для основных блоков */
    .glass-card {
        background: rgba(10, 11, 25, 0.82);
        border-radius: 18px;
        padding: 1.2rem 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.06);
        box-shadow: 0 18px 45px rgba(0, 0, 0, 0.65);
        backdrop-filter: blur(18px);
    }

    .kpi-card {
        background: rgba(14, 16, 35, 0.98);
        border-radius: 16px;
        padding: 0.9rem 1.1rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
    }

    .kpi-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        color: #9fa3ff;
        margin-bottom: 0.15rem;
    }

    .kpi-value {
        font-size: 1.35rem;
        font-weight: 600;
        color: #f7f7ff;
    }

    .kpi-sub {
        font-size: 0.75rem;
        color: #c4c6ff;
        margin-top: 0.15rem;
    }

    .stTabs [role="tablist"] {
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }

    .stTabs [role="tab"] {
        font-weight: 500;
    }
    </style>

    <!-- Слой с "пятнами" -->
    <div id="bg-animation-layer">
        <div class="blob" id="blob1"></div>
        <div class="blob" id="blob2"></div>
    </div>

    <script>
    (function() {
        const b1 = document.getElementById('blob1');
        const b2 = document.getElementById('blob2');

        function handleMouseMove(e) {
            if (!b1 || !b2) return;

            const w = window.innerWidth || document.documentElement.clientWidth;
            const h = window.innerHeight || document.documentElement.clientHeight;
            const x = e.clientX;
            const y = e.clientY;

            const px = x / w;
            const py = y / h;

            const move1X = (px - 0.5) * 140;
            const move1Y = (py - 0.5) * 120;

            const move2X = (0.5 - px) * 200;
            const move2Y = (0.5 - py) * 160;

            b1.style.transform = `translate3d(${move1X}px, ${move1Y}px, 0)`;
            b2.style.transform = `translate3d(${move2X}px, ${move2Y}px, 0)`;
        }

        window.addEventListener('mousemove', handleMouseMove);
    })();
    </script>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Marketing Analytics Copilot")
st.caption("Загрузи данные по кампаниям → получи метрики, дашборд и инсайты от локальной LLM")

if "insights_answer" not in st.session_state:
    st.session_state["insights_answer"] = ""
if "ab_answer" not in st.session_state:
    st.session_state["ab_answer"] = ""
if "df_raw" not in st.session_state:
    st.session_state["df_raw"] = None
if "data_source_label" not in st.session_state:
    st.session_state["data_source_label"] = ""

# --- Загрузка файла / подключение источника ---
source_type = st.sidebar.radio(
    "Источник данных",
    ["Файл (CSV/XLSX)", "CSV/XLSX по URL", "JSON API", "Meta Ads (example API)"],
)

uploaded_file = None
df_raw = None

if source_type == "Файл (CSV/XLSX)":
    uploaded_file = st.file_uploader(
        "Загрузи CSV или Excel с данными кампаний (impressions, clicks, spend, conversions, revenue, campaign, channel, date, ...)",
        type=["csv", "xlsx"],
    )
    if uploaded_file is not None:
        df_raw = load_marketing_data(uploaded_file)
        st.session_state["df_raw"] = df_raw
        st.session_state["data_source_label"] = f"file:{uploaded_file.name}"

elif source_type == "CSV/XLSX по URL":
    data_url = st.text_input("Ссылка на CSV/XLSX", placeholder="https://.../marketing.csv")
    if st.button("Подтянуть данные по URL") and data_url:
        try:
            df_raw = load_marketing_data_from_url(data_url)
            st.session_state["df_raw"] = df_raw
            st.session_state["data_source_label"] = f"url:{data_url}"
        except Exception as exc:
            st.error(f"Не удалось загрузить данные по URL: {exc}")

elif source_type == "JSON API":
    api_url = st.text_input("API endpoint", placeholder="https://api.example.com/metrics")
    records_field = st.text_input("Поле с массивом записей (если JSON-объект)", value="data")
    if st.button("Подтянуть данные из API") and api_url:
        try:
            df_raw = load_from_json_api(api_url, records_field=records_field)
            st.session_state["df_raw"] = df_raw
            st.session_state["data_source_label"] = f"api:{api_url}"
        except Exception as exc:
            st.error(f"Не удалось загрузить данные из API: {exc}")

elif source_type == "Meta Ads (example API)":
    st.caption("Нужны переменные окружения META_ACCESS_TOKEN и META_AD_ACCOUNT_ID")
    if st.button("Подтянуть из Meta Ads"):
        try:
            df_raw = fetch_meta_ads_example()
            st.session_state["df_raw"] = df_raw
            st.session_state["data_source_label"] = "meta_ads"
        except Exception as exc:
            st.error(f"Ошибка подключения к Meta Ads: {exc}")

if df_raw is None and st.session_state.get("df_raw") is not None:
    df_raw = st.session_state["df_raw"]

if df_raw is None:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.info("Выбери источник и загрузи данные, чтобы начать анализ.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

st.success(f"Источник подключен: {st.session_state.get('data_source_label', 'custom')}")

# --- Чтение и базовые метрики ---
df = add_basic_metrics(df_raw)
rows_before_filters = len(df)

# --- Фильтры в сайдбаре ---
st.sidebar.header("Фильтры")

# Фильтр по дате
if "date" in df.columns and pd.api.types.is_datetime64_any_dtype(df["date"]):
    min_date = df["date"].min()
    max_date = df["date"].max()
    date_range = st.sidebar.date_input(
        "Период",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date(),
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        mask_date = (df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))
        df = df[mask_date]

# Фильтр по каналам
if "channel" in df.columns:
    channels_all = sorted(df["channel"].dropna().unique().tolist())
    selected_channels = st.sidebar.multiselect(
        "Каналы",
        options=channels_all,
        default=channels_all,
    )
    if selected_channels:
        df = df[df["channel"].isin(selected_channels)]

# Фильтр по кампаниям
if "campaign" in df.columns:
    campaigns_all = sorted(df["campaign"].dropna().unique().tolist())
    selected_campaigns = st.sidebar.multiselect(
        "Кампании",
        options=campaigns_all,
        default=campaigns_all[:20] if len(campaigns_all) > 20 else campaigns_all,
    )
    if selected_campaigns:
        df = df[df["campaign"].isin(selected_campaigns)]

rows_after_filters = len(df)

if df.empty:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.warning("После применения фильтров данных не осталось. Ослабь фильтры.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- Агрегация ---
group_cols_campaign = [c for c in ["campaign", "channel"] if c in df.columns]
if group_cols_campaign:
    df_campaigns = aggregate_by(df, group_cols_campaign)
else:
    df_campaigns = aggregate_by(df, [])

if "channel" in df.columns:
    df_channels = aggregate_by(df, ["channel"])
else:
    df_channels = df_campaigns.copy()
    if "channel" not in df_channels.columns:
        df_channels["channel"] = "all"

# Для таймсерии
if "date" in df.columns:
    df_time = (
        df.groupby("date")[["impressions", "clicks", "spend", "conversions", "revenue"]]
        .sum()
        .reset_index()
    )
    df_time = add_basic_metrics(df_time)
else:
    df_time = None

# --- Верхние KPI ---
total_spend = float(df["spend"].sum()) if "spend" in df.columns else 0.0
total_impressions = int(df["impressions"].sum()) if "impressions" in df.columns else 0
total_clicks = int(df["clicks"].sum()) if "clicks" in df.columns else 0
total_conversions = int(df["conversions"].sum()) if "conversions" in df.columns else 0
total_revenue = float(df["revenue"].sum()) if "revenue" in df.columns else 0.0

overall_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
overall_cpc = total_spend / total_clicks if total_clicks > 0 else 0
overall_cpa = total_spend / total_conversions if total_conversions > 0 else 0
overall_roas = total_revenue / total_spend if total_spend > 0 else 0

best_channel = "—"
best_channel_roas = 0.0
worst_channel = "—"
worst_channel_cpa = 0.0
if "channel" in df_channels.columns:
    if "roas" in df_channels.columns and not df_channels["roas"].dropna().empty:
        top_row = df_channels.dropna(subset=["roas"]).sort_values("roas", ascending=False).iloc[0]
        best_channel = str(top_row.get("channel", "—"))
        best_channel_roas = _safe_metric_value(top_row.get("roas", 0.0), 0.0)
    if "cpa" in df_channels.columns and not df_channels["cpa"].dropna().empty:
        bottom_row = df_channels.dropna(subset=["cpa"]).sort_values("cpa", ascending=False).iloc[0]
        worst_channel = str(bottom_row.get("channel", "—"))
        worst_channel_cpa = _safe_metric_value(bottom_row.get("cpa", 0.0), 0.0)

period_spend_delta = 0.0
period_revenue_delta = 0.0
if df_time is not None and len(df_time) >= 2:
    half = len(df_time) // 2
    first_half = df_time.iloc[:half] if half > 0 else df_time.iloc[:1]
    second_half = df_time.iloc[half:] if half > 0 else df_time.iloc[-1:]

    first_spend = first_half["spend"].sum() if "spend" in first_half.columns else 0.0
    second_spend = second_half["spend"].sum() if "spend" in second_half.columns else 0.0
    if first_spend > 0:
        period_spend_delta = (second_spend - first_spend) / first_spend

    if "revenue" in df_time.columns:
        first_rev = first_half["revenue"].sum()
        second_rev = second_half["revenue"].sum()
        if first_rev > 0:
            period_revenue_delta = (second_rev - first_rev) / first_rev

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">Расход (Spend)</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kpi-value">{total_spend:,.0f}</div>', unsafe_allow_html=True)
    st.markdown('<div class="kpi-sub">Суммарные рекламные затраты</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with kpi_col2:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">Доход (Revenue)</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kpi-value">{total_revenue:,.0f}</div>', unsafe_allow_html=True)
    st.markdown('<div class="kpi-sub">Суммарная выручка по данным</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with kpi_col3:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">ROAS</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kpi-value">{overall_roas:.2f}</div>', unsafe_allow_html=True)
    st.markdown('<div class="kpi-sub">Доход / Расход</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with kpi_col4:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">CPA</div>', unsafe_allow_html=True)
    cpa_str = f"{overall_cpa:.2f}" if overall_cpa > 0 else "—"
    st.markdown(f'<div class="kpi-value">{cpa_str}</div>', unsafe_allow_html=True)
    st.markdown('<div class="kpi-sub">Расход за конверсию</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="glass-card" style="margin-top: 1rem;">', unsafe_allow_html=True)
st.markdown("### Executive Summary")
exec_col1, exec_col2, exec_col3 = st.columns(3)
with exec_col1:
    st.metric("Лучший канал по ROAS", best_channel, f"ROAS {best_channel_roas:.2f}")
with exec_col2:
    st.metric("Канал с самым высоким CPA", worst_channel, f"CPA {worst_channel_cpa:.2f}")
with exec_col3:
    retained_pct = (rows_after_filters / rows_before_filters * 100) if rows_before_filters else 0
    st.metric("Rows retained после фильтров", f"{rows_after_filters:,}", f"{retained_pct:.1f}% от исходных")
st.caption(f"Δ Spend (2-я половина vs 1-я): {period_spend_delta:+.1%} | Δ Revenue: {period_revenue_delta:+.1%}")
st.markdown('</div>', unsafe_allow_html=True)

# --- Вкладки в стеклянной карточке ---
st.markdown('<div class="glass-card" style="margin-top: 1.2rem;">', unsafe_allow_html=True)
tab_data, tab_dashboard, tab_insights, tab_abtests = st.tabs(
    ["📄 Данные", "📊 Дашборд", "🧠 Инсайты от ИИ", "🧪 A/B-тесты"]
)


# =============== TAB 1: ДАННЫЕ ===================
with tab_data:
    st.subheader("Сырые данные (после фильтров)")
    st.dataframe(df.head(200))

    st.subheader("Качество данных")
    quality_df = build_data_quality_table(df_raw)
    if not quality_df.empty:
        st.dataframe(quality_df, use_container_width=True)
    if "date" in df_raw.columns and pd.api.types.is_datetime64_any_dtype(df_raw["date"]):
        st.caption(f"Диапазон дат: {df_raw['date'].min().date()} → {df_raw['date'].max().date()}")

    st.subheader("Агрегация по кампаниям")
    st.dataframe(df_campaigns)

    st.subheader("Агрегация по каналам")
    st.dataframe(df_channels)

# =============== TAB 2: ДАШБОРД ===================
with tab_dashboard:
    st.subheader("Ключевые метрики по каналам")

    # ROAS по каналам
    if "channel" in df_channels.columns and "roas" in df_channels.columns:
        chart_roas = (
            alt.Chart(df_channels)
            .mark_bar()
            .encode(
                x=alt.X("channel:N", title="Канал"),
                y=alt.Y("roas:Q", title="ROAS"),
                tooltip=["channel", "roas", "spend", "cpa"],
            )
        )
        st.altair_chart(chart_roas, use_container_width=True)

    # CPA по каналам
    if "channel" in df_channels.columns and "cpa" in df_channels.columns:
        chart_cpa = (
            alt.Chart(df_channels)
            .mark_bar()
            .encode(
                x=alt.X("channel:N", title="Канал"),
                y=alt.Y("cpa:Q", title="CPA"),
                tooltip=["channel", "cpa", "spend", "roas"],
            )
        )
        st.altair_chart(chart_cpa, use_container_width=True)

    st.markdown("---")
    st.subheader("Динамика по времени")

    if df_time is not None and not df_time.empty:
        # Расход
        chart_spend = (
            alt.Chart(df_time)
            .mark_line()
            .encode(
                x=alt.X("date:T", title="Дата"),
                y=alt.Y("spend:Q", title="Расход"),
                tooltip=["date", "spend"],
            )
        )
        st.altair_chart(chart_spend, use_container_width=True)

        # Доход
        if "revenue" in df_time.columns:
            chart_rev = (
                alt.Chart(df_time)
                .mark_line()
                .encode(
                    x=alt.X("date:T", title="Дата"),
                    y=alt.Y("revenue:Q", title="Доход"),
                    tooltip=["date", "revenue"],
                )
            )
            st.altair_chart(chart_rev, use_container_width=True)

    st.markdown("---")
    st.subheader("Hero-chart: ROAS vs CPA по кампаниям")

    if {"roas", "cpa"}.issubset(df_campaigns.columns):
        scatter = (
            alt.Chart(df_campaigns)
            .mark_circle(size=60)
            .encode(
                x=alt.X("cpa:Q", title="CPA"),
                y=alt.Y("roas:Q", title="ROAS"),
                color=alt.Color("channel:N", title="Канал") if "channel" in df_campaigns.columns else alt.value("steelblue"),
                size=alt.Size("spend:Q", title="Spend", legend=None) if "spend" in df_campaigns.columns else alt.value(60),
                tooltip=[c for c in ["campaign", "channel", "cpa", "roas", "spend"] if c in df_campaigns.columns],
            )
        )
        st.altair_chart(scatter, use_container_width=True)
    else:
        st.info("Для hero-chart нужны ROAS и CPA (они считаются из revenue/spend/conversions).")

# =============== TAB 3: ИНСАЙТЫ ================
with tab_insights:
    st.subheader("Инсайты и рекомендации от локальной LLM")

    st.write(
        "Модель получит агрегированные данные по кампаниям и каналам "
        "и сформирует текстовый отчёт: общая картина, ключевые инсайты и рекомендации."
    )

    if st.button("Сгенерировать инсайты"):
        with st.spinner("Генерируем инсайты с помощью локальной модели..."):
            summary_text = build_text_summary(df_campaigns, df_channels)
            prompt = marketing_insights_prompt(summary_text)
            try:
                answer = ask_llm(prompt)
                st.session_state["insights_answer"] = answer
            except RuntimeError as exc:
                st.error(str(exc))
                st.info(
                    "Если приложение запущено в Streamlit Cloud, укажи внешний LLM endpoint через "
                    "переменную окружения OLLAMA_URL (и при необходимости OLLAMA_MODEL)."
                )

        if st.session_state.get("insights_answer"):
            st.markdown("### 🧠 Ответ модели")
            st.markdown(st.session_state["insights_answer"])



# =============== TAB 4: A/B-ТЕСТЫ ================
with tab_abtests:
    st.subheader("Генерация A/B-гипотез")

    st.write(
        "Здесь локальная модель предложит конкретные A/B-тесты на основе текущих данных: "
        "какие кампании/каналы/креативы стоит тестировать и что именно менять."
    )

    # Немного показать пользователю, что анализируем
    with st.expander("Посмотреть сводку, на основе которой строятся гипотезы"):
        st.write("ТОП/антитоп кампаний и сводка по каналам (см. также вкладку 'Данные').")
        st.dataframe(df_campaigns.head(20))
        st.dataframe(df_channels)

    if st.button("Сгенерировать A/B-гипотезы"):
        with st.spinner("Генерируем A/B-гипотезы с помощью локальной модели..."):
            ab_summary = build_ab_test_summary(df_campaigns, df_channels)
            ab_prompt = marketing_ab_test_prompt(ab_summary)
            try:
                ab_answer = ask_llm(ab_prompt)
                st.session_state["ab_answer"] = ab_answer
            except RuntimeError as exc:
                st.error(str(exc))
                st.info(
                    "Для Streamlit Cloud используй внешний LLM endpoint и задай OLLAMA_URL/OLLAMA_MODEL "
                    "в Secrets приложения."
                )

        if st.session_state.get("ab_answer"):
            st.markdown("### 🧪 Предложенные A/B-гипотезы")
            st.markdown(st.session_state["ab_answer"])


report_snapshot = {
    "spend": total_spend,
    "revenue": total_revenue,
    "roas": overall_roas,
    "cpa": overall_cpa,
}
report_summary = build_text_summary(df_campaigns, df_channels)
report_md = build_markdown_report(
    report_snapshot,
    report_summary,
    st.session_state.get("insights_answer", ""),
    st.session_state.get("ab_answer", ""),
)
st.download_button(
    "⬇️ Скачать report.md",
    data=report_md.encode("utf-8"),
    file_name="marketing_analytics_report.md",
    mime="text/markdown",
)

st.markdown('</div>', unsafe_allow_html=True)  # закрываем glass-card вокруг табов
   
