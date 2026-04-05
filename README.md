# The Demographic Tide

**Retirement Flows and Price Impact in an Inelastic Equity Market**

BDBA Capstone Thesis — IE University, School of Science & Technology

Antonio de Ipiña Sanchez | Supervised by Prof. Manuele Leonelli

## Overview

This repository contains the data, code, and outputs for a study projecting when U.S. defined-contribution (DC) retirement account outflows will overtake inflows into passive equity index funds, and what the resulting price impact looks like from 2025 to 2050. The model combines cohort-level retirement flow accounting with the Gabaix-Koijen inelastic markets multiplier, the Haddad et al. time-varying pass-through, and global Sobol sensitivity analysis into a single five-module projection framework.

Across 25,000 Monte Carlo paths, the median demographic net flow trajectory crosses zero between 2040 and 2041. The annual price drag reaches −0.11% of market capitalisation by 2050. Including corporate buybacks, total net flows remain positive in 95.5% of simulations.

## Repository Structure

```
capstone-demographic-flows/
├── notebooks/
│   ├── simulation_engine.py      # Shared simulation module (constants, age mappings, simulate_once)
│   ├── model_runner.py           # Monte Carlo runner (25,000 paths, stress tests, sensitivity)
│   ├── sobol_runner.py           # Sobol variance decomposition (7/32/57-param + conditional)
│   ├── verify_data.py            # Data verification utilities
│   ├── 01_data_exploration.ipynb # Data loading, cleaning, and exploratory analysis
│   ├── 02_arima.ipynb            # ARIMA(0,1,0) passive share forecasting
│   ├── 03_regression.ipynb       # OLS regression (ICI Table 20, Newey-West HAC)
│   ├── model_visualisation.ipynb # All Monte Carlo and stress test figures
│   └── sobol_visualisation.ipynb # Sobol sensitivity figures
├── data/
│   ├── ici/                      # ICI Fact Book raw data (Tables 20, 21, 63, 64)
│   ├── free_sources/             # Fed Z.1, FRED, ICI supplemental tables
│   ├── module1_demographics/     # Census population projections by age
│   ├── module2_inflows/          # Vanguard/BLS inflow calibration inputs
│   ├── module3_outflows/         # SCF, IRS RMD, Vanguard withdrawal data
│   ├── module4_netflows/         # Fed buyback/issuance data
│   ├── module5_priceimpact/      # Bloomberg passive AUM, FactSet market cap
│   ├── descriptive/              # Summary statistics and cross-checks
│   └── processed/                # All pipeline outputs (CSV, NPZ)
└── outputs/                      # Figures (PNG) used in the thesis
```

## Run Order

All scripts run from the `notebooks/` directory. The pipeline has a strict dependency chain:

```
1. 01_data_exploration.ipynb     → Loads raw data, generates processed CSVs
2. model_runner.py               → Runs 25,000-path Monte Carlo (imports simulation_engine.py)
3. sobol_runner.py               → Runs Sobol analysis (imports simulation_engine.py)
4. 02_arima.ipynb                → ARIMA passive share forecast
5. 03_regression.ipynb           → OLS regression on ICI quarterly flows
6. model_visualisation.ipynb     → Generates all MC/stress test figures
7. sobol_visualisation.ipynb     → Generates all Sobol figures
```

Steps 2 and 3 are the computationally intensive runs. Step 2 produces `data/processed/mc_results.npz`; step 3 produces `data/processed/sobol_results.npz`. Steps 4-7 can run in any order once the upstream outputs exist.

## Requirements

Python 3.10+ with the following packages:

```
numpy
pandas
matplotlib
seaborn
scipy
statsmodels
SALib
openpyxl
xlrd
```

Install with:
```bash
pip install numpy pandas matplotlib seaborn scipy statsmodels SALib openpyxl xlrd
```

## Key Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| Monte Carlo paths | 25,000 | `model_runner.py` |
| Random seed | 42 | `model_runner.py` |
| Equity return (arithmetic) | 11.8% | Damodaran (1928-2024) |
| Equity return (geometric) | 9.9% | Damodaran (1928-2024) |
| Return volatility | 19.5% | Damodaran (1928-2024) |
| Base multiplier M | U(3, 7) | Gabaix & Koijen (2023) |
| Haddad et al. chi | 3.0 | Haddad et al. (2025) |
| Passive share, 2025 | 35% | Chinco & Sammon (2024) |
| Passive share cap | 67% | Modelling assumption |
| Net buyback yield | 0.98% ± 0.72% | Fed Z.1, 2020-2024 |
| DC plan access rate | 72% | BLS NCS (2024) |
| Sobol sample size (N) | 2,048 | `sobol_runner.py` |

## Data Sources

All primary data sources except Bloomberg and FactSet are publicly available:

- **U.S. Census Bureau (2023)**: Population projections by single-year age, 2025-2060
- **Vanguard (2025a, 2025b)**: Retirement savings and withdrawal behaviour
- **BLS (2024, 2025)**: National Compensation Survey, Employment Cost Index
- **IRS Publication 590-B (2024)**: RMD divisor tables
- **Federal Reserve SCF (2022)**: Retirement account balances by age
- **Federal Reserve Z.1 (2025)**: Net equity issuance (Table F.103)
- **ICI Fact Book (2025)**: Mutual fund flow data (Tables 20, 21)
- **Damodaran (2025)**: Historical U.S. equity returns, 1928-2024
- **Chinco & Sammon (2024)**: Corrected passive ownership share
- **Bloomberg (2025)**: Semi-annual passive equity AUM (proprietary)
- **FactSet (2025)**: FT Wilshire 5000 market capitalisation (proprietary)

## Reproducibility

All results are fully reproducible from the random seed (42). Running `model_runner.py` and `sobol_runner.py` from the `notebooks/` directory regenerates the `.npz` result files. The visualisation notebooks then reproduce all thesis figures.

## License

This repository accompanies an academic thesis. Please cite appropriately if referencing the code or methodology.
