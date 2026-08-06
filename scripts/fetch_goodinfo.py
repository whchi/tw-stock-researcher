#!/usr/bin/env python3
# https://github.com/chengwesley/taiwan-stock-analysis
"""
fetch_goodinfo.py
從 Goodinfo.tw 抓取台灣股票財報數據，含三層驗證機制（Provenance / Sanity / MOPS連結）
用法：python fetch_goodinfo.py <股票代碼>
範例：python fetch_goodinfo.py 2317
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

if __package__:
    from .data_availability import build_data_availability, latest_observation_date
else:
    from data_availability import build_data_availability, latest_observation_date

# ─── 抓取層 ───────────────────────────────────────────────


def get_client_key():
    tz_offset = -480  # 台灣 UTC+8
    now_ms = time.time() * 1000
    days_since_epoch = now_ms / 86400000
    days_adjusted = days_since_epoch - tz_offset / 1440
    client_key = f"2.8|38057.1435627105|46946.0324515993|{tz_offset}|{days_adjusted}|{days_adjusted}"
    return client_key, days_adjusted


def fetch_report(stock_id, rpt_cat, days_adjusted, client_key, session=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={stock_id}",
    }
    cookies = {"CLIENT_KEY": client_key}
    url = f"https://goodinfo.tw/tw/StockFinDetail.asp?STOCK_ID={stock_id}&RPT_CAT={rpt_cat}"
    client = session if session is not None else requests
    r = client.get(url, headers=headers, cookies=cookies, timeout=30)
    r.encoding = "utf-8"
    return BeautifulSoup(r.text, "html.parser")


def parse_table(soup):
    """解析 Goodinfo 財報表格，返回 {欄位名: {年度: 數值}} 的字典"""
    tables = soup.find_all("table")
    if not tables:
        return {}, []

    t = max(tables, key=lambda table: len(table.find_all("tr")))
    rows = t.find_all("tr")
    years = []
    data = {}
    header_row_index = None
    paired_value_columns = False

    for i, row in enumerate(rows):
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        row_data = [c.get_text(strip=True) for c in cells]

        if not years and any(len(val) == 4 and val.isdigit() for val in row_data[1:]):
            header_row_index = i
            for val in row_data[1:]:
                if len(val) == 4 and val.isdigit():
                    years.append(val)
            continue

        if not years:
            continue

        if header_row_index is not None and i == header_row_index + 1 and row_data[0] == "金額":
            paired_value_columns = True
            continue

        if len(row_data) >= 3 and row_data[0]:
            field_name = row_data[0]
            values = {}
            val_cols = row_data[1:]
            step = 2 if paired_value_columns else 1
            for j, yr in enumerate(years):
                idx = j * step
                if idx < len(val_cols):
                    raw = val_cols[idx]
                    try:
                        values[yr] = float(raw.replace(",", ""))
                    except Exception:
                        values[yr] = None
            if values:
                data[field_name] = values

    return data, years


def pick_key(table, exact_name, includes=None, excludes=None):
    keys = list(table.keys()) if hasattr(table, "keys") else list(table)
    if hasattr(table, "keys") and exact_name in table:
        return exact_name
    if exact_name in keys:
        return exact_name

    includes = includes or [exact_name]
    excludes = excludes or []

    for key in keys:
        if all(term in key for term in includes) and all(term not in key for term in excludes):
            return key

    return None


THREE_STATEMENT_REQUIRED_ITEMS = {
    "revenue": {
        "statement": "income_statement",
        "required_for": "revenue growth and demand validation",
        "keys": [{"exact": "營業收入", "includes": ["營業收入"]}],
    },
    "operating_income": {
        "statement": "income_statement",
        "required_for": "operating leverage and interest coverage",
        "keys": [{"exact": "營業利益", "includes": ["營業利益"]}],
    },
    "net_income": {
        "statement": "income_statement",
        "required_for": "cash conversion and ROE",
        "keys": [{"exact": "稅後淨利", "includes": ["稅後淨利"], "excludes": ["合併"]}],
    },
    "cash": {
        "statement": "balance_sheet",
        "required_for": "liquidity and net cash / debt",
        "keys": [{"exact": "現金及約當現金", "includes": ["現金", "約當現金"]}],
    },
    "accounts_receivable": {
        "statement": "balance_sheet",
        "required_for": "revenue quality, DSO, and stuffing risk",
        "keys": [
            {"exact": "應收帳款淨額", "includes": ["應收帳款"]},
            {"exact": "應收帳款及票據", "includes": ["應收", "帳款"]},
        ],
    },
    "inventory": {
        "statement": "balance_sheet",
        "required_for": "DIO and inventory build risk",
        "keys": [{"exact": "存貨", "includes": ["存貨"]}],
    },
    "accounts_payable": {
        "statement": "balance_sheet",
        "required_for": "DPO and supplier financing read",
        "keys": [
            {"exact": "應付帳款", "includes": ["應付帳款"]},
            {"exact": "應付帳款及票據", "includes": ["應付", "帳款"]},
        ],
    },
    "current_assets": {
        "statement": "balance_sheet",
        "required_for": "current ratio and short-term resilience",
        "keys": [{"exact": "流動資產合計", "includes": ["流動資產合計"]}],
    },
    "current_liabilities": {
        "statement": "balance_sheet",
        "required_for": "current ratio and short-term resilience",
        "keys": [{"exact": "流動負債合計", "includes": ["流動負債合計"]}],
    },
    "total_liabilities": {
        "statement": "balance_sheet",
        "required_for": "debt ratio and leverage read",
        "keys": [{"exact": "負債總額", "includes": ["負債總額"]}],
    },
    "shareholder_equity": {
        "statement": "balance_sheet",
        "required_for": "ROE and shareholder value accrual",
        "keys": [{"exact": "股東權益總額", "includes": ["股東權益總額"]}],
    },
    "total_assets": {
        "statement": "balance_sheet",
        "required_for": "ROA and asset efficiency",
        "keys": [{"exact": "資產總額", "includes": ["資產總額"]}],
    },
    "operating_cash_flow": {
        "statement": "cash_flow",
        "required_for": "earnings quality and cash collection",
        "keys": [{"exact": "營業活動之淨現金流入(出)", "includes": ["營業活動"]}],
    },
    "investing_cash_flow": {
        "statement": "cash_flow",
        "required_for": "capital deployment read",
        "keys": [{"exact": "投資活動之淨現金流入(出)", "includes": ["投資活動"]}],
    },
    "financing_cash_flow": {
        "statement": "cash_flow",
        "required_for": "external financing / shareholder return read",
        "keys": [{"exact": "融資活動之淨現金流入(出)", "includes": ["融資活動"]}],
    },
    "capex": {
        "statement": "cash_flow",
        "required_for": "FCF, capital intensity, and capex productivity",
        "keys": [
            {"exact": "固定資產(增加)減少", "includes": ["固定資產", "增加"]},
            {"exact": "取得不動產、廠房及設備", "includes": ["不動產", "廠房", "設備"]},
        ],
    },
}


THREE_STATEMENT_SUPPLEMENTAL_ITEMS = {
    "depreciation_amortization": {
        "statement": "cash_flow",
        "required_for": "depreciation / revenue and fixed-cost pressure",
        "keys": [{"exact": "折舊及攤銷", "includes": ["折舊"]}],
    },
    "interest_expense": {
        "statement": "income_statement",
        "required_for": "interest coverage",
        "keys": [{"exact": "利息費用", "includes": ["利息費用"]}],
    },
    "short_term_debt": {
        "statement": "balance_sheet",
        "required_for": "near-term refinancing pressure",
        "keys": [{"exact": "短期借款", "includes": ["短期借款"]}],
    },
    "long_term_debt": {
        "statement": "balance_sheet",
        "required_for": "leverage and debt runway",
        "keys": [{"exact": "長期借款", "includes": ["長期借款"]}],
    },
    "prepaid_assets": {
        "statement": "balance_sheet",
        "required_for": "capacity prepayment and demand pull-forward",
        "keys": [{"exact": "預付款項", "includes": ["預付款"]}],
    },
    "contract_liabilities": {
        "statement": "balance_sheet",
        "required_for": "customer prepayment / deferred revenue demand signal",
        "keys": [
            {"exact": "合約負債", "includes": ["合約負債"]},
            {"exact": "遞延收入", "includes": ["遞延收入"]},
            {"exact": "預收款項", "includes": ["預收"]},
        ],
    },
    "goodwill": {
        "statement": "balance_sheet",
        "required_for": "M&A quality and impairment risk",
        "keys": [{"exact": "商譽", "includes": ["商譽"]}],
    },
    "intangible_assets": {
        "statement": "balance_sheet",
        "required_for": "intangible moat or acquisition accounting read",
        "keys": [{"exact": "無形資產", "includes": ["無形資產"]}],
    },
    "dividends": {
        "statement": "cash_flow",
        "required_for": "shareholder return and capital allocation",
        "keys": [{"exact": "發放現金股利", "includes": ["現金股利"]}],
    },
    "diluted_share_count": {
        "statement": "income_statement",
        "required_for": "dilution and per-share value creation",
        "keys": [{"exact": "稀釋加權平均股數", "includes": ["稀釋", "股數"]}],
    },
    "allowance_for_doubtful_accounts": {
        "statement": "mops_notes",
        "required_for": "receivable quality and bad-debt risk",
        "keys": [],
    },
    "debt_maturity_schedule": {
        "statement": "mops_notes",
        "required_for": "refinancing wall and debt maturity risk",
        "keys": [],
    },
}


def _match_item_key(result, item):
    table = result.get(item["statement"], {})
    for spec in item["keys"]:
        key = pick_key(
            table,
            spec["exact"],
            includes=spec.get("includes"),
            excludes=spec.get("excludes"),
        )
        if key:
            return key
    return None


def build_three_statement_coverage(result):
    required = {}
    required_missing = []

    for name, item in THREE_STATEMENT_REQUIRED_ITEMS.items():
        matched_key = _match_item_key(result, item)
        required[name] = {
            "statement": item["statement"],
            "matched_key": matched_key,
            "required_for": item["required_for"],
        }
        if matched_key is None:
            required_missing.append(name)

    supplemental = {}
    supplemental_missing = []
    for name, item in THREE_STATEMENT_SUPPLEMENTAL_ITEMS.items():
        matched_key = _match_item_key(result, item)
        supplemental[name] = {
            "statement": item["statement"],
            "matched_key": matched_key,
            "required_for": item["required_for"],
        }
        if matched_key is None:
            supplemental_missing.append(name)

    return {
        "purpose": "coverage check for balance-sheet demand validation and three-statement pattern read",
        "baseline_supported": not required_missing,
        "required": required,
        "required_missing": required_missing,
        "supplemental": supplemental,
        "supplemental_missing": supplemental_missing,
        "notes": [
            "Goodinfo IS_YEAR / BS_YEAR / CF_YEAR is enough for annual baseline pattern reads when required_missing is empty.",
            "Quarterly timing, debt maturity schedules, bad-debt allowance, contract-liability detail, and dilution notes still require MOPS filings or company reports when material.",
        ],
    }


# ─── 驗證層 A：資料來源標注 ────────────────────────────────


def build_metadata(stock_id, years):
    observation_date = latest_observation_date(years)
    return {
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "source": "Goodinfo.tw",
        "source_urls": {
            "income_statement": f"https://goodinfo.tw/tw/StockFinDetail.asp?RPT_CAT=IS_YEAR&STOCK_ID={stock_id}",
            "balance_sheet": f"https://goodinfo.tw/tw/StockFinDetail.asp?RPT_CAT=BS_YEAR&STOCK_ID={stock_id}",
            "cash_flow": f"https://goodinfo.tw/tw/StockFinDetail.asp?RPT_CAT=CF_YEAR&STOCK_ID={stock_id}",
        },
        "mops_url": f"https://mops.twse.com.tw/mops/web/t05st01?step=1&co_id={stock_id}&TYPEK=sii",
        "mops_url_otc": f"https://mops.twse.com.tw/mops/web/t05st01?step=1&co_id={stock_id}&TYPEK=otc",
        "years_covered": years[:3],
        "currency": "TWD 億元",
        "data_availability": build_data_availability(
            observation_date=observation_date,
            source="Goodinfo.tw",
            missing_inputs=[] if observation_date else ["financial_years"],
            failure_reasons=[]
            if observation_date
            else ["no_current_observation"],
        ),
    }


# ─── 驗證層 B：合理性檢查 ──────────────────────────────────


def sanity_check(metrics_by_year, years):
    """
    metrics_by_year: {year: {gross_margin, op_margin, net_margin,
                              current_ratio, debt_ratio, roe, roa}}
    回傳 warnings 列表，每項為 {'level': 'warn'|'error', 'field': str, 'msg': str}
    """
    warnings = []

    for yr in years:
        m = metrics_by_year.get(yr, {})

        gm = m.get("gross_margin")
        if gm is not None:
            if gm > 100:
                warnings.append(
                    {
                        "level": "error",
                        "field": f"{yr} 毛利率",
                        "msg": f"{gm:.1f}% 超過 100%，數據可能有誤",
                    }
                )
            elif gm < -50:
                warnings.append(
                    {
                        "level": "error",
                        "field": f"{yr} 毛利率",
                        "msg": f"{gm:.1f}% 低於 -50%，請確認是否為特殊損失年度",
                    }
                )

        cr = m.get("current_ratio")
        if cr is not None and cr < 0:
            warnings.append(
                {
                    "level": "error",
                    "field": f"{yr} 流動比率",
                    "msg": f"{cr:.1f}% 為負值，請檢查資產負債表數據",
                }
            )

        dr = m.get("debt_ratio")
        if dr is not None and dr > 100:
            warnings.append(
                {
                    "level": "warn",
                    "field": f"{yr} 負債比率",
                    "msg": f"{dr:.1f}% 超過 100%，若非金融業則為警示訊號",
                }
            )

        roe = m.get("roe")
        if roe is not None and roe > 100:
            warnings.append(
                {
                    "level": "warn",
                    "field": f"{yr} ROE",
                    "msg": f"{roe:.1f}% 超過 100%，可能為高槓桿，請確認股東權益是否偏低",
                }
            )

    # 相鄰年度淨利率波動檢查
    nm_list = [
        (yr, metrics_by_year[yr].get("net_margin"))
        for yr in years
        if yr in metrics_by_year
    ]
    for i in range(1, len(nm_list)):
        yr_prev, nm_prev = nm_list[i - 1]
        yr_curr, nm_curr = nm_list[i]
        if nm_prev is not None and nm_curr is not None:
            delta = nm_curr - nm_prev
            if abs(delta) > 30:
                warnings.append(
                    {
                        "level": "warn",
                        "field": f"{yr_prev}→{yr_curr} 淨利率",
                        "msg": f"波動 {delta:+.1f} 個百分點，建議確認是否有一次性損益",
                    }
                )

    return warnings


# ─── 主流程 ───────────────────────────────────────────────


def fetch_all(stock_id):
    client_key, days_adjusted = get_client_key()
    result = {"stock_id": stock_id}

    # Keep the requests sequential with polite sleeps (Goodinfo anti-scraping);
    # the shared session only reuses the TLS connection.
    with requests.Session() as session:
        print(f"正在抓取 {stock_id} 損益表...")
        is_soup = fetch_report(stock_id, "IS_YEAR", days_adjusted, client_key, session=session)
        is_data, years = parse_table(is_soup)
        result["income_statement"] = is_data
        result["years"] = years

        time.sleep(1)
        print(f"正在抓取 {stock_id} 資產負債表...")
        bs_soup = fetch_report(stock_id, "BS_YEAR", days_adjusted, client_key, session=session)
        bs_data, _ = parse_table(bs_soup)
        result["balance_sheet"] = bs_data

        time.sleep(1)
        print(f"正在抓取 {stock_id} 現金流量表...")
        cf_soup = fetch_report(stock_id, "CF_YEAR", days_adjusted, client_key, session=session)
        cf_data, _ = parse_table(cf_soup)
        result["cash_flow"] = cf_data

    result["three_statement_coverage"] = build_three_statement_coverage(result)

    # 驗證層 A：資料標注
    result["metadata"] = build_metadata(stock_id, years)

    return result


def run_verification(result, metrics_by_year):
    """在 fetch_all() 之後、建立儀表板之前呼叫。"""
    years = result["years"][:3]

    # 驗證層 B：合理性檢查
    warnings = sanity_check(metrics_by_year, years)
    if not years:
        warnings.append(
            {
                "level": "error",
                "field": "Goodinfo 財報年度",
                "msg": "未解析到任何年度，請重新抓取或改用 MOPS / 官方來源交叉確認",
            }
        )

    required_tables = [
        ("income_statement", "損益表"),
        ("balance_sheet", "資產負債表"),
        ("cash_flow", "現金流量表"),
    ]
    for key, label in required_tables:
        if not result.get(key):
            warnings.append(
                {
                    "level": "error",
                    "field": f"Goodinfo {label}",
                    "msg": f"未解析到{label}資料，不能作為 financial-analysis.md 主要證據",
                }
            )

    sanity_pass = all(w["level"] != "error" for w in warnings)

    result["verification"] = {
        "sanity": warnings,
        "sanity_pass": sanity_pass,
    }
    missing_inputs = []
    if not years:
        missing_inputs.append("financial_years")
    missing_inputs.extend(
        key for key, _label in required_tables if not result.get(key)
    )
    failure_reasons = [
        warning["msg"] for warning in warnings if warning["level"] == "error"
    ]
    result["metadata"]["data_availability"] = build_data_availability(
        observation_date=latest_observation_date(years),
        source="Goodinfo.tw",
        missing_inputs=missing_inputs,
        failure_reasons=failure_reasons,
    )

    if warnings:
        print(f"\n⚠️  合理性檢查發現 {len(warnings)} 項警示：")
        for w in warnings:
            icon = "❌" if w["level"] == "error" else "⚠️ "
            print(f"  {icon} [{w['field']}] {w['msg']}")
    else:
        print("✅ 合理性檢查通過，所有指標在合理範圍內")

    # 驗證層 C：MOPS 連結（已在 metadata 中）
    print(f"📋 MOPS 官方申報（上市）：{result['metadata']['mops_url']}")

    return result


def default_output_path(stock_id):
    repo_root = Path(__file__).resolve().parent.parent
    companies_dir = repo_root / "companies"
    case_dirs = sorted(p for p in companies_dir.glob(f"{stock_id}-*") if p.is_dir())

    if len(case_dirs) != 1:
        raise RuntimeError(
            f"Expected exactly one case directory for {stock_id}, found {len(case_dirs)}; "
            "create the case first or pass --output explicitly."
        )

    return case_dirs[0] / "raw-data.json"


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock_id", help="Taiwan stock id")
    parser.add_argument("--output", help="Output JSON path")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    stock_id = args.stock_id
    output_path = Path(args.output) if args.output else default_output_path(stock_id)
    data = fetch_all(stock_id)

    is_d = data["income_statement"]
    bs_d = data["balance_sheet"]
    cf_d = data["cash_flow"]
    years = data["years"][:3]

    # 計算衍生指標（示範用）
    def g(table, key, yr):
        return table.get(key, {}).get(yr)

    def safe(a, b):
        return a / b * 100 if (a is not None and b) else None

    metrics_by_year = {}
    for yr in years:
        rev_key = pick_key(is_d, "營業收入")
        gp_key = pick_key(is_d, "營業毛利淨額", includes=["營業毛利", "淨額"])
        if gp_key is None:
            gp_key = pick_key(is_d, "營業毛利", includes=["營業毛利"], excludes=["淨額"])
        ni_key = pick_key(is_d, "稅後淨利", includes=["稅後淨利"], excludes=["合併"])
        ca_key = next((k for k in bs_d if "流動資產合計" in k), None)
        cl_key = next((k for k in bs_d if "流動負債合計" in k), None)
        tl_key = next((k for k in bs_d if "負債總額" in k), None)
        ta_key = next((k for k in bs_d if "資產總額" in k), None)
        eq_key = next((k for k in bs_d if "股東權益總額" in k), None)

        rev = g(is_d, rev_key, yr) if rev_key else None
        gp = g(is_d, gp_key, yr) if gp_key else None
        ni = g(is_d, ni_key, yr) if ni_key else None
        ca = g(bs_d, ca_key, yr) if ca_key else None
        cl = g(bs_d, cl_key, yr) if cl_key else None
        tl = g(bs_d, tl_key, yr) if tl_key else None
        ta = g(bs_d, ta_key, yr) if ta_key else None
        eq = g(bs_d, eq_key, yr) if eq_key else None

        metrics_by_year[yr] = {
            "gross_margin": safe(gp, rev),
            "net_margin": safe(ni, rev),
            "current_ratio": safe(ca, cl),
            "debt_ratio": safe(tl, ta),
            "roe": safe(ni, eq),
            "roa": safe(ni, ta),
        }

    data = run_verification(data, metrics_by_year)

    print(f"\n=== {stock_id} 財報摘要 ===")
    print(f"年度: {years}")
    for yr in years:
        rev_key = pick_key(is_d, "營業收入")
        eps_key = pick_key(is_d, "每股稅後盈餘(元)", includes=["每股", "盈餘"])
        rev = g(is_d, rev_key, yr) if rev_key else None
        eps = g(is_d, eps_key, yr) if eps_key else None
        print(f"  {yr}: 營收={rev}億, EPS={eps}元")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n原始數據（含驗證結果）已存至 {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
