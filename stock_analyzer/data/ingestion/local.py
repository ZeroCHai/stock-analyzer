"""
Local file ingestion — PLACEHOLDER.

TODO: Implement once the local file format is confirmed.

Expected interface:
    load_local_data(file_path: str) -> dict
        Parse a user-provided file and return a dict compatible
        with the financials schema used by db.upsert_financials().

Likely formats to support: CSV, Excel (.xlsx), JSON.
Key fields expected: symbol, revenue, net_income, total_assets,
                     total_equity, eps, pe_ratio, etc.
"""


def load_local_data(file_path: str) -> dict:
    raise NotImplementedError(
        "Local file ingestion is not yet implemented. "
        "Please provide the file format so this module can be completed."
    )
