import io
import os

import pandas as pd
import requests


def normalize_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["date", "datetime", "timestamp"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_marketing_data(file) -> pd.DataFrame:
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    return normalize_date_columns(df)


def load_marketing_data_from_url(url: str, timeout: int = 20) -> pd.DataFrame:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    raw = response.content
    if url.lower().endswith(".xlsx") or "spreadsheet" in content_type:
        df = pd.read_excel(io.BytesIO(raw))
    else:
        df = pd.read_csv(io.BytesIO(raw))

    return normalize_date_columns(df)


def load_from_json_api(endpoint: str, records_field: str = "data", timeout: int = 20) -> pd.DataFrame:
    response = requests.get(endpoint, timeout=timeout)
    response.raise_for_status()
    payload = response.json()

    if isinstance(payload, list):
        df = pd.DataFrame(payload)
    elif isinstance(payload, dict):
        records = payload.get(records_field, payload)
        if isinstance(records, list):
            df = pd.DataFrame(records)
        else:
            df = pd.DataFrame([records])
    else:
        raise ValueError("Unsupported JSON payload format")

    return normalize_date_columns(df)


def fetch_meta_ads_example() -> pd.DataFrame:
    token = os.getenv("META_ACCESS_TOKEN")
    ad_account_id = os.getenv("META_AD_ACCOUNT_ID")
    if not token or not ad_account_id:
        raise ValueError("Set META_ACCESS_TOKEN and META_AD_ACCOUNT_ID environment variables")

    endpoint = f"https://graph.facebook.com/v20.0/act_{ad_account_id}/insights"
    params = {
        "access_token": token,
        "fields": "date_start,campaign_name,impressions,clicks,spend,actions",
        "level": "campaign",
        "time_increment": 1,
        "limit": 200,
    }
    response = requests.get(endpoint, params=params, timeout=25)
    response.raise_for_status()
    rows = response.json().get("data", [])

    normalized = []
    for row in rows:
        conversions = 0
        for action in row.get("actions", []):
            if action.get("action_type") in {"purchase", "offsite_conversion.purchase"}:
                conversions += float(action.get("value", 0))

        normalized.append(
            {
                "date": row.get("date_start"),
                "campaign": row.get("campaign_name"),
                "channel": "meta_ads",
                "impressions": float(row.get("impressions", 0)),
                "clicks": float(row.get("clicks", 0)),
                "spend": float(row.get("spend", 0)),
                "conversions": conversions,
            }
        )

    return normalize_date_columns(pd.DataFrame(normalized))


def add_basic_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "impressions" in df.columns and "clicks" in df.columns:
        df["ctr"] = df["clicks"] / df["impressions"]

    if "spend" in df.columns and "clicks" in df.columns:
        df["cpc"] = df["spend"] / df["clicks"].replace(0, pd.NA)

    if "spend" in df.columns and "conversions" in df.columns:
        df["cpa"] = df["spend"] / df["conversions"].replace(0, pd.NA)

    if "revenue" in df.columns and "spend" in df.columns:
        df["roas"] = df["revenue"] / df["spend"].replace(0, pd.NA)

    return df


def aggregate_by(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    metric_cols = [
        c for c in ["impressions", "clicks", "spend", "conversions", "revenue"]
        if c in df.columns
    ]
    agg_dict = {col: "sum" for col in metric_cols}

    res = df.groupby(group_cols).agg(agg_dict).reset_index()
    res = add_basic_metrics(res)
    return res


def build_text_summary(df_campaigns: pd.DataFrame, df_channels: pd.DataFrame) -> str:
    lines = []
    lines.append("Краткое описание данных по маркетинговым кампаниям.\n")

    lines.append("Агрегация по кампаниям (топ 5 по расходам):")
    if "spend" in df_campaigns.columns:
        top_campaigns = df_campaigns.sort_values("spend", ascending=False).head(5)
    else:
        top_campaigns = df_campaigns.head(5)

    for _, row in top_campaigns.iterrows():
        lines.append(
            f"- Кампания: {row.get('campaign','?')}, канал: {row.get('channel','?')}, "
            f"расход: {row.get('spend',0):.2f}, ROAS: {row.get('roas',0):.2f}, "
            f"CPA: {row.get('cpa',0):.2f}"
        )

    lines.append("\nАгрегация по каналам (топ 5):")
    df_channels_sorted = (
        df_channels.sort_values("spend", ascending=False).head(5)
        if "spend" in df_channels.columns
        else df_channels.head(5)
    )

    for _, row in df_channels_sorted.iterrows():
        lines.append(
            f"- Канал: {row.get('channel','?')}, расход: {row.get('spend',0):.2f}, "
            f"ROAS: {row.get('roas',0):.2f}, CPA: {row.get('cpa',0):.2f}"
        )

    summary = "\n".join(lines)
    return summary[:4000]


def build_ab_test_summary(df_campaigns: pd.DataFrame, df_channels: pd.DataFrame) -> str:
    lines = []
    lines.append("Данные для генерации A/B-гипотез.\n")

    if "roas" in df_campaigns.columns and "spend" in df_campaigns.columns:
        df_valid = df_campaigns.dropna(subset=["roas"])
        if not df_valid.empty:
            lines.append("Кампании с высоким ROAS (топ 5):")
            for _, row in df_valid.sort_values("roas", ascending=False).head(5).iterrows():
                lines.append(
                    f"- HIGH ROAS | {row.get('campaign','?')} | канал: {row.get('channel','?')} | "
                    f"ROAS: {row.get('roas',0):.2f} | CPA: {row.get('cpa',0):.2f}"
                )

            lines.append("\nКампании с низким ROAS (антитоп 5):")
            for _, row in df_valid.sort_values("roas", ascending=True).head(5).iterrows():
                lines.append(
                    f"- LOW ROAS | {row.get('campaign','?')} | канал: {row.get('channel','?')} | "
                    f"ROAS: {row.get('roas',0):.2f} | CPA: {row.get('cpa',0):.2f}"
                )

    if "ctr" in df_campaigns.columns:
        df_ctr = df_campaigns.dropna(subset=["ctr"])
        if not df_ctr.empty:
            lines.append("\nКампании с низким CTR (возможные проблемы с креативами):")
            for _, row in df_ctr.sort_values("ctr", ascending=True).head(5).iterrows():
                lines.append(
                    f"- LOW CTR | {row.get('campaign','?')} | канал: {row.get('channel','?')} | "
                    f"CTR: {row.get('ctr',0):.4f}"
                )

            lines.append("\nКампании с высоким CTR:")
            for _, row in df_ctr.sort_values("ctr", ascending=False).head(5).iterrows():
                lines.append(
                    f"- HIGH CTR | {row.get('campaign','?')} | канал: {row.get('channel','?')} | "
                    f"CTR: {row.get('ctr',0):.4f} | CPA: {row.get('cpa',0):.2f}"
                )

    if "channel" in df_channels.columns:
        lines.append("\nСводка по каналам:")
        for _, row in df_channels.iterrows():
            lines.append(
                f"- Канал: {row.get('channel','?')} | ROAS: {row.get('roas',0):.2f} | "
                f"CPA: {row.get('cpa',0):.2f} | Spend: {row.get('spend',0):.2f}"
            )

    summary = "\n".join(lines)
    return summary[:4000]
