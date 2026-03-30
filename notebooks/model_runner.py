#!/usr/bin/env python3
"""
model_runner.py — Monte Carlo simulation runner for "The Demographic Tide"

Runs all computation:
  1. 25,000-path Monte Carlo simulation
  2. M=2 multiplier stress test
  3. 3x3 deterministic scenario table
  4. Crash stress test (-30% in 2030/2035/2040)
  5. TDF 30% equity sensitivity (5,000 paths)
  6. N1 outflow decomposition by age group

Saves ALL results to data/processed/mc_results.npz.
Run from notebooks/ directory:  python model_runner.py
"""

import os
import sys
import time
import importlib
import numpy as np
import pandas as pd

# Force-reload to avoid stale .pyc cache
import simulation_engine
importlib.reload(simulation_engine)
from simulation_engine import (
    INFLOW_AGE_MAP, OUTFLOW_AGE_MAP, get_age_pop, haddad_multiplier,
    simulate_once, YEARS, N_YEARS, PLAN_ACCESS, RECESSION_CUT_MOD,
    RECESSION_CUT_SEV, M_LOW, M_MID, M_HIGH, CHI, PASSIVE_2025,
    PASSIVE_CAP, MKTCAP_2025_B, TOTAL_EQUITY_SHARE, BOND_RETURN
)

print('=' * 70)
print('MODEL RUNNER — The Demographic Tide')
print('=' * 70)

# ═════════════════════════════════════════════════════════════════════════
# SECTION 1: DATA LOADING
# ═════════════════════════════════════════════════════════════════════════
PROC = r'..\data\processed'
OUT = r'..\outputs'
os.makedirs(OUT, exist_ok=True)

N_SIMS = 25000

# ── MC distribution parameters ──────────────────────────────────────────────
RETURN_MEAN_ARITH = 0.118  # Arithmetic mean (Damodaran, 1928-2024) — for Normal() MC draws
RETURN_MEAN_GEOM = 0.099   # Geometric mean (Damodaran, 1928-2024) — for deterministic paths
RETURN_VOL = 0.195        # Equity return std dev (Damodaran, 1928-2024: 19.5%)
INFLOW_SHOCK_STD = 0.07  # Inflow shock std dev (±2σ covers 0.86-1.14; Vanguard-ICI cross-validated <1%)
DEMO_WEIGHTS = [0.4, 0.3, 0.3]  # Census scenario probabilities (mid/hi/low)
BB_YIELD_FLOOR = 0.001   # Buyback yield lower bound
BB_YIELD_CEIL = 0.035    # Buyback yield upper bound
DEFAULT_CRASH_RETURN = -0.30  # Stress test crash magnitude

np.random.seed(42)

pop_matrices = {}
for scenario in ['mid', 'hi', 'low']:
    df = pd.read_csv(f'{PROC}\\pop_age_matrix_{scenario}.csv', index_col=0)
    df.columns = [int(c) for c in df.columns]
    df.index = [int(i) for i in df.index]
    pop_matrices[scenario] = df
print(f'Population matrices loaded: {list(pop_matrices.keys())}')

inflow_params = pd.read_csv(f'{PROC}\\module2_inflow_params.csv')
print(f'Inflow params: {len(inflow_params)} age groups')

outflow_params = pd.read_csv(f'{PROC}\\module3_outflow_params.csv')
print(f'Outflow params: {len(outflow_params)} age groups')

bb_params = pd.read_csv(f'{PROC}\\buyback_params.csv')
NET_BUYBACK_YIELD = bb_params.loc[bb_params['parameter'] == 'net_buyback_yield_mean', 'value'].values[0]
NET_BUYBACK_STD = bb_params.loc[bb_params['parameter'] == 'net_buyback_yield_std', 'value'].values[0]
print(f'Net buyback yield: {NET_BUYBACK_YIELD*100:.2f}% +/- {NET_BUYBACK_STD*100:.2f}%')

arima = pd.read_csv(f'{PROC}\\arima_passive_share_annual.csv')
arima['cs_sigma'] = (arima['cs_upper_95'] - arima['cs_lower_95']) / (2 * 1.96)
print(f'ARIMA forecast: {len(arima)} years')

try:
    reg = pd.read_csv(f'{PROC}\\regression_output.csv')
    BETA_POP65 = reg['beta_pop_65plus'].values[0]
    print(f'Regression beta: {BETA_POP65:.3f} (validation only)')
except FileNotFoundError:
    BETA_POP65 = None
    print('Regression output not found (not required)')

print(f'\nAll data loaded.\n')

# ═════════════════════════════════════════════════════════════════════════
# SECTION 2: MONTE CARLO (25,000 paths)
# ═════════════════════════════════════════════════════════════════════════
t0 = time.time()
print(f'Running {N_SIMS:,} Monte Carlo simulations...')

mc_inflows = np.zeros((N_SIMS, N_YEARS))
mc_outflows = np.zeros((N_SIMS, N_YEARS))
mc_net_demo = np.zeros((N_SIMS, N_YEARS))
mc_net_total = np.zeros((N_SIMS, N_YEARS))
mc_buybacks = np.zeros((N_SIMS, N_YEARS))
mc_multipliers = np.zeros((N_SIMS, N_YEARS))
mc_passive = np.zeros((N_SIMS, N_YEARS))
mc_price_impact = np.zeros((N_SIMS, N_YEARS))
mc_mktcap = np.zeros((N_SIMS, N_YEARS))
mc_crossover_demo = np.zeros(N_SIMS)
mc_crossover_total = np.zeros(N_SIMS)

DEMO_LABELS = ['mid', 'hi', 'low']
demo_choices_str = np.random.choice(DEMO_LABELS, size=N_SIMS, p=DEMO_WEIGHTS)
demo_choices_int = np.array([DEMO_LABELS.index(d) for d in demo_choices_str])

for i in range(N_SIMS):
    params = {
        'demo_scenario': demo_choices_str[i],
        'inflow_shock': np.random.normal(1.0, INFLOW_SHOCK_STD, size=N_YEARS),
        'vol_multiplier': np.random.uniform(0.5, 1.5, size=N_YEARS),
        'net_buyback_yield': np.clip(np.random.normal(NET_BUYBACK_YIELD, NET_BUYBACK_STD, size=N_YEARS), BB_YIELD_FLOOR, BB_YIELD_CEIL),
        'M_base': np.random.uniform(M_LOW, M_HIGH),
        'passive_z': np.random.normal(0, 1),
        'returns': np.random.normal(RETURN_MEAN_ARITH, RETURN_VOL, size=N_YEARS),
        'stress_year': None,
    }
    result = simulate_once(params, pop_matrices, inflow_params, outflow_params, arima)

    mc_inflows[i] = result['inflows']
    mc_outflows[i] = result['outflows']
    mc_net_demo[i] = result['net_demo']
    mc_net_total[i] = result['net_total']
    mc_buybacks[i] = result['buybacks']
    mc_multipliers[i] = result['multipliers']
    mc_passive[i] = result['passive_path']
    mc_price_impact[i] = result['price_impact_pct']
    mc_mktcap[i] = result['mktcap']
    mc_crossover_demo[i] = result['crossover_demo']
    mc_crossover_total[i] = result['crossover_total']

    if (i + 1) % 10000 == 0:
        print(f'  {i+1:,}/{N_SIMS:,} complete...')

t_mc = time.time() - t0
print(f'\n  MC complete in {t_mc:.0f}s')
print(f'  Median inflow 2025:  ${np.median(mc_inflows[:, 0]):,.1f}B')
print(f'  Median outflow 2025: ${np.median(mc_outflows[:, 0]):,.1f}B')
print(f'  Median net 2025:     ${np.median(mc_net_demo[:, 0]):,.1f}B')

# ═════════════════════════════════════════════════════════════════════════
# SECTION 3: M=2 STRESS TEST
# ═════════════════════════════════════════════════════════════════════════
print(f'\nComputing M=2 stress test...')
M_STRESS = 2
mc_pi_m2 = np.zeros_like(mc_net_demo)
for t in range(N_YEARS):
    mktcap_t = np.median(mc_mktcap[:, t])
    mc_pi_m2[:, t] = (mc_net_demo[:, t] * M_STRESS / mktcap_t) * 100
print(f'  M=5 median 2050: {np.median(mc_price_impact[:, 25]):.3f}%')
print(f'  M=2 median 2050: {np.median(mc_pi_m2[:, 25]):.3f}%')

# ═════════════════════════════════════════════════════════════════════════
# SECTION 4: 3x3 SCENARIO TABLE
# ═════════════════════════════════════════════════════════════════════════
print(f'\nRunning 3x3 scenario table...')
det_params_base = {
    'demo_scenario': 'mid', 'inflow_shock': 1.0, 'vol_multiplier': 1.0,
    'net_buyback_yield': NET_BUYBACK_YIELD,
    'returns': np.full(N_YEARS, RETURN_MEAN_GEOM), 'stress_year': None,
}

M_vals = [3, 5, 7]
P_growths = [1.0, 1.4, 1.8]
scenario_crossovers = np.zeros(9)
scenario_net_2035 = np.zeros(9)
scenario_net_2050 = np.zeros(9)
scenario_impact_2050 = np.zeros(9)

idx = 0
for m_val in M_vals:
    for p_growth in P_growths:
        passive_manual = np.minimum(PASSIVE_2025 + p_growth * (YEARS - 2025), PASSIVE_CAP)
        arima_det = pd.DataFrame({
            'year': YEARS, 'cs_narrow_pct': passive_manual,
            'cs_sigma': np.zeros(N_YEARS),
        })
        params = det_params_base.copy()
        params['M_base'] = m_val
        params['passive_z'] = 0.0
        result = simulate_once(params, pop_matrices, inflow_params, outflow_params, arima_det)
        scenario_crossovers[idx] = result['crossover_demo']
        scenario_net_2035[idx] = result['net_demo'][10]
        scenario_net_2050[idx] = result['net_demo'][25]
        scenario_impact_2050[idx] = result['price_impact_pct'][25]
        idx += 1
print(f'  9 scenarios complete')

# ═════════════════════════════════════════════════════════════════════════
# SECTION 5: CRASH STRESS TEST
# ═════════════════════════════════════════════════════════════════════════
print(f'\nRunning crash stress tests...')
baseline_params = det_params_base.copy()
baseline_params['M_base'] = 5.0
baseline_params['passive_z'] = 0.0
baseline_result = simulate_once(baseline_params, pop_matrices, inflow_params, outflow_params, arima)
stress_baseline_net = baseline_result['net_demo']

stress_years = [2030, 2035, 2040]
stress_net = np.zeros((3, N_YEARS))
for j, s_year in enumerate(stress_years):
    sp = baseline_params.copy()
    sp['stress_year'] = s_year
    sp['stress_return'] = DEFAULT_CRASH_RETURN
    sr = simulate_once(sp, pop_matrices, inflow_params, outflow_params, arima)
    stress_net[j] = sr['net_demo']
print(f'  3 crash scenarios complete')

# ═════════════════════════════════════════════════════════════════════════
# SECTION 6: TDF EQUITY SENSITIVITY (36% double-TDF + 52% observed)
# ═════════════════════════════════════════════════════════════════════════
# Exponential decay over 20 years (2025–2045): self-directed retirees
# gradually replaced by TDF cohorts. Same random draws for all three
# scenarios (base, 36%, 52%) = proper paired comparison.
print(f'\nRunning TDF sensitivity (10,000 paths × 3 scenarios)...')
N_SENS = 10000
np.random.seed(99)

TDF_GROUPS = ['65-72', '73-74', '75-84', '85-94', '95+']

tdf_override_36 = {
    'start': 2025, 'end': 2045,
    'groups': TDF_GROUPS,
    'equity_pct': 36.0,   # Double TDF allocation
}

tdf_override_52 = {
    'start': 2025, 'end': 2045,
    'groups': TDF_GROUPS,
    'equity_pct': 52.0,   # Vanguard observed allocation (ages 65-69)
}

tdf_cross_base = np.zeros(N_SENS)
tdf_cross_sens_36 = np.zeros(N_SENS)
tdf_cross_sens_52 = np.zeros(N_SENS)
tdf_base_outflows = np.zeros((N_SENS, N_YEARS))
tdf_base_inflows = np.zeros((N_SENS, N_YEARS))
tdf_sens_outflows_36 = np.zeros((N_SENS, N_YEARS))
tdf_sens_outflows_52 = np.zeros((N_SENS, N_YEARS))

for i in range(N_SENS):
    base_p = {
        'demo_scenario': np.random.choice(DEMO_LABELS, p=DEMO_WEIGHTS),
        'inflow_shock': np.random.normal(1.0, INFLOW_SHOCK_STD, size=N_YEARS),
        'vol_multiplier': np.random.uniform(0.5, 1.5, size=N_YEARS),
        'net_buyback_yield': np.clip(np.random.normal(NET_BUYBACK_YIELD, NET_BUYBACK_STD, size=N_YEARS), BB_YIELD_FLOOR, BB_YIELD_CEIL),
        'M_base': np.random.uniform(M_LOW, M_HIGH),
        'passive_z': np.random.normal(0, 1),
        'returns': np.random.normal(RETURN_MEAN_ARITH, RETURN_VOL, size=N_YEARS),
        'stress_year': None,
    }

    # Base (TDF allocation, no override)
    r_base = simulate_once(base_p, pop_matrices, inflow_params, outflow_params, arima)
    tdf_base_outflows[i] = r_base['outflows']
    tdf_base_inflows[i] = r_base['inflows']

    net_base = r_base['inflows'] - r_base['outflows']
    cross_b = np.where(net_base < 0)[0]
    tdf_cross_base[i] = YEARS[cross_b[0]] if len(cross_b) > 0 else 2099

    # 36% sensitivity (double TDF)
    sens_36_p = base_p.copy()
    sens_36_p['tdf_override'] = tdf_override_36
    r_36 = simulate_once(sens_36_p, pop_matrices, inflow_params, outflow_params, arima)
    tdf_sens_outflows_36[i] = r_36['outflows']

    net_36 = r_base['inflows'] - r_36['outflows']
    cross_36 = np.where(net_36 < 0)[0]
    tdf_cross_sens_36[i] = YEARS[cross_36[0]] if len(cross_36) > 0 else 2099

    # 52% sensitivity (Vanguard observed)
    sens_52_p = base_p.copy()
    sens_52_p['tdf_override'] = tdf_override_52
    r_52 = simulate_once(sens_52_p, pop_matrices, inflow_params, outflow_params, arima)
    tdf_sens_outflows_52[i] = r_52['outflows']

    net_52 = r_base['inflows'] - r_52['outflows']
    cross_52 = np.where(net_52 < 0)[0]
    tdf_cross_sens_52[i] = YEARS[cross_52[0]] if len(cross_52) > 0 else 2099

    if (i + 1) % 2500 == 0:
        print(f'  {i+1:,}/{N_SENS:,} complete...')

# Summary
for label, cross_arr in [('Base (18%)', tdf_cross_base),
                          ('36% (2×TDF)', tdf_cross_sens_36),
                          ('52% (observed)', tdf_cross_sens_52)]:
    valid = cross_arr[cross_arr < 2099]
    prob = (cross_arr < 2099).sum() / N_SENS * 100
    med = int(np.median(valid)) if len(valid) > 0 else 'N/A'
    print(f'  {label}: prob={prob:.1f}%, median={med}')
print(f'  TDF sensitivity complete')

# ═════════════════════════════════════════════════════════════════════════
# SECTION 7: N1 OUTFLOW DECOMPOSITION
# ═════════════════════════════════════════════════════════════════════════
print(f'\nComputing outflow decomposition...')
pop = pop_matrices['mid']
balances_n1 = outflow_params['mean_balance_k'].values.copy().astype(float)
outflow_by_group = np.zeros((len(outflow_params), N_YEARS))

# Per-group blended return (equity × RETURN_MEAN_GEOM + bond × BOND_RETURN)
n1_blended = {}
for _, orow in outflow_params.iterrows():
    ag = orow['age_group']
    eq = TOTAL_EQUITY_SHARE.get(ag, 0.30)
    n1_blended[ag] = eq * RETURN_MEAN_GEOM + (1 - eq) * BOND_RETURN

for t, yr in enumerate(YEARS):
    pop_yr = pop.loc[yr] if yr in pop.index else pop.iloc[-1]
    for j, orow in outflow_params.iterrows():
        ag = orow['age_group']
        ages = OUTFLOW_AGE_MAP[ag]
        age_pop = get_age_pop(pop_yr, ages)
        ownership = orow['ownership_pct'] / 100
        rmd_rate = orow['rmd_rate_pct'] / 100
        vol_rate = orow['voluntary_rate_pct'] / 100
        tdf_equity = orow['tdf_us_equity_pct'] / 100
        eff_rate = max(rmd_rate, vol_rate)
        withdrawal_k = balances_n1[j] * eff_rate
        equity_per_person_B = (withdrawal_k * tdf_equity) / 1e6
        outflow_by_group[j, t] = age_pop * ownership * equity_per_person_B
    for j, orow in outflow_params.iterrows():
        ag = orow['age_group']
        rmd_rate = orow['rmd_rate_pct'] / 100
        vol_rate = orow['voluntary_rate_pct'] / 100
        eff_rate = max(rmd_rate, vol_rate)
        balances_n1[j] = balances_n1[j] * (1 + n1_blended[ag]) * (1 - eff_rate)

# Balance snapshots
balances_n2 = outflow_params['mean_balance_k'].values.copy().astype(float)
bal_2025 = balances_n2.copy()
bal_2035 = None
bal_2050 = None
for t, yr in enumerate(YEARS):
    if yr == 2035: bal_2035 = balances_n2.copy()
    if yr == 2050: bal_2050 = balances_n2.copy()
    for j, orow in outflow_params.iterrows():
        ag = orow['age_group']
        rmd_rate = orow['rmd_rate_pct'] / 100
        vol_rate = orow['voluntary_rate_pct'] / 100
        eff_rate = max(rmd_rate, vol_rate)
        balances_n2[j] = balances_n2[j] * (1 + n1_blended[ag]) * (1 - eff_rate)
if bal_2050 is None: bal_2050 = balances_n2.copy()
balance_snapshots = np.stack([bal_2025, bal_2035, bal_2050])

print(f'  Decomposition complete')

# ═════════════════════════════════════════════════════════════════════════
# SECTION 8: SAVE TO NPZ
# ═════════════════════════════════════════════════════════════════════════
save_path = f'{PROC}\\mc_results.npz'
print(f'\nSaving to {save_path}...')

np.savez(save_path,
    mc_inflows=mc_inflows, mc_outflows=mc_outflows,
    mc_net_demo=mc_net_demo, mc_net_total=mc_net_total,
    mc_buybacks=mc_buybacks, mc_multipliers=mc_multipliers,
    mc_passive=mc_passive, mc_price_impact=mc_price_impact,
    mc_mktcap=mc_mktcap, mc_crossover_demo=mc_crossover_demo,
    mc_crossover_total=mc_crossover_total, demo_choices=demo_choices_int,
    mc_pi_m2=mc_pi_m2,
    scenario_crossovers=scenario_crossovers, scenario_net_2035=scenario_net_2035,
    scenario_net_2050=scenario_net_2050, scenario_impact_2050=scenario_impact_2050,
    stress_baseline_net=stress_baseline_net, stress_net=stress_net,
    tdf_cross_base=tdf_cross_base,
    tdf_cross_sens_36=tdf_cross_sens_36, tdf_sens_outflows_36=tdf_sens_outflows_36,
    tdf_cross_sens_52=tdf_cross_sens_52, tdf_sens_outflows_52=tdf_sens_outflows_52,
    tdf_base_outflows=tdf_base_outflows, tdf_base_inflows=tdf_base_inflows,
    outflow_by_group=outflow_by_group, balance_snapshots=balance_snapshots,
)

# ═════════════════════════════════════════════════════════════════════════
# SECTION 9: VERIFY
# ═════════════════════════════════════════════════════════════════════════
data = np.load(save_path)
EXPECTED = {
    'mc_inflows': (N_SIMS, N_YEARS), 'mc_outflows': (N_SIMS, N_YEARS),
    'mc_net_demo': (N_SIMS, N_YEARS), 'mc_net_total': (N_SIMS, N_YEARS),
    'mc_buybacks': (N_SIMS, N_YEARS), 'mc_multipliers': (N_SIMS, N_YEARS),
    'mc_passive': (N_SIMS, N_YEARS), 'mc_price_impact': (N_SIMS, N_YEARS),
    'mc_mktcap': (N_SIMS, N_YEARS), 'mc_crossover_demo': (N_SIMS,),
    'mc_crossover_total': (N_SIMS,), 'demo_choices': (N_SIMS,),
    'mc_pi_m2': (N_SIMS, N_YEARS),
    'scenario_crossovers': (9,), 'scenario_net_2035': (9,),
    'scenario_net_2050': (9,), 'scenario_impact_2050': (9,),
    'stress_baseline_net': (N_YEARS,), 'stress_net': (3, N_YEARS),
    'tdf_cross_base': (N_SENS,),
    'tdf_cross_sens_36': (N_SENS,), 'tdf_sens_outflows_36': (N_SENS, N_YEARS),
    'tdf_cross_sens_52': (N_SENS,), 'tdf_sens_outflows_52': (N_SENS, N_YEARS),
    'tdf_base_outflows': (N_SENS, N_YEARS), 'tdf_base_inflows': (N_SENS, N_YEARS),
    'outflow_by_group': (len(outflow_params), N_YEARS),
    'balance_snapshots': (3, len(outflow_params)),
}

print(f'\nVerification — {len(data.files)} arrays:')
all_ok = True
for key, shape in EXPECTED.items():
    if key not in data:
        print(f'  MISSING: {key}')
        all_ok = False
    elif data[key].shape != shape:
        print(f'  WRONG SHAPE: {key} expected {shape} got {data[key].shape}')
        all_ok = False
    else:
        print(f'  OK: {key} {shape}')

if not all_ok:
    print('\nVERIFICATION FAILED')
    sys.exit(1)

# Key results
cross_prob = (mc_crossover_demo < 2099).sum() / N_SIMS * 100
valid_cross = mc_crossover_demo[mc_crossover_demo < 2099]
cross_total_prob = (mc_crossover_total < 2099).sum() / N_SIMS * 100
valid_total = mc_crossover_total[mc_crossover_total < 2099]

print(f'\n{"="*70}')
print('KEY RESULTS')
print(f'{"="*70}')
print(f'  Crossover prob (demo):    {cross_prob:.1f}%')
print(f'  Median crossover (demo):  {int(np.median(valid_cross))}')
print(f'  Crossover prob (total):   {cross_total_prob:.1f}%')
print(f'  Median crossover (total): {int(np.median(valid_total)) if len(valid_total) > 0 else "N/A"}')
print(f'  Price impact 2050:        {np.median(mc_price_impact[:, 25]):.3f}%')
print(f'  Total runtime:            {time.time()-t0:.0f}s')
print(f'\nDone. Run model_visualisation.ipynb to generate figures.')

