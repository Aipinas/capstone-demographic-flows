#!/usr/bin/env python3
"""
sobol_runner.py — Sobol sensitivity analysis for "The Demographic Tide"

Runs:
  1. Overall 7-parameter Sobol (crossover + net flow + price impact)
  2. 32-parameter Sobol (individual annual returns)
  3. Conditional 6-parameter Sobol (return fixed at 9.9%)

Saves ALL results to data/processed/sobol_results.npz.
Run from notebooks/ directory:  python sobol_runner.py
"""

import time
import importlib
import numpy as np
import pandas as pd
from SALib.sample import sobol as sobol_sample
from SALib.analyze import sobol as sobol_analyze

import simulation_engine
importlib.reload(simulation_engine)
from simulation_engine import (
    INFLOW_AGE_MAP, OUTFLOW_AGE_MAP, get_age_pop, haddad_multiplier,
    simulate_once, YEARS, N_YEARS, PLAN_ACCESS, M_LOW, M_HIGH, CHI,
    PASSIVE_2025, PASSIVE_CAP, MKTCAP_2025_B
)

print('=' * 70)
print('SOBOL RUNNER — The Demographic Tide')
print('=' * 70)

# ═════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═════════════════════════════════════════════════════════════════════════
PROC = r'..\data\processed'
np.random.seed(42)
N_SOBOL = 2048
HORIZON_YEARS = [2030, 2040, 2050]
HORIZON_IDXS = {yr: yr - 2025 for yr in HORIZON_YEARS}

pop_matrices = {}
for scenario in ['mid', 'hi', 'low']:
    df = pd.read_csv(f'{PROC}\\pop_age_matrix_{scenario}.csv', index_col=0)
    df.columns = [int(c) for c in df.columns]
    df.index = [int(i) for i in df.index]
    pop_matrices[scenario] = df

inflow_params = pd.read_csv(f'{PROC}\\module2_inflow_params.csv')
outflow_params = pd.read_csv(f'{PROC}\\module3_outflow_params.csv')

bb_params = pd.read_csv(f'{PROC}\\buyback_params.csv')
NET_BUYBACK_YIELD = bb_params.loc[bb_params['parameter'] == 'net_buyback_yield_mean', 'value'].values[0]

arima = pd.read_csv(f'{PROC}\\arima_passive_share_annual.csv')
arima['cs_sigma'] = (arima['cs_upper_95'] - arima['cs_lower_95']) / (2 * 1.96)

print(f'Data loaded. N_SOBOL = {N_SOBOL}')
t0 = time.time()

# ═════════════════════════════════════════════════════════════════════════
# SECTION 1: OVERALL 7-PARAMETER SOBOL
# ═════════════════════════════════════════════════════════════════════════
print(f'\n{"="*70}')
print('OVERALL SOBOL — 7 parameters')
print(f'{"="*70}')

problem = {
    'num_vars': 7,
    'names': ['demo_u', 'inflow_shock', 'vol_multiplier',
              'net_buyback_yield', 'M_base', 'passive_z', 'annual_return'],
    'bounds': [
        [0.0, 1.0], [0.86, 1.14], [0.50, 1.50],
        [0.001, 0.035], [3.0, 7.0], [-2.0, 2.0], [0.00, 0.20],
    ]
}

param_values = sobol_sample.sample(problem, N_SOBOL, calc_second_order=False)
n_evals = param_values.shape[0]
print(f'Evaluations: {n_evals:,}')

Y_crossover = np.zeros(n_evals)
Y_netflow = {yr: np.zeros(n_evals) for yr in HORIZON_YEARS}
Y_pi = {yr: np.zeros(n_evals) for yr in HORIZON_YEARS}

for i in range(n_evals):
    X = param_values[i]
    demo = 'mid' if X[0] < 0.4 else ('hi' if X[0] < 0.7 else 'low')
    params = {
        'demo_scenario': demo, 'inflow_shock': X[1], 'vol_multiplier': X[2],
        'net_buyback_yield': X[3], 'M_base': X[4], 'passive_z': X[5],
        'returns': np.full(N_YEARS, X[6]), 'stress_year': None,
    }
    result = simulate_once(params, pop_matrices, inflow_params, outflow_params, arima)
    Y_crossover[i] = result['crossover_demo']
    for yr in HORIZON_YEARS:
        Y_netflow[yr][i] = result['net_demo'][HORIZON_IDXS[yr]]
        Y_pi[yr][i] = result['price_impact_pct'][HORIZON_IDXS[yr]]
    if (i + 1) % 5000 == 0:
        print(f'  {i+1:,}/{n_evals:,}...')

t1 = time.time()
print(f'  Complete in {t1-t0:.0f}s')

Si_cross = sobol_analyze.analyze(problem, Y_crossover, calc_second_order=False, print_to_console=False)
Si_nf = {}
Si_pi_all = {}
for yr in HORIZON_YEARS:
    Si_nf[yr] = sobol_analyze.analyze(problem, Y_netflow[yr], calc_second_order=False, print_to_console=False)
    Si_pi_all[yr] = sobol_analyze.analyze(problem, Y_pi[yr], calc_second_order=False, print_to_console=False)
    print(f'  NF {yr}: return ST={Si_nf[yr]["ST"][-1]:.3f}')

# ═════════════════════════════════════════════════════════════════════════
# SECTION 2: 32-PARAMETER SOBOL
# ═════════════════════════════════════════════════════════════════════════
print(f'\n{"="*70}')
print('32-PARAMETER SOBOL')
print(f'{"="*70}')

problem_32 = {
    'num_vars': 32,
    'names': [f'return_{yr}' for yr in range(2025, 2051)] +
             ['inflow_shock', 'vol_multiplier', 'net_buyback_yield',
              'M_base', 'passive_z', 'demo_u'],
    'bounds': [[-0.30, 0.50]] * 26 +
              [[0.86, 1.14], [0.50, 1.50], [0.001, 0.035],
               [3.0, 7.0], [-2.0, 2.0], [0.0, 1.0]],
}

param_values_32 = sobol_sample.sample(problem_32, N_SOBOL, calc_second_order=False)
n_evals_32 = param_values_32.shape[0]
print(f'Evaluations: {n_evals_32:,}')

Y_nf_32 = {yr: np.zeros(n_evals_32) for yr in HORIZON_YEARS}

t2 = time.time()
for i in range(n_evals_32):
    X = param_values_32[i]
    demo = 'mid' if X[31] < 0.4 else ('hi' if X[31] < 0.7 else 'low')
    params = {
        'demo_scenario': demo, 'inflow_shock': X[26], 'vol_multiplier': X[27],
        'net_buyback_yield': X[28], 'M_base': X[29], 'passive_z': X[30],
        'returns': X[:26], 'stress_year': None,
    }
    result = simulate_once(params, pop_matrices, inflow_params, outflow_params, arima)
    for yr in HORIZON_YEARS:
        Y_nf_32[yr][i] = result['net_demo'][HORIZON_IDXS[yr]]
    if (i + 1) % 20000 == 0:
        print(f'  {i+1:,}/{n_evals_32:,}...')

t3 = time.time()
print(f'  Complete in {t3-t2:.0f}s')

Si_32 = {}
for yr in HORIZON_YEARS:
    Si_32[yr] = sobol_analyze.analyze(problem_32, Y_nf_32[yr], calc_second_order=False, print_to_console=False)
    print(f'  {yr}: agg return ST={Si_32[yr]["ST"][:26].sum():.3f}')

# ═════════════════════════════════════════════════════════════════════════
# SECTION 3: CONDITIONAL 6-PARAMETER SOBOL
# ═════════════════════════════════════════════════════════════════════════
print(f'\n{"="*70}')
print('CONDITIONAL SOBOL — return fixed at 9.9%')
print(f'{"="*70}')

FIXED_RETURN = 0.099
problem_cond = {
    'num_vars': 6,
    'names': ['demo_u', 'inflow_shock', 'vol_multiplier',
              'net_buyback_yield', 'M_base', 'passive_z'],
    'bounds': [
        [0.0, 1.0], [0.86, 1.14], [0.50, 1.50],
        [0.001, 0.035], [3.0, 7.0], [-2.0, 2.0],
    ]
}

param_values_cond = sobol_sample.sample(problem_cond, N_SOBOL, calc_second_order=False)
n_evals_cond = param_values_cond.shape[0]
print(f'Evaluations: {n_evals_cond:,}')

Y_cross_cond = np.zeros(n_evals_cond)
Y_nf_cond = {yr: np.zeros(n_evals_cond) for yr in HORIZON_YEARS}

t4 = time.time()
for i in range(n_evals_cond):
    X = param_values_cond[i]
    demo = 'mid' if X[0] < 0.4 else ('hi' if X[0] < 0.7 else 'low')
    params = {
        'demo_scenario': demo, 'inflow_shock': X[1], 'vol_multiplier': X[2],
        'net_buyback_yield': X[3], 'M_base': X[4], 'passive_z': X[5],
        'returns': np.full(N_YEARS, FIXED_RETURN), 'stress_year': None,
    }
    result = simulate_once(params, pop_matrices, inflow_params, outflow_params, arima)
    Y_cross_cond[i] = result['crossover_demo']
    for yr in HORIZON_YEARS:
        Y_nf_cond[yr][i] = result['net_demo'][HORIZON_IDXS[yr]]
    if (i + 1) % 5000 == 0:
        print(f'  {i+1:,}/{n_evals_cond:,}...')

t5 = time.time()
print(f'  Complete in {t5-t4:.0f}s')

Si_cond_cross = sobol_analyze.analyze(problem_cond, Y_cross_cond, calc_second_order=False, print_to_console=False)
Si_cond_nf = {}
for yr in HORIZON_YEARS:
    Si_cond_nf[yr] = sobol_analyze.analyze(problem_cond, Y_nf_cond[yr], calc_second_order=False, print_to_console=False)

# ═════════════════════════════════════════════════════════════════════════
# SECTION 4: 57-PARAMETER SOBOL (per-year returns + per-year vol_multiplier)
# ═════════════════════════════════════════════════════════════════════════
# Tests whether "return dominates" is an artefact of returns being the only
# per-year parameter. Gives vol_multiplier the same temporal resolution.
# If returns still dominate, the finding is structural, not design-driven.
# Bounds: returns from Damodaran mean ± 2σ (0.118 ± 2×0.195 = [-0.27, 0.51])
#         vol_multiplier [0.50, 1.50] same as 7-parameter analysis.
print(f'\n{"="*70}')
print('57-PARAMETER SOBOL — per-year returns + per-year vol_multiplier')
print(f'{"="*70}')

RET_LO = -0.27   # Damodaran arith mean - 2σ: 0.118 - 2×0.195
RET_HI = 0.51    # Damodaran arith mean + 2σ: 0.118 + 2×0.195

problem_57 = {
    'num_vars': 57,
    'names': ([f'return_{yr}' for yr in range(2025, 2051)] +
              [f'vol_mult_{yr}' for yr in range(2025, 2051)] +
              ['inflow_shock', 'net_buyback_yield', 'M_base',
               'passive_z', 'demo_u']),
    'bounds': ([[RET_LO, RET_HI]] * 26 +
               [[0.50, 1.50]] * 26 +
               [[0.86, 1.14], [0.001, 0.035], [3.0, 7.0],
                [-2.0, 2.0], [0.0, 1.0]]),
}

N_SOBOL_57 = 2048
param_values_57 = sobol_sample.sample(problem_57, N_SOBOL_57, calc_second_order=False)
n_evals_57 = param_values_57.shape[0]
print(f'Evaluations: {n_evals_57:,}')

Y_nf_57 = {yr: np.zeros(n_evals_57) for yr in HORIZON_YEARS}

t6 = time.time()
for i in range(n_evals_57):
    X = param_values_57[i]
    demo = 'mid' if X[56] < 0.4 else ('hi' if X[56] < 0.7 else 'low')
    params = {
        'demo_scenario': demo,
        'inflow_shock': X[52],           # scalar → broadcast to constant
        'vol_multiplier': X[26:52],      # 26-element array → per-year
        'net_buyback_yield': X[53],      # scalar → broadcast to constant
        'M_base': X[54],
        'passive_z': X[55],
        'returns': X[:26],               # 26-element array → per-year
        'stress_year': None,
    }
    result = simulate_once(params, pop_matrices, inflow_params, outflow_params, arima)
    for yr in HORIZON_YEARS:
        Y_nf_57[yr][i] = result['net_demo'][HORIZON_IDXS[yr]]
    if (i + 1) % 20000 == 0:
        print(f'  {i+1:,}/{n_evals_57:,}...')

t7 = time.time()
print(f'  Complete in {t7-t6:.0f}s')

Si_57 = {}
for yr in HORIZON_YEARS:
    Si_57[yr] = sobol_analyze.analyze(problem_57, Y_nf_57[yr], calc_second_order=False, print_to_console=False)
    agg_ret_ST = Si_57[yr]['ST'][:26].sum()
    agg_vol_ST = Si_57[yr]['ST'][26:52].sum()
    inflow_ST = Si_57[yr]['ST'][52]
    print(f'  {yr}: agg return ST={agg_ret_ST:.3f}, agg vol_mult ST={agg_vol_ST:.3f}, inflow ST={inflow_ST:.3f}')

# ═════════════════════════════════════════════════════════════════════════
# SAVE
# ═════════════════════════════════════════════════════════════════════════
save_path = f'{PROC}\\sobol_results.npz'
print(f'\nSaving to {save_path}...')

save_dict = {}
save_dict['overall_cross_S1'] = Si_cross['S1']
save_dict['overall_cross_ST'] = Si_cross['ST']
save_dict['overall_cross_S1_conf'] = Si_cross['S1_conf']
save_dict['overall_cross_ST_conf'] = Si_cross['ST_conf']

for yr in HORIZON_YEARS:
    for metric, si_dict in [('nf', Si_nf), ('pi', Si_pi_all)]:
        si = si_dict[yr]
        save_dict[f'overall_{metric}_{yr}_S1'] = si['S1']
        save_dict[f'overall_{metric}_{yr}_ST'] = si['ST']
        save_dict[f'overall_{metric}_{yr}_S1_conf'] = si['S1_conf']
        save_dict[f'overall_{metric}_{yr}_ST_conf'] = si['ST_conf']

for yr in HORIZON_YEARS:
    si = Si_32[yr]
    save_dict[f'full32_nf_{yr}_S1'] = si['S1']
    save_dict[f'full32_nf_{yr}_ST'] = si['ST']
    save_dict[f'full32_nf_{yr}_S1_conf'] = si['S1_conf']
    save_dict[f'full32_nf_{yr}_ST_conf'] = si['ST_conf']

save_dict['cond_cross_S1'] = Si_cond_cross['S1']
save_dict['cond_cross_ST'] = Si_cond_cross['ST']
save_dict['cond_cross_S1_conf'] = Si_cond_cross['S1_conf']
save_dict['cond_cross_ST_conf'] = Si_cond_cross['ST_conf']

for yr in HORIZON_YEARS:
    si = Si_cond_nf[yr]
    save_dict[f'cond_nf_{yr}_S1'] = si['S1']
    save_dict[f'cond_nf_{yr}_ST'] = si['ST']
    save_dict[f'cond_nf_{yr}_S1_conf'] = si['S1_conf']
    save_dict[f'cond_nf_{yr}_ST_conf'] = si['ST_conf']

for yr in HORIZON_YEARS:
    si = Si_57[yr]
    save_dict[f'full57_nf_{yr}_S1'] = si['S1']
    save_dict[f'full57_nf_{yr}_ST'] = si['ST']
    save_dict[f'full57_nf_{yr}_S1_conf'] = si['S1_conf']
    save_dict[f'full57_nf_{yr}_ST_conf'] = si['ST_conf']

np.savez(save_path, **save_dict)

# Verify
data = np.load(save_path)
print(f'Saved {len(data.files)} arrays')
for key in sorted(data.files):
    print(f'  {key}: {data[key].shape}')

print(f'\nTotal runtime: {time.time()-t0:.0f}s')
print(f'Done. Run sobol_visualisation.ipynb to generate figures.')
