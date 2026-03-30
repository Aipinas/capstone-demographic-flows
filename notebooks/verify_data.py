# verify_data.py
# Deep data ingestion verification for "The Demographic Tide"
# Run from notebooks/ directory: python verify_data.py
# Takes ~5 seconds. Run BEFORE model_runner.py.
# Checks actual data content at specific ages, not just file shapes.

import numpy as np
import pandas as pd
import sys
import importlib
import simulation_engine
importlib.reload(simulation_engine)
from simulation_engine import (
    YEARS, N_YEARS, PLAN_ACCESS, M_LOW, M_HIGH, CHI,
    PASSIVE_2025, PASSIVE_CAP, MKTCAP_2025_B, BOND_RETURN,
    WAGE_GROWTH_NOMINAL, OWN_CONVERGE_RATE, EMP_65_GROWTH,
    INFLOW_AGE_MAP, OUTFLOW_AGE_MAP, COHORT_AGES, N_COHORT,
    IDX_55, IDX_65, IRS_RMD_RATE, SCF_MEAN_BALANCE_K,
    SCF_OWNERSHIP, TOTAL_EQUITY_SHARE,
    _age_to_scf_group, _age_to_equity_group, _age_to_outflow_group,
    _age_to_inflow_group, simulate_once
)

PROC = r'..\data\processed'
PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  OK: {name}')
    else:
        FAIL += 1
        print(f'  FAIL: {name} — {detail}')

print("=" * 70)
print("DEEP DATA INGESTION VERIFICATION")
print("=" * 70)

# ═════════════════════════════════════════════════════════════════════════
# 1. ENGINE CONSTANTS
# ═════════════════════════════════════════════════════════════════════════
print("\n[1] Engine constants:")
check("BOND_RETURN = 0.046", BOND_RETURN == 0.046, f"got {BOND_RETURN}")
check("MKTCAP_2025_B = 64709", MKTCAP_2025_B == 64709, f"got {MKTCAP_2025_B}")
check("PASSIVE_CAP = 67.0", PASSIVE_CAP == 67.0, f"got {PASSIVE_CAP}")
check("PASSIVE_2025 = 35.0", PASSIVE_2025 == 35.0, f"got {PASSIVE_2025}")
check("M_LOW=3, M_HIGH=7", M_LOW == 3 and M_HIGH == 7, f"got {M_LOW},{M_HIGH}")
check("CHI = 3.0", CHI == 3.0, f"got {CHI}")
check("PLAN_ACCESS = 0.72", PLAN_ACCESS == 0.72, f"got {PLAN_ACCESS}")
check("WAGE_GROWTH = 0.0284", WAGE_GROWTH_NOMINAL == 0.0284, f"got {WAGE_GROWTH_NOMINAL}")
check("OWN_CONVERGE = 0.027", OWN_CONVERGE_RATE == 0.027, f"got {OWN_CONVERGE_RATE}")
check("EMP_65_GROWTH = 0.0018", EMP_65_GROWTH == 0.0018, f"got {EMP_65_GROWTH}")
check("N_YEARS = 26", N_YEARS == 26, f"got {N_YEARS}")
check("N_COHORT = 76", N_COHORT == 76, f"got {N_COHORT}")
check("IDX_55 = 30", IDX_55 == 30, f"got {IDX_55}")
check("IDX_65 = 40", IDX_65 == 40, f"got {IDX_65}")
check("COHORT_AGES[0] = 25", COHORT_AGES[0] == 25, f"got {COHORT_AGES[0]}")
check("COHORT_AGES[75] = 100", COHORT_AGES[75] == 100, f"got {COHORT_AGES[75]}")
check("COHORT_AGES[IDX_55] = 55", COHORT_AGES[IDX_55] == 55, f"got {COHORT_AGES[IDX_55]}")
check("COHORT_AGES[IDX_65] = 65", COHORT_AGES[IDX_65] == 65, f"got {COHORT_AGES[IDX_65]}")

# ═════════════════════════════════════════════════════════════════════════
# 2. AGE MAPPING FUNCTIONS — spot checks
# ═════════════════════════════════════════════════════════════════════════
print("\n[2] Age mapping functions:")
check("age 30 -> SCF '25-34'", _age_to_scf_group(30) == '25-34', f"got {_age_to_scf_group(30)}")
check("age 65 -> SCF '65-74'", _age_to_scf_group(65) == '65-74', f"got {_age_to_scf_group(65)}")
check("age 80 -> SCF '75+'", _age_to_scf_group(80) == '75+', f"got {_age_to_scf_group(80)}")
check("age 57 -> equity '55-59'", _age_to_equity_group(57) == '55-59', f"got {_age_to_equity_group(57)}")
check("age 73 -> equity '73-74'", _age_to_equity_group(73) == '73-74', f"got {_age_to_equity_group(73)}")
check("age 80 -> equity '75-84'", _age_to_equity_group(80) == '75-84', f"got {_age_to_equity_group(80)}")
check("age 50 -> outflow None", _age_to_outflow_group(50) is None, f"got {_age_to_outflow_group(50)}")
check("age 57 -> outflow '55-59'", _age_to_outflow_group(57) == '55-59', f"got {_age_to_outflow_group(57)}")
check("age 73 -> outflow '73-74'", _age_to_outflow_group(73) == '73-74', f"got {_age_to_outflow_group(73)}")
check("age 96 -> outflow '95+'", _age_to_outflow_group(96) == '95+', f"got {_age_to_outflow_group(96)}")
check("age 30 -> inflow '25-34'", _age_to_inflow_group(30) == '25-34', f"got {_age_to_inflow_group(30)}")
check("age 66 -> inflow '65+'", _age_to_inflow_group(66) == '65+', f"got {_age_to_inflow_group(66)}")

# ═════════════════════════════════════════════════════════════════════════
# 3. IRS RMD RATES — verified against Pub 590-B
# ═════════════════════════════════════════════════════════════════════════
print("\n[3] IRS RMD rates (Pub 590-B):")
check("no RMD at age 72", IRS_RMD_RATE.get(72, 0.0) == 0.0, f"got {IRS_RMD_RATE.get(72, 0.0)}")
check("RMD at 73 = 1/26.5 = 3.774%", abs(IRS_RMD_RATE[73] - 1/26.5) < 0.001, f"got {IRS_RMD_RATE[73]:.5f}")
check("RMD at 75 = 4.065%", abs(IRS_RMD_RATE[75] - 0.04065) < 0.0001, f"got {IRS_RMD_RATE[75]}")
check("RMD at 80 = 4.950%", abs(IRS_RMD_RATE[80] - 0.04950) < 0.0001, f"got {IRS_RMD_RATE[80]}")
check("RMD at 90 = 8.197%", abs(IRS_RMD_RATE[90] - 0.08197) < 0.0001, f"got {IRS_RMD_RATE[90]}")
check("RMD at 100 = 15.625%", abs(IRS_RMD_RATE[100] - 0.15625) < 0.0001, f"got {IRS_RMD_RATE[100]}")
check("RMD increases with age", IRS_RMD_RATE[80] > IRS_RMD_RATE[73] and IRS_RMD_RATE[90] > IRS_RMD_RATE[80], "non-monotonic!")
check("28 RMD entries (ages 73-100)", len(IRS_RMD_RATE) == 28, f"got {len(IRS_RMD_RATE)}")

# ═════════════════════════════════════════════════════════════════════════
# 4. SCF BALANCES AND OWNERSHIP
# ═════════════════════════════════════════════════════════════════════════
print("\n[4] SCF balances and ownership:")
check("balance <35 = $49.1K", SCF_MEAN_BALANCE_K['<35'] == 49.1, f"got {SCF_MEAN_BALANCE_K['<35']}")
check("balance 55-64 = $537.6K", SCF_MEAN_BALANCE_K['55-64'] == 537.6, f"got {SCF_MEAN_BALANCE_K['55-64']}")
check("balance 65-74 = $609.2K", SCF_MEAN_BALANCE_K['65-74'] == 609.2, f"got {SCF_MEAN_BALANCE_K['65-74']}")
check("balance 75+ = $462.4K", SCF_MEAN_BALANCE_K['75+'] == 462.4, f"got {SCF_MEAN_BALANCE_K['75+']}")
check("balances rise to 65-74", SCF_MEAN_BALANCE_K['65-74'] > SCF_MEAN_BALANCE_K['55-64'] > SCF_MEAN_BALANCE_K['45-54'], "non-monotonic!")
check("ownership 65-74 = 0.510", SCF_OWNERSHIP['65-74'] == 0.510, f"got {SCF_OWNERSHIP['65-74']}")
check("ownership 75+ = 0.420", SCF_OWNERSHIP['75+'] == 0.420, f"got {SCF_OWNERSHIP['75+']}")

# ═════════════════════════════════════════════════════════════════════════
# 5. TDF EQUITY SHARES — glide path must decrease with age
# ═════════════════════════════════════════════════════════════════════════
print("\n[5] TDF equity allocations (glide path):")
check("TDF <25 = 0.90", TOTAL_EQUITY_SHARE['<25'] == 0.90, f"got {TOTAL_EQUITY_SHARE['<25']}")
check("TDF 55-59 = 0.64", TOTAL_EQUITY_SHARE['55-59'] == 0.64, f"got {TOTAL_EQUITY_SHARE['55-59']}")
check("TDF 65-72 = 0.40", TOTAL_EQUITY_SHARE['65-72'] == 0.40, f"got {TOTAL_EQUITY_SHARE['65-72']}")
check("TDF 75-84 = 0.30", TOTAL_EQUITY_SHARE['75-84'] == 0.30, f"got {TOTAL_EQUITY_SHARE['75-84']}")
check("glide path decreases", TOTAL_EQUITY_SHARE['<25'] > TOTAL_EQUITY_SHARE['45-54'] > TOTAL_EQUITY_SHARE['65-72'] >= TOTAL_EQUITY_SHARE['75-84'], "not decreasing!")

# ═════════════════════════════════════════════════════════════════════════
# 6. AGE MAP COVERAGE — no gaps, no overlaps
# ═════════════════════════════════════════════════════════════════════════
print("\n[6] Age map coverage:")
inflow_all = []
for ages in INFLOW_AGE_MAP.values():
    inflow_all.extend(ages)
check("inflow map covers 16-100", sorted(inflow_all) == list(range(16, 101)), "gaps or overlaps!")
outflow_all = []
for ages in OUTFLOW_AGE_MAP.values():
    outflow_all.extend(ages)
check("outflow map covers 55-100", sorted(outflow_all) == list(range(55, 101)), "gaps or overlaps!")

# ═════════════════════════════════════════════════════════════════════════
# 7. POPULATION MATRICES — actual row/column content
# ═════════════════════════════════════════════════════════════════════════
print("\n[7] Population matrices:")
pop_matrices = {}
for scenario in ['mid', 'hi', 'low']:
    df = pd.read_csv(f'{PROC}\\pop_age_matrix_{scenario}.csv', index_col=0)
    df.columns = [int(c) for c in df.columns]
    df.index = [int(i) for i in df.index]
    pop_matrices[scenario] = df
    check(f"pop_{scenario} has 2025", 2025 in df.index, f"missing")
    check(f"pop_{scenario} has 2050", 2050 in df.index, f"missing")
    check(f"pop_{scenario} has age 25", 25 in df.columns, f"missing")
    check(f"pop_{scenario} has age 100", 100 in df.columns, f"missing")
    # Spot check: age 30 in 2025 should be ~4-5 million (in thousands)
    pop_30 = df.loc[2025, 30]
    check(f"pop_{scenario} age 30 in 2025 ~4-5M", 3500 < pop_30 < 5500, f"got {pop_30:.0f}K")
    # 65+ total
    pop65 = sum(df.loc[2025].get(a, 0) for a in range(65, 101))
    check(f"pop_{scenario} 65+ ~58-68M", 55000 < pop65 < 72000, f"got {pop65:,.0f}K")
    # 65+ must grow by 2050
    pop65_50 = sum(df.loc[2050].get(a, 0) for a in range(65, 101))
    check(f"pop_{scenario} 65+ grows", pop65_50 > pop65, f"2025={pop65:,.0f}K, 2050={pop65_50:,.0f}K")

# ═════════════════════════════════════════════════════════════════════════
# 8. INFLOW PARAMS CSV — row-level content
# ═════════════════════════════════════════════════════════════════════════
print("\n[8] Inflow parameters (row-level):")
inflow = pd.read_csv(f'{PROC}\\module2_inflow_params.csv')
check("6 age groups", len(inflow) == 6, f"got {len(inflow)}")
required_cols = ['Age Group', 'Employment Ratio', 'Median Annual Salary ($)',
                 'Total Contribution Rate', 'TDF US Equity Share (Model)',
                 'Annual US Equity per Worker ($)']
for col in required_cols:
    check(f"column '{col}'", col in inflow.columns, "missing!")

# Salary should increase with age (up to 55-64)
sal_25 = inflow[inflow['Age Group']=='25-34']['Median Annual Salary ($)'].values[0]
sal_45 = inflow[inflow['Age Group']=='45-54']['Median Annual Salary ($)'].values[0]
check("salary 45-54 > salary 25-34", sal_45 > sal_25, f"45-54=${sal_45:,.0f}, 25-34=${sal_25:,.0f}")

# Equity per worker should be positive for all groups
for _, row in inflow.iterrows():
    val = row['Annual US Equity per Worker ($)']
    check(f"equity/worker {row['Age Group']} > 0", val > 0, f"got ${val:,.0f}")

# TDF equity should decrease with age
tdf_25 = inflow[inflow['Age Group']=='25-34']['TDF US Equity Share (Model)'].values[0]
tdf_55 = inflow[inflow['Age Group']=='55-64']['TDF US Equity Share (Model)'].values[0]
check("TDF equity 25-34 > 55-64", tdf_25 > tdf_55, f"25-34={tdf_25:.2f}, 55-64={tdf_55:.2f}")

# ═════════════════════════════════════════════════════════════════════════
# 9. OUTFLOW PARAMS CSV — row-level content, off-by-one detection
# ═════════════════════════════════════════════════════════════════════════
print("\n[9] Outflow parameters (row-level):")
outflow = pd.read_csv(f'{PROC}\\module3_outflow_params.csv')
check("7 age groups", len(outflow) == 7, f"got {len(outflow)}")

# RMD must be 0 for pre-73 groups — THIS IS THE KEY OFF-BY-ONE CHECK
for grp in ['55-59', '60-64', '65-72']:
    rmd = outflow[outflow['age_group']==grp]['rmd_rate_pct'].values[0]
    check(f"RMD {grp} = 0 (pre-73)", rmd == 0.0, f"got {rmd}% — OFF BY ONE ROW?")

# RMD must be positive for 73+ groups
for grp in ['73-74', '75-84', '85-94', '95+']:
    rmd = outflow[outflow['age_group']==grp]['rmd_rate_pct'].values[0]
    check(f"RMD {grp} > 0 (post-73)", rmd > 3.0, f"got {rmd}%")

# RMD should increase with age
rmd_73 = outflow[outflow['age_group']=='73-74']['rmd_rate_pct'].values[0]
rmd_75 = outflow[outflow['age_group']=='75-84']['rmd_rate_pct'].values[0]
rmd_85 = outflow[outflow['age_group']=='85-94']['rmd_rate_pct'].values[0]
check("RMD 85-94 > 75-84 > 73-74", rmd_85 > rmd_75 > rmd_73, f"got {rmd_73:.1f}, {rmd_75:.1f}, {rmd_85:.1f}")

# Balance should be highest for 55-59 or 60-64 (peak accumulation)
bal_55 = outflow[outflow['age_group']=='55-59']['mean_balance_k'].values[0]
bal_95 = outflow[outflow['age_group']=='95+']['mean_balance_k'].values[0]
check("balance 55-59 > balance 95+", bal_55 > bal_95, f"55-59=${bal_55:.0f}K, 95+=${bal_95:.0f}K")

# Ownership should be reasonable
own_65 = outflow[outflow['age_group']=='65-72']['ownership_pct'].values[0]
check("ownership 65-72 in 40-60%", 40 < own_65 < 60, f"got {own_65}%")

# TDF equity should be lower for older groups
tdf_55 = outflow[outflow['age_group']=='55-59']['tdf_us_equity_pct'].values[0]
tdf_85 = outflow[outflow['age_group']=='85-94']['tdf_us_equity_pct'].values[0]
check("TDF equity 55-59 > 85-94", tdf_55 > tdf_85, f"55-59={tdf_55}%, 85-94={tdf_85}%")

# ═════════════════════════════════════════════════════════════════════════
# 10. BUYBACK PARAMS
# ═════════════════════════════════════════════════════════════════════════
print("\n[10] Buyback parameters:")
bb = pd.read_csv(f'{PROC}\\buyback_params.csv')
bb_yield = bb.loc[bb['parameter']=='net_buyback_yield_mean', 'value'].values[0]
bb_std = bb.loc[bb['parameter']=='net_buyback_yield_std', 'value'].values[0]
check("buyback yield ~0.98%", 0.005 < bb_yield < 0.020, f"got {bb_yield*100:.2f}%")
check("buyback std ~0.72%", 0.003 < bb_std < 0.015, f"got {bb_std*100:.2f}%")

# ═════════════════════════════════════════════════════════════════════════
# 11. ARIMA FORECAST
# ═════════════════════════════════════════════════════════════════════════
print("\n[11] ARIMA passive share forecast:")
arima = pd.read_csv(f'{PROC}\\arima_passive_share_annual.csv')
check("26 rows", len(arima) == 26, f"got {len(arima)}")
check("starts 2025", arima.iloc[0]['year'] == 2025, f"got {arima.iloc[0]['year']}")
check("ends 2050", arima.iloc[-1]['year'] == 2050, f"got {arima.iloc[-1]['year']}")
check("2025 passive ~35-36%", 33 < arima.iloc[0]['cs_narrow_pct'] < 38, f"got {arima.iloc[0]['cs_narrow_pct']:.1f}%")
check("2050 passive >= 60%", arima.iloc[-1]['cs_narrow_pct'] >= 60, f"got {arima.iloc[-1]['cs_narrow_pct']:.1f}%")
check("monotonically increasing", all(arima['cs_narrow_pct'].iloc[i] <= arima['cs_narrow_pct'].iloc[i+1] for i in range(len(arima)-1)), "not monotonic!")
check("has CI columns", 'cs_upper_95' in arima.columns and 'cs_lower_95' in arima.columns, "missing CI columns")

# ═════════════════════════════════════════════════════════════════════════
# 12. SINGLE-PATH SMOKE TEST
# ═════════════════════════════════════════════════════════════════════════
print("\n[12] Simulation smoke test (deterministic path):")
arima['cs_sigma'] = (arima['cs_upper_95'] - arima['cs_lower_95']) / (2 * 1.96)

params = {
    'demo_scenario': 'mid', 'inflow_shock': 1.0, 'vol_multiplier': 1.0,
    'net_buyback_yield': bb_yield, 'M_base': 5.0, 'passive_z': 0.0,
    'returns': np.full(N_YEARS, 0.099), 'stress_year': None,
}
result = simulate_once(params, pop_matrices, inflow, outflow, arima)

check("inflow 2025 $200-350B", 200 < result['inflows'][0] < 350, f"got ${result['inflows'][0]:.1f}B")
check("outflow 2025 $100-300B", 100 < result['outflows'][0] < 300, f"got ${result['outflows'][0]:.1f}B")
check("net positive 2025", result['inflows'][0] - result['outflows'][0] > 0, f"net=${result['inflows'][0]-result['outflows'][0]:.1f}B")
check("no NaN in inflows", not np.any(np.isnan(result['inflows'])), "NaN!")
check("no NaN in outflows", not np.any(np.isnan(result['outflows'])), "NaN!")
check("no NaN in price_impact", not np.any(np.isnan(result['price_impact_pct'])), "NaN!")
check("no NaN in mktcap", not np.any(np.isnan(result['mktcap'])), "NaN!")
check("no NaN in buybacks", not np.any(np.isnan(result['buybacks'])), "NaN!")
check("all inflows > 0", np.all(result['inflows'] > 0), "negative inflow!")
check("all outflows > 0", np.all(result['outflows'] > 0), "negative outflow!")
check("all buybacks > 0", np.all(result['buybacks'] > 0), "negative buyback!")
check("mktcap > floor", np.all(result['mktcap'] >= 5000), f"min={result['mktcap'].min():.0f}")
check("multiplier range 4-10", result['multipliers'].min() >= 4 and result['multipliers'].max() <= 10, f"[{result['multipliers'].min():.1f}, {result['multipliers'].max():.1f}]")
check("inflows grow (wage growth)", result['inflows'][25] > result['inflows'][0] * 1.5, f"ratio={result['inflows'][25]/result['inflows'][0]:.2f}")
check("outflows grow (demographics)", result['outflows'][25] > result['outflows'][0] * 2.0, f"ratio={result['outflows'][25]/result['outflows'][0]:.2f}")

# DC feedback: net flows positive in 2025, so dc_return=0, mktcap grows at exactly r_t
expected_mc1 = result['mktcap'][0] * 1.099
check("DC feedback OFF when net>0", abs(result['mktcap'][1] - expected_mc1) < 1.0, f"diff={abs(result['mktcap'][1]-expected_mc1):.1f}")

# ═════════════════════════════════════════════════════════════════════════
# 13. BROADCAST VERIFICATION — scalar vs array must match
# ═════════════════════════════════════════════════════════════════════════
print("\n[13] Broadcast verification (scalar vs array):")
params_arr = params.copy()
params_arr['inflow_shock'] = np.full(N_YEARS, 1.0)
params_arr['vol_multiplier'] = np.full(N_YEARS, 1.0)
params_arr['net_buyback_yield'] = np.full(N_YEARS, bb_yield)
r2 = simulate_once(params_arr, pop_matrices, inflow, outflow, arima)

check("inflows match", np.allclose(result['inflows'], r2['inflows']), f"max diff={np.max(np.abs(result['inflows']-r2['inflows'])):.6f}")
check("outflows match", np.allclose(result['outflows'], r2['outflows']), f"max diff={np.max(np.abs(result['outflows']-r2['outflows'])):.6f}")
check("mktcap match", np.allclose(result['mktcap'], r2['mktcap']), f"max diff={np.max(np.abs(result['mktcap']-r2['mktcap'])):.6f}")
check("buybacks match", np.allclose(result['buybacks'], r2['buybacks']), f"max diff={np.max(np.abs(result['buybacks']-r2['buybacks'])):.6f}")

# ═════════════════════════════════════════════════════════════════════════
# 14. DC FEEDBACK ACTIVATION — must drag mktcap when flows negative
# ═════════════════════════════════════════════════════════════════════════
print("\n[14] DC feedback activation (forced negative flows):")
params_neg = {
    'demo_scenario': 'mid', 'inflow_shock': 0.7, 'vol_multiplier': 1.5,
    'net_buyback_yield': bb_yield, 'M_base': 5.0, 'passive_z': 0.0,
    'returns': np.full(N_YEARS, 0.04), 'stress_year': None,
}
r_neg = simulate_once(params_neg, pop_matrices, inflow, outflow, arima)
net_neg = r_neg['inflows'] - r_neg['outflows']
neg_idx = np.where(net_neg < 0)[0]
if len(neg_idx) > 0:
    t = neg_idx[0]
    check(f"negative flow found at {YEARS[t]}", True, f"net=${net_neg[t]:.1f}B")
    if t > 0:
        mc_no_fb = r_neg['mktcap'][t-1] * 1.04
        check(f"DC feedback drags mktcap at {YEARS[t]}", r_neg['mktcap'][t] < mc_no_fb,
              f"actual={r_neg['mktcap'][t]:.0f}, no-feedback={mc_no_fb:.0f}")
else:
    check("negative flow found", False, "none even with extreme params!")

# ═════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═════════════════════════════════════════════════════════════════════════
print(f"\n{'='*70}")
print(f"RESULTS: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("ALL CHECKS PASSED — safe to run model_runner.py")
else:
    print("FIX FAILURES BEFORE RUNNING")
    sys.exit(1)
print(f"{'='*70}")
