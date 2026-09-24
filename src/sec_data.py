import pandas as pd
import requests


def fetch_company_facts(cik, headers):
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    response = requests.get(
        url,
        headers=headers
    )

    response.raise_for_status()

    return response.json()


def extract_annual_metric(
    company_data,
    concept_name,
    company,
    ticker,
    metric
):
    if isinstance(concept_name, str):
        concept_names = [concept_name]
    else:
        concept_names = concept_name

    observations = []

    for name in concept_names:
        concept_observations = (
            company_data["facts"]["us-gaap"][name]["units"]["USD"]
        )

        observations.extend(concept_observations)

    df = pd.DataFrame(observations)

    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])

    df = df[
        (df["form"] == "10-K") &
        (df["fp"] == "FY")
    ].copy()

    df["period_days"] = (
        df["end"] - df["start"]
    ).dt.days

    df = df[
        df["period_days"] > 300
    ].copy()

    df["fiscal_year"] = df["end"].dt.year

    df = df[
        df["fiscal_year"].between(2021, 2025)
    ].copy()

    restatement_check = (
        df
        .groupby(["start", "end"])["val"]
        .nunique()
        .reset_index(name="unique_values")
    )

    restated_periods = restatement_check[
        restatement_check["unique_values"] > 1
    ]

    if not restated_periods.empty:
        raise ValueError(
            f"Conflicting values found for {company} - {metric}"
        )

    df = (
        df
        .sort_values("filed")
        .drop_duplicates(
            subset=["start", "end"],
            keep="first"
        )
        .copy()
    )

    df = df[
        ["fiscal_year", "start", "end", "val", "filed"]
    ].copy()

    df = df.rename(
        columns={
            "start": "period_start",
            "end": "period_end",
            "val": "value_usd"
        }
    )

    df["company"] = company
    df["ticker"] = ticker
    df["metric"] = metric

    df["value_billions"] = (
        df["value_usd"] / 1_000_000_000
    )

    df = df.reset_index(drop=True)

    return df


def calculate_derived_metrics(wide_df):
    df = wide_df.copy()

    df["Operating Margin (%)"] = (
        df["Operating Income"]
        / df["Revenue"]
        * 100
    ).round(2)

    df["Net Margin (%)"] = (
        df["Net Income"]
        / df["Revenue"]
        * 100
    ).round(2)

    df["R&D as % of Revenue"] = (
        df["R&D Expense"]
        / df["Revenue"]
        * 100
    ).round(2)

    df["Free Cash Flow"] = (
        df["Operating Cash Flow"]
        - df["Capital Expenditure"]
    )

    df["Revenue Growth (%)"] = (
        df["Revenue"]
        .pct_change()
        .mul(100)
        .round(2)
    )

    df["Free Cash Flow Margin (%)"] = (
        df["Free Cash Flow"]
        / df["Revenue"]
        * 100
    ).round(2)

    df["CapEx as % of Revenue"] = (
        df["Capital Expenditure"]
        / df["Revenue"]
        * 100
    ).round(2)

    return df