"""Load ecommerce customer churn CSV and print summary, missing values, columns, and samples."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_churn_csv(csv_path: Path) -> pd.DataFrame:
    """Read the churn dataset from a CSV file.

    Args:
        csv_path: Absolute or relative path to the CSV file.

    Returns:
        DataFrame containing the churn records.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
    """
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    return pd.read_csv(csv_path)


def main() -> None:
    """Print describe(), missing-value stats, column names, and the first five rows."""
    root = Path(__file__).resolve().parent
    csv_path = root / "data" / "archive" / "data_ecommerce_customer_churn.csv"
    df = load_churn_csv(csv_path)

    print("=== describe() ===")
    print(df.describe())
    print()

    print("=== 各欄位缺失值 ===")
    missing_count = df.isna().sum()
    missing_pct = (missing_count / len(df) * 100).round(2)
    missing_summary = pd.DataFrame(
        {"missing_count": missing_count, "missing_pct": missing_pct}
    )
    print(missing_summary)
    print()

    print("=== 欄位 (columns) ===")
    print(df.columns.tolist())
    print()

    print("=== 前五筆資料 ===")
    print(df.head(5))


if __name__ == "__main__":
    main()
