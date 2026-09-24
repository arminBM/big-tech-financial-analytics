import os
from pathlib import Path

import pandas as pd

from sec_data import (
    fetch_company_facts,
    extract_annual_metric,
    calculate_derived_metrics,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

SEC_USER_AGENT = os.getenv("SEC_USER_AGENT")

if not SEC_USER_AGENT:
    raise RuntimeError(
        "SEC_USER_AGENT environment variable is not set."
    )

HEADERS = {
    "User-Agent": SEC_USER_AGENT
}

COMPANIES = {
    "Apple": {
        "ticker": "AAPL",
        "cik": "0000320193",
    },
    "Microsoft": {
        "ticker": "MSFT",
        "cik": "0000789019",
    },
    "Alphabet": {
        "ticker": "GOOGL",
        "cik": "0001652044",
    },
}

METRICS = {
    "Revenue": {
        "Apple": "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Microsoft": "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Alphabet": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
        ],
    },
    "Operating Income": "OperatingIncomeLoss",
    "Net Income": "NetIncomeLoss",
    "R&D Expense": "ResearchAndDevelopmentExpense",
    "Operating Cash Flow": "NetCashProvidedByUsedInOperatingActivities",
    "Capital Expenditure": "PaymentsToAcquirePropertyPlantAndEquipment",
}

def process_company(company_name, company_config):
    ticker = company_config["ticker"]
    cik = company_config["cik"]

    print(f"Fetching {company_name}...")

    company_data = fetch_company_facts(
        cik=cik,
        headers=HEADERS
    )

    metric_tables = []

    for metric_name, concept_config in METRICS.items():
        if isinstance(concept_config, dict):
            concept_name = concept_config[company_name]
        else:
            concept_name = concept_config

        metric_df = extract_annual_metric(
            company_data=company_data,
            concept_name=concept_name,
            company=company_name,
            ticker=ticker,
            metric=metric_name
        )

        metric_tables.append(metric_df)

    company_metrics = pd.concat(
        metric_tables,
        ignore_index=True
    )

    return company_metrics

def build_company_kpis(company_metrics):
    company_name = company_metrics["company"].iloc[0]
    ticker = company_metrics["ticker"].iloc[0]

    wide_df = (
        company_metrics
        .pivot(
            index="fiscal_year",
            columns="metric",
            values="value_billions"
        )
        .reset_index()
    )

    wide_df.columns.name = None

    wide_df = calculate_derived_metrics(wide_df)

    wide_df["company"] = company_name
    wide_df["ticker"] = ticker

    return wide_df

def main():
    all_metrics = []
    all_kpis = []

    for company_name, company_config in COMPANIES.items():
        company_metrics = process_company(
            company_name,
            company_config
        )

        metric_counts = (
            company_metrics
            .groupby("metric")["fiscal_year"]
            .nunique()
        )

        if not (metric_counts == 5).all():
            raise ValueError(
                f"Incomplete data found for {company_name}:\n"
                f"{metric_counts}"
            )

        company_kpis = build_company_kpis(
            company_metrics
        )

        all_metrics.append(company_metrics)
        all_kpis.append(company_kpis)

    financial_metrics_long = pd.concat(
        all_metrics,
        ignore_index=True
    )

    company_kpis = pd.concat(
        all_kpis,
        ignore_index=True
    )

    financial_metrics_long = (
        financial_metrics_long
        .sort_values(
            ["company", "metric", "fiscal_year"]
        )
        .reset_index(drop=True)
    )

    company_kpis = (
        company_kpis
        .sort_values(
            ["company", "fiscal_year"]
        )
        .reset_index(drop=True)
    )

    financial_metrics_long.to_csv(
        OUTPUT_DIR / "financial_metrics_long.csv",
        index=False
    )

    company_kpis.to_csv(
        OUTPUT_DIR / "company_kpis.csv",
        index=False
    )

    print()
    print("Pipeline completed successfully.")
    print(
        f"financial_metrics_long: "
        f"{financial_metrics_long.shape}"
    )
    print(
        f"company_kpis: "
        f"{company_kpis.shape}"
    )
    print(
        f"Files saved to: {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()