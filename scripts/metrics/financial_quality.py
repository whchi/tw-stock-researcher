"""Deterministic financial-quality metric families.

Each function returns a MetricResult with an explicit `state`
(`ready` / `unavailable` / `not_meaningful`) instead of raising on a missing
input or a non-positive denominator, or silently returning a fabricated
zero. Correlated metrics share one `evidence_family` so a downstream
investment scenario cannot count several transforms of the same evidence as
independent votes.
"""

from decimal import Decimal

from metrics.common import not_meaningful, ready, safe_divide, to_decimal, unavailable

FORMULA_VERSION = "1"

FAMILY_WORKING_CAPITAL = "working_capital_efficiency"
FAMILY_CAPITAL_RETURNS = "capital_returns"
FAMILY_CASH_QUALITY = "cash_quality"
FAMILY_LEVERAGE = "leverage_capacity"
FAMILY_DILUTION = "dilution"
FAMILY_GOVERNANCE = "governance_disclosure"


def dso(accounts_receivable, revenue, days_in_period, period, input_refs):
    quotient = safe_divide(accounts_receivable, revenue)
    if quotient is None:
        return unavailable("DSO", FAMILY_WORKING_CAPITAL, "days", period, FORMULA_VERSION, input_refs, "missing accounts receivable or revenue")
    days = to_decimal(days_in_period)
    if days is None or days <= 0:
        return unavailable("DSO", FAMILY_WORKING_CAPITAL, "days", period, FORMULA_VERSION, input_refs, "invalid days_in_period")
    return ready("DSO", FAMILY_WORKING_CAPITAL, quotient * days, "days", period, FORMULA_VERSION, input_refs)


def dio(inventories, cost_of_goods_sold, days_in_period, period, input_refs):
    quotient = safe_divide(inventories, cost_of_goods_sold)
    if quotient is None:
        return unavailable("DIO", FAMILY_WORKING_CAPITAL, "days", period, FORMULA_VERSION, input_refs, "missing inventories or cost of goods sold")
    days = to_decimal(days_in_period)
    if days is None or days <= 0:
        return unavailable("DIO", FAMILY_WORKING_CAPITAL, "days", period, FORMULA_VERSION, input_refs, "invalid days_in_period")
    return ready("DIO", FAMILY_WORKING_CAPITAL, quotient * days, "days", period, FORMULA_VERSION, input_refs)


def dpo(accounts_payable, cost_of_goods_sold, days_in_period, period, input_refs):
    quotient = safe_divide(accounts_payable, cost_of_goods_sold)
    if quotient is None:
        return unavailable("DPO", FAMILY_WORKING_CAPITAL, "days", period, FORMULA_VERSION, input_refs, "missing accounts payable or cost of goods sold")
    days = to_decimal(days_in_period)
    if days is None or days <= 0:
        return unavailable("DPO", FAMILY_WORKING_CAPITAL, "days", period, FORMULA_VERSION, input_refs, "invalid days_in_period")
    return ready("DPO", FAMILY_WORKING_CAPITAL, quotient * days, "days", period, FORMULA_VERSION, input_refs)


def cash_conversion_cycle(dso_days, dio_days, dpo_days, period, input_refs):
    values = [to_decimal(v) for v in (dso_days, dio_days, dpo_days)]
    if any(v is None for v in values):
        return unavailable(
            "CashConversionCycle", FAMILY_WORKING_CAPITAL, "days", period, FORMULA_VERSION, input_refs,
            "DSO, DIO, or DPO is unavailable",
        )
    dso_value, dio_value, dpo_value = values
    return ready(
        "CashConversionCycle", FAMILY_WORKING_CAPITAL, dso_value + dio_value - dpo_value, "days", period,
        FORMULA_VERSION, input_refs,
    )


def incremental_roic(nopat_t, nopat_t_minus_3, capex, depreciation_amortization, change_in_nowc, period, input_refs):
    values = [to_decimal(v) for v in (nopat_t, nopat_t_minus_3, capex, depreciation_amortization, change_in_nowc)]
    if any(v is None for v in values):
        return unavailable(
            "IncrementalROIC3Y", FAMILY_CAPITAL_RETURNS, "ratio", period, FORMULA_VERSION, input_refs,
            "missing NOPAT, capex, depreciation, or change in net working capital",
        )
    nopat_t_v, nopat_t3_v, capex_v, da_v, nowc_v = values
    denominator = capex_v - da_v + nowc_v
    if denominator <= 0:
        return not_meaningful(
            "IncrementalROIC3Y", FAMILY_CAPITAL_RETURNS, "ratio", period, FORMULA_VERSION, input_refs,
            "non-positive invested-capital denominator",
        )
    return ready("IncrementalROIC3Y", FAMILY_CAPITAL_RETURNS, (nopat_t_v - nopat_t3_v) / denominator, "ratio", period, FORMULA_VERSION, input_refs)


def interest_coverage(ebit, interest_expense, period, input_refs):
    ebit_v = to_decimal(ebit)
    interest_v = to_decimal(interest_expense)
    if ebit_v is None or interest_v is None:
        return unavailable("InterestCoverage", FAMILY_LEVERAGE, "ratio", period, FORMULA_VERSION, input_refs, "missing EBIT or interest expense")
    if interest_v == 0:
        return not_meaningful("InterestCoverage", FAMILY_LEVERAGE, "ratio", period, FORMULA_VERSION, input_refs, "zero interest expense; coverage ratio undefined")
    return ready("InterestCoverage", FAMILY_LEVERAGE, ebit_v / abs(interest_v), "ratio", period, FORMULA_VERSION, input_refs)


def net_debt_to_ebitda(net_debt, ttm_ebitda, period, input_refs):
    net_debt_v = to_decimal(net_debt)
    ebitda_v = to_decimal(ttm_ebitda)
    if net_debt_v is None or ebitda_v is None:
        return unavailable("NetDebtToEBITDA", FAMILY_LEVERAGE, "ratio", period, FORMULA_VERSION, input_refs, "missing net debt or TTM EBITDA")
    if ebitda_v <= 0:
        return not_meaningful("NetDebtToEBITDA", FAMILY_LEVERAGE, "ratio", period, FORMULA_VERSION, input_refs, "non-positive EBITDA; ratio not meaningful")
    return ready("NetDebtToEBITDA", FAMILY_LEVERAGE, net_debt_v / ebitda_v, "ratio", period, FORMULA_VERSION, input_refs)


def diluted_share_growth(diluted_shares_t, diluted_shares_t0, years, period, input_refs):
    shares_t = to_decimal(diluted_shares_t)
    shares_t0 = to_decimal(diluted_shares_t0)
    years_v = to_decimal(years)
    if shares_t is None or shares_t0 is None or years_v is None:
        return unavailable("DilutedShareCAGR", FAMILY_DILUTION, "ratio", period, FORMULA_VERSION, input_refs, "missing diluted share counts or years")
    if shares_t0 <= 0 or years_v <= 0:
        return unavailable("DilutedShareCAGR", FAMILY_DILUTION, "ratio", period, FORMULA_VERSION, input_refs, "non-positive base share count or years")
    cagr = (shares_t / shares_t0) ** (Decimal("1") / years_v) - Decimal("1")
    return ready("DilutedShareCAGR", FAMILY_DILUTION, cagr, "ratio", period, FORMULA_VERSION, input_refs)


def owner_earnings(operating_cash_flow, maintenance_capex_estimate, period, input_refs):
    cfo = to_decimal(operating_cash_flow)
    capex = to_decimal(maintenance_capex_estimate)
    if cfo is None or capex is None:
        return unavailable("OwnerEarnings", FAMILY_CASH_QUALITY, "currency", period, FORMULA_VERSION, input_refs, "missing operating cash flow or maintenance capex estimate")
    return ready("OwnerEarnings", FAMILY_CASH_QUALITY, cfo - capex, "currency", period, FORMULA_VERSION, input_refs)


def cash_conversion(free_cash_flow, net_income, period, input_refs):
    fcf = to_decimal(free_cash_flow)
    ni = to_decimal(net_income)
    if fcf is None or ni is None:
        return unavailable("CashConversion", FAMILY_CASH_QUALITY, "ratio", period, FORMULA_VERSION, input_refs, "missing free cash flow or net income")
    if ni <= 0:
        return not_meaningful("CashConversion", FAMILY_CASH_QUALITY, "ratio", period, FORMULA_VERSION, input_refs, "non-positive net income; conversion ratio not meaningful")
    return ready("CashConversion", FAMILY_CASH_QUALITY, fcf / ni, "ratio", period, FORMULA_VERSION, input_refs)


def cash_flow_accrual(ttm_net_income, ttm_cfo, average_total_assets, period, input_refs):
    ni = to_decimal(ttm_net_income)
    cfo = to_decimal(ttm_cfo)
    assets = to_decimal(average_total_assets)
    if ni is None or cfo is None or assets is None:
        return unavailable("CashFlowAccrual", FAMILY_CASH_QUALITY, "ratio", period, FORMULA_VERSION, input_refs, "missing TTM net income, TTM CFO, or average total assets")
    if assets <= 0:
        return unavailable("CashFlowAccrual", FAMILY_CASH_QUALITY, "ratio", period, FORMULA_VERSION, input_refs, "non-positive average total assets")
    return ready("CashFlowAccrual", FAMILY_CASH_QUALITY, (ni - cfo) / assets, "ratio", period, FORMULA_VERSION, input_refs)


def dilution_adjusted_owner_earnings_cagr(owner_earnings_per_share_t, owner_earnings_per_share_t0, years, period, input_refs):
    oeps_t = to_decimal(owner_earnings_per_share_t)
    oeps_t0 = to_decimal(owner_earnings_per_share_t0)
    years_v = to_decimal(years)
    if oeps_t is None or oeps_t0 is None or years_v is None:
        return unavailable(
            "DilutionAdjustedOwnerEarningsCAGR", FAMILY_DILUTION, "ratio", period, FORMULA_VERSION, input_refs,
            "missing owner earnings per diluted share or years",
        )
    if years_v <= 0:
        return unavailable(
            "DilutionAdjustedOwnerEarningsCAGR", FAMILY_DILUTION, "ratio", period, FORMULA_VERSION, input_refs,
            "non-positive years",
        )
    if oeps_t0 <= 0:
        return not_meaningful(
            "DilutionAdjustedOwnerEarningsCAGR", FAMILY_DILUTION, "ratio", period, FORMULA_VERSION, input_refs,
            "non-positive base-period owner earnings per share; CAGR not meaningful",
        )
    cagr = (oeps_t / oeps_t0) ** (Decimal("1") / years_v) - Decimal("1")
    return ready("DilutionAdjustedOwnerEarningsCAGR", FAMILY_DILUTION, cagr, "ratio", period, FORMULA_VERSION, input_refs)


def governance_disclosure_vector(
    pledge_ratio,
    pre_announced_transfer_flag,
    modified_audit_opinion_flag,
    restatement_flag,
    penalty_flag,
    period,
    input_refs,
):
    """Independent governance/disclosure flags. Never collapsed into a single
    score -- correlated flags share FAMILY_GOVERNANCE but each keeps its own
    state so a scenario cannot silently double-count them."""

    def flag_result(metric_id, flag_value):
        if flag_value is None:
            return unavailable(metric_id, FAMILY_GOVERNANCE, "boolean", period, FORMULA_VERSION, input_refs, "flag not disclosed")
        return ready(metric_id, FAMILY_GOVERNANCE, Decimal("1") if flag_value else Decimal("0"), "boolean", period, FORMULA_VERSION, input_refs)

    pledge_value = to_decimal(pledge_ratio)
    if pledge_value is None:
        pledge_result = unavailable("PledgeRatio", FAMILY_GOVERNANCE, "pct", period, FORMULA_VERSION, input_refs, "pledge ratio not disclosed")
    else:
        pledge_result = ready("PledgeRatio", FAMILY_GOVERNANCE, pledge_value, "pct", period, FORMULA_VERSION, input_refs)

    return {
        "pledge_ratio": pledge_result,
        "pre_announced_transfer": flag_result("PreAnnouncedTransfer90d", pre_announced_transfer_flag),
        "modified_audit_opinion": flag_result("ModifiedAuditOpinion", modified_audit_opinion_flag),
        "restatement": flag_result("Restatement", restatement_flag),
        "penalty": flag_result("Penalty", penalty_flag),
    }
