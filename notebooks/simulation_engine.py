# simulation_engine.py
# Shared simulation module for capstone "The Demographic Tide"
# Contains constants, age mappings, helper functions, and simulate_once().
# Imported by 02_model.ipynb and 05_sobol.ipynb.
# Place this file in the notebooks/ directory alongside the .ipynb files.
#
# v2: Birth-cohort tracking (ages 25-100), blended portfolio returns,
#     per-age IRS RMD rates, annual aging transition.
# v3: Wage/contribution growth (BLS ECI 3% nominal),
#     ownership cohort replacement (SCF 1989-2022 trend for ages 65+).
# v4: Per-year parameter variation (inflow_shock, vol_multiplier, bb_yield).
#     DC return feedback: when net flows are negative (new regime not in
#     historical returns), the G&K drag is applied to the return path.

import numpy as np

# ── Simulation grid ──────────────────────────────────────────────────────────
YEARS = np.arange(2025, 2051)
N_YEARS = len(YEARS)

# ── Module 2: Inflow constants ───────────────────────────────────────────────
PLAN_ACCESS = 0.72  # BLS NCS 2024: 72% of workers have DC plan access

# ── Module 4: Buyback constants ──────────────────────────────────────────────
RECESSION_CUT_MOD = 0.30  # S&P DJI: ~30% buyback decline in mild downturns
RECESSION_CUT_SEV = 0.50  # S&P DJI: ~50% buyback decline in GFC/COVID

# ── Module 5: Price impact constants ─────────────────────────────────────────
M_LOW, M_MID, M_HIGH = 3, 5, 7  # Gabaix & Koijen (2023)
CHI = 3.0                         # Haddad et al. (2025) strategic substitutability
PASSIVE_2025 = 35.0               # Chinco & Sammon (2024), rounded for 2025
PASSIVE_CAP = 67.0                # Double current global max (Section 4.12)
MKTCAP_2025_B = 64709             # Total US equity market cap, early 2025 (Fed Z.1)

# ── Bond return for blended portfolio growth ─────────────────────────────────
BOND_RETURN = 0.046  # 10-year Treasury nominal geometric mean (Damodaran, 1928-2024: 4.6%)

# ── Wage growth ──────────────────────────────────────────────────────────────
WAGE_GROWTH_NOMINAL = 0.0284  # BLS Employment Cost Index CAGR 2001-2025

# ── 65+ employment trend ─────────────────────────────────────────────────────
EMP_65_GROWTH = 0.0018      # Annual increase in 65+ employment ratio (BLS EPOP 2008-2024: 0.18pp/yr)
EMP_65_CAP = 0.25           # Maximum 65+ employment ratio (25% of age-group pop)
DEFAULT_STRESS_RETURN = -0.30  # Default crash magnitude for stress tests

# ── Ownership cohort replacement (ages 65+) ──────────────────────────────────
# As pension-era retirees (born <1947, ownership ~42%) are replaced by 401(k)
# cohorts (ownership 51-57%), retirement-age ownership rises.
# Targets: next-younger bracket's 2022 SCF rate (cohort replacement ceiling).
# Speed: 6% annual gap closure ≈ 11-year half-life (conservative; observed
# 2013-2022 SCF growth for 65-74 implies ~12%/yr, halved for prudence).
OWN_CONVERGE_RATE = 0.027  # Fraction of gap closed per year (SCF 65-74: 48%→51% in 9yr, gap=6pp)
OWN_TARGET_65_74 = 0.570   # SCF 2022 55-64 rate (next-younger bracket)
OWN_TARGET_75PLUS = 0.510  # SCF 2022 65-74 rate (next-younger bracket)

# ── Age-to-group mappings ────────────────────────────────────────────────────
INFLOW_AGE_MAP = {
    '<25':   list(range(16, 25)),
    '25-34': list(range(25, 35)),
    '35-44': list(range(35, 45)),
    '45-54': list(range(45, 55)),
    '55-64': list(range(55, 65)),
    '65+':   list(range(65, 101)),
}

OUTFLOW_AGE_MAP = {
    '55-59': list(range(55, 60)),
    '60-64': list(range(60, 65)),
    '65-72': list(range(65, 73)),
    '73-74': list(range(73, 75)),
    '75-84': list(range(75, 85)),
    '85-94': list(range(85, 95)),
    '95+':   list(range(95, 101)),
}

# ── Birth-cohort tracking constants ──────────────────────────────────────────
COHORT_AGES = np.arange(25, 101)  # 76 individual ages tracked
N_COHORT = len(COHORT_AGES)
IDX_55 = 30   # Index where age 55 starts (25 + 30 = 55)
IDX_65 = 40   # Index where age 65 starts (25 + 40 = 65)

# SCF 2022 mean retirement account balances ($K, conditional on ownership)
# Source: Federal Reserve Survey of Consumer Finances, 2022
SCF_MEAN_BALANCE_K = {
    '<35': 49.1, '35-44': 141.5, '45-54': 313.2,
    '55-64': 537.6, '65-74': 609.2, '75+': 462.4,
}

# SCF 2022 retirement account ownership rates (fraction)
SCF_OWNERSHIP = {
    '<35': 0.496, '35-44': 0.615, '45-54': 0.622,
    '55-64': 0.570, '65-74': 0.510, '75+': 0.420,
}

# TDF total equity allocation by age group (US + international)
# Source: Vanguard Target Retirement Fund glide path (2025b)
TOTAL_EQUITY_SHARE = {
    '<25': 0.90, '25-34': 0.88, '35-44': 0.86, '45-54': 0.76,
    '55-59': 0.64, '60-64': 0.50, '65-72': 0.40, '73-74': 0.35,
    '75-84': 0.30, '85-94': 0.30, '95+': 0.30,
}

# IRS Uniform Lifetime Table III — RMD rates by single-year age (fraction)
# Source: IRS Publication 590-B (2024). Rate = 1 / divisor.
# RMD starts at age 73 under SECURE 2.0 (born 1951-1959).
IRS_RMD_RATE = {
    73: 0.03774, 74: 0.03922, 75: 0.04065, 76: 0.04219, 77: 0.04367,
    78: 0.04545, 79: 0.04739, 80: 0.04950, 81: 0.05155, 82: 0.05405,
    83: 0.05650, 84: 0.05952, 85: 0.06250, 86: 0.06579, 87: 0.06944,
    88: 0.07299, 89: 0.07752, 90: 0.08197, 91: 0.08696, 92: 0.09259,
    93: 0.09901, 94: 0.10526, 95: 0.11236, 96: 0.11905, 97: 0.12821,
    98: 0.13699, 99: 0.14706, 100: 0.15625,
}


def get_age_pop(pop_row, age_list):
    """Sum population across single-year ages in age_list."""
    return sum(pop_row.get(a, 0) for a in age_list)


def haddad_multiplier(M_base, passive_share_pct):
    """
    Haddad et al. (2025) time-varying multiplier.
    As passive share grows, active investors partially offset lost elasticity.
    chi=3 implies ~1/3 pass-through to equilibrium prices.
    """
    active = (100 - passive_share_pct) / 100
    zeta_base = 1.0 / M_base
    delta_passive = (passive_share_pct - PASSIVE_2025) / 100
    pass_through = 1.0 / (1.0 + CHI * active)
    zeta_new = zeta_base * (1.0 - pass_through * delta_passive)
    zeta_new = max(zeta_new, 0.05)  # Floor to prevent numerical instability
    return 1.0 / zeta_new


def _age_to_scf_group(age):
    if age < 35: return '<35'
    if age < 45: return '35-44'
    if age < 55: return '45-54'
    if age < 65: return '55-64'
    if age < 75: return '65-74'
    return '75+'


def _age_to_equity_group(age):
    if age < 25: return '<25'
    if age < 35: return '25-34'
    if age < 45: return '35-44'
    if age < 55: return '45-54'
    if age < 60: return '55-59'
    if age < 65: return '60-64'
    if age < 73: return '65-72'
    if age < 75: return '73-74'
    if age < 85: return '75-84'
    if age < 95: return '85-94'
    return '95+'


def _age_to_outflow_group(age):
    if age < 55: return None
    if age < 60: return '55-59'
    if age < 65: return '60-64'
    if age < 73: return '65-72'
    if age < 75: return '73-74'
    if age < 85: return '75-84'
    if age < 95: return '85-94'
    return '95+'


def _age_to_inflow_group(age):
    if age < 25: return '<25'
    if age < 35: return '25-34'
    if age < 45: return '35-44'
    if age < 55: return '45-54'
    if age < 65: return '55-64'
    return '65+'


def simulate_once(params, pop_matrices, inflow_params, outflow_params, arima):
    """
    Run one 2025-2050 simulation path with birth-cohort balance tracking.

    Tracks 76 individual-age balances (ages 25-100) with:
    - Ages 25-64: annual contributions (salary x total contribution rate)
    - Ages 55+: withdrawals (max of IRS RMD rate or voluntary rate x TDF equity)
    - All ages: blended portfolio return (equity share x r_equity + bond share x 0.05)
    - Annual aging transition: each balance shifts to the next age; new 25-year-old
      enters with $0; 100-year-old exits.

    Parameters
    ----------
    params : dict with keys:
        demo_scenario, inflow_shock, vol_multiplier, net_buyback_yield,
        M_base, passive_z, returns, stress_year, stress_return, tdf_override

    Returns
    -------
    dict with: years, inflows, outflows, net_demo, buybacks, net_total,
               multipliers, passive_path, price_impact_pct, mktcap,
               crossover_demo, crossover_total
    """
    demo = params['demo_scenario']
    inflow_shock = params['inflow_shock']
    vol_mult = params['vol_multiplier']
    bb_yield = params['net_buyback_yield']
    M_base_val = params['M_base']
    passive_z = params['passive_z']
    returns = params['returns'].copy()
    tdf_override = params.get('tdf_override')

    # ── Per-year parameter support (v4) ──────────────────────────────────
    # MC paths pass arrays (size=N_YEARS); Sobol/deterministic pass scalars.
    # Broadcast scalars to constant arrays so the loop can always index [t].
    if np.isscalar(inflow_shock):
        inflow_shock = np.full(N_YEARS, inflow_shock)
    if np.isscalar(vol_mult):
        vol_mult = np.full(N_YEARS, vol_mult)
    if np.isscalar(bb_yield):
        bb_yield = np.full(N_YEARS, bb_yield)

    if params.get('stress_year') is not None:
        yr_idx = params['stress_year'] - 2025
        if 0 <= yr_idx < N_YEARS:
            returns[yr_idx] = params.get('stress_return', DEFAULT_STRESS_RETURN)

    pop = pop_matrices[demo]

    # ── Passive share path from ARIMA forecast + uncertainty ──────────────
    passive_path = np.zeros(N_YEARS)
    for t, yr in enumerate(YEARS):
        arima_row = arima[arima['year'] == yr]
        if len(arima_row) > 0:
            central = arima_row['cs_narrow_pct'].values[0]
            sigma = arima_row['cs_sigma'].values[0]
            passive_path[t] = np.clip(central + passive_z * sigma, 0, PASSIVE_CAP)
        else:
            passive_path[t] = PASSIVE_2025

    # ── Initialize per-age arrays (76 ages: 25-100) ─────────────────────
    bal = np.zeros(N_COHORT)
    own = np.zeros(N_COHORT)
    vol_base = np.zeros(N_COHORT)
    rmd_arr = np.zeros(N_COHORT)
    tdf_us_arr = np.zeros(N_COHORT)
    tot_eq_arr = np.zeros(N_COHORT)
    contrib_k = np.zeros(N_COHORT)
    outflow_grp = [None] * N_COHORT

    for idx in range(N_COHORT):
        age = COHORT_AGES[idx]

        # SCF balance and ownership
        scf_g = _age_to_scf_group(age)
        bal[idx] = SCF_MEAN_BALANCE_K[scf_g]
        own[idx] = SCF_OWNERSHIP[scf_g]

        # Total equity share for blended returns
        tot_eq_arr[idx] = TOTAL_EQUITY_SHARE[_age_to_equity_group(age)]

        # IRS RMD rate (0 below age 73)
        rmd_arr[idx] = IRS_RMD_RATE.get(age, 0.0)

        # Outflow-group parameters (ages 55+)
        og = _age_to_outflow_group(age)
        outflow_grp[idx] = og
        if og is not None:
            orow = outflow_params[outflow_params['age_group'] == og].iloc[0]
            vol_base[idx] = orow['voluntary_rate_pct'] / 100
            tdf_us_arr[idx] = orow['tdf_us_equity_pct'] / 100
        else:
            ig = _age_to_inflow_group(age)
            irow = inflow_params[inflow_params['Age Group'] == ig].iloc[0]
            tdf_us_arr[idx] = irow['TDF US Equity Share (Model)']

        # Contributions per participant ($K/year, ages 25-64)
        if age < 65:
            ig = _age_to_inflow_group(age)
            irow = inflow_params[inflow_params['Age Group'] == ig].iloc[0]
            contrib_k[idx] = (irow['Median Annual Salary ($)']
                              * irow['Total Contribution Rate']) / 1000

    # ── Pre-extract 65+ base employment ratio for inflow section ─────────
    base_emp_65 = inflow_params.loc[inflow_params['Age Group'] == '65+',
                                     'Employment Ratio'].values[0]

    # ── Output arrays ────────────────────────────────────────────────────
    inflows = np.zeros(N_YEARS)
    outflows = np.zeros(N_YEARS)
    buybacks = np.zeros(N_YEARS)
    multipliers = np.zeros(N_YEARS)
    mktcap = np.zeros(N_YEARS)
    mktcap[0] = MKTCAP_2025_B

    # ── Main simulation loop ─────────────────────────────────────────────
    for t, yr in enumerate(YEARS):
        pop_yr = pop.loc[yr] if yr in pop.index else pop.iloc[-1]
        r_t = returns[t]

        # ── WAGE GROWTH (BLS ECI, 3% nominal) ───────────────────────────
        wage_factor = (1 + WAGE_GROWTH_NOMINAL) ** (yr - 2025)

        # ── OWNERSHIP COHORT REPLACEMENT (ages 65+) ─────────────────────
        # Pension-era retirees replaced by 401(k) cohorts each year
        for idx in range(IDX_65, N_COHORT):
            age = COHORT_AGES[idx]
            target = OWN_TARGET_65_74 if age < 75 else OWN_TARGET_75PLUS
            own[idx] = own[idx] + OWN_CONVERGE_RATE * (target - own[idx])

        # ── INFLOWS (aggregate equity flow into market) ──────────────────
        total_inflow = 0.0
        for _, irow in inflow_params.iterrows():
            ag = irow['Age Group']
            ages = INFLOW_AGE_MAP[ag]
            age_pop = get_age_pop(pop_yr, ages)
            emp_ratio = irow['Employment Ratio']
            if ag == '65+':
                emp_ratio = base_emp_65 + EMP_65_GROWTH * (yr - 2025)
                emp_ratio = min(emp_ratio, EMP_65_CAP)
            equity_per_worker = irow['Annual US Equity per Worker ($)'] * wage_factor
            total_inflow += age_pop * emp_ratio * equity_per_worker / 1e9
        inflows[t] = total_inflow * PLAN_ACCESS * inflow_shock[t]

        # ── OUTFLOWS (birth-cohort: per-age withdrawals, ages 55+) ───────
        vol_scaled = vol_base * vol_mult[t]
        eff_rates = np.maximum(rmd_arr, vol_scaled)

        # TDF US equity with possible override (exponential decay toward TDF base)
        # Cohort replacement: self-directed retirees gradually replaced by TDF cohorts.
        # decay = exp(-3 * t_frac) → starts at 1.0 (full override), ~95% converged by end.
        tdf_eq = tdf_us_arr.copy()
        if tdf_override and tdf_override['start'] <= yr <= tdf_override['end']:
            t_frac = (yr - tdf_override['start']) / max(tdf_override['end'] - tdf_override['start'], 1)
            decay = np.exp(-3.0 * t_frac)
            for idx in range(IDX_55, N_COHORT):
                if outflow_grp[idx] in tdf_override['groups']:
                    base_pct = tdf_us_arr[idx]
                    override_pct = tdf_override['equity_pct'] / 100
                    tdf_eq[idx] = base_pct + (override_pct - base_pct) * decay

        # Withdrawals ($K per account holder)
        withdrawals_k = bal * eff_rates

        # Equity outflow per person ($B)
        eq_out_per_person_B = withdrawals_k * tdf_eq * own * 1000 / 1e9

        # Aggregate outflow: population-weighted sum (ages 55+)
        total_outflow = 0.0
        for idx in range(IDX_55, N_COHORT):
            age = COHORT_AGES[idx]
            pop_age = pop_yr.get(age, 0)
            total_outflow += pop_age * eq_out_per_person_B[idx]
        outflows[t] = total_outflow

        # ── MULTIPLIER (moved up — needed for DC return adjustment) ───────
        multipliers[t] = haddad_multiplier(M_base_val, passive_path[t])

        # ── DC RETURN ADJUSTMENT (v4) ────────────────────────────────────
        # Historical returns embed positive DC flows (which prevailed 1990-2024).
        # Negative DC flows are a new regime absent from the historical sample.
        # Apply the G&K drag only when net flow is negative; positive flows
        # are already priced into the drawn return distribution.
        mc_boy = mktcap[t] if t == 0 else mktcap[t-1]
        net_flow_t = inflows[t] - outflows[t]
        dc_return = multipliers[t] * min(net_flow_t, 0) / mc_boy if mc_boy > 0 else 0.0
        r_adj = r_t + dc_return

        # ── BALANCE UPDATE ───────────────────────────────────────────────
        # Blended return: equity portion at adjusted rate, bond at fixed rate
        r_blended = tot_eq_arr * r_adj + (1.0 - tot_eq_arr) * BOND_RETURN

        # balance = (balance - withdrawals + contributions) x (1 + r_blended)
        bal = np.maximum((bal - withdrawals_k + contrib_k * wage_factor) * (1.0 + r_blended), 0.0)

        # ── AGING TRANSITION ─────────────────────────────────────────────
        # Everyone ages by one year. 100-year-old exits. New 25-year-old enters.
        bal = np.roll(bal, 1)
        bal[0] = 0.0  # New 25-year-old starts with $0

        # ── BUYBACKS (yield-based, procyclical, uses r_adj) ──────────────
        procyclical = 1.0
        if r_adj < -0.20:
            procyclical = 1.0 - RECESSION_CUT_SEV
        elif r_adj < -0.10:
            procyclical = 1.0 - RECESSION_CUT_MOD
        current_mc = mc_boy if t == 0 else mc_boy * (1 + r_adj)
        buybacks[t] = current_mc * bb_yield[t] * procyclical

        # ── MARKET CAP ───────────────────────────────────────────────────
        if t > 0:
            mktcap[t] = mc_boy * (1 + r_adj)
            mktcap[t] = max(mktcap[t], 5000)

    # ── Post-loop calculations ───────────────────────────────────────────
    net_demo = inflows - outflows
    net_total = net_demo + buybacks
    price_impact_pct = np.where(mktcap > 0,
                                multipliers * net_demo / mktcap * 100, 0)

    neg_years = YEARS[net_demo < 0]
    crossover_demo = int(neg_years[0]) if len(neg_years) > 0 else 2099
    neg_total = YEARS[net_total < 0]
    crossover_total = int(neg_total[0]) if len(neg_total) > 0 else 2099

    return {
        'years': YEARS, 'inflows': inflows, 'outflows': outflows,
        'net_demo': net_demo, 'buybacks': buybacks, 'net_total': net_total,
        'multipliers': multipliers, 'passive_path': passive_path,
        'price_impact_pct': price_impact_pct, 'mktcap': mktcap,
        'crossover_demo': crossover_demo, 'crossover_total': crossover_total,
    }
