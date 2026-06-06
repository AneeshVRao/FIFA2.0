# Product Requirements Document

## FIFA World Cup 2026 Prediction Platform

**Document Version:** 1.0  
**Status:** Final — Pre-Tournament Freeze  
**Prediction Freeze Date:** June 6, 2026  
**Classification:** Internal — Engineering & Product  
**Authors:** Principal ML Architect · Senior Football Data Scientist · Product Manager · Technical Lead

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Product Scope](#3-product-scope)
4. [Functional Requirements](#4-functional-requirements)
5. [Data Requirements](#5-data-requirements)
6. [Entity Resolution Strategy](#6-entity-resolution-strategy)
7. [Feature Engineering Specification](#7-feature-engineering-specification)
8. [Machine Learning Architecture](#8-machine-learning-architecture)
9. [Evaluation Strategy](#9-evaluation-strategy)
10. [System Architecture](#10-system-architecture)
11. [Database Design](#11-database-design)
12. [API Design](#12-api-design)
13. [Frontend Requirements](#13-frontend-requirements)
14. [Risks and Limitations](#14-risks-and-limitations)
15. [Validation and Launch Checklist](#15-validation-and-launch-checklist)
16. [Future Roadmap](#16-future-roadmap)

---

## 1. Executive Summary

### 1.1 Project Vision

The FIFA World Cup 2026 Prediction Platform is a pre-tournament forecasting system that uses rigorous machine learning, probabilistic modeling, and Monte Carlo simulation to generate the most statistically defensible predictions for every match, stage, and outcome of the 2026 FIFA World Cup — entirely from data available on or before June 6, 2026.

This platform does not make live in-tournament predictions. All models are frozen at the prediction freeze date. The system is designed to provide a transparent, explainable, and mathematically sound probabilistic view of tournament outcomes, serving football analysts, sports journalists, data science researchers, and engaged fans who want to understand the quantitative edge beneath tournament forecasting.

### 1.2 Objectives

The platform must accomplish the following before the tournament's opening match:

- **O1:** Train and validate a Match Outcome Predictor capable of exceeding 57% accuracy on historical international match data, outperforming a naïve bookmaker-anchored baseline.
- **O2:** Build a calibrated Expected Goals (xG) model achieving a Log Loss of ≤ 0.28 on held-out shot data.
- **O3:** Produce a Bayesian Penalty Shootout Predictor that correctly models the partial-pooling behavior of players with minimal historical data.
- **O4:** Run 100,000 Monte Carlo simulations of the complete 104-match tournament to generate stable, converged probabilistic distributions for every team's stage-by-stage advancement.
- **O5:** Expose all model outputs through a documented REST API consumed by a React-based frontend dashboard.
- **O6:** Provide full auditability — every prediction must be traceable to the features and datasets that produced it.

### 1.3 Success Criteria

| Metric | Target |
|---|---|
| Match Outcome Accuracy | ≥ 57% on 2022 WC holdout |
| Match Outcome AUC-ROC | ≥ 0.75 |
| xG Log Loss | ≤ 0.28 |
| xG Brier Score | ≤ 0.07 |
| Penalty Model Calibration | Within ±3% of observed rates |
| Monte Carlo Convergence | Champion probability variance < 0.5% at 100k runs |
| API P95 Response Time | ≤ 400 ms |
| Frontend Dashboard Load | ≤ 2.5 s on 4G |

### 1.4 Intended Users

| User Segment | Primary Use Case |
|---|---|
| Football Analysts & Journalists | Cite probabilistic forecasts in pre-tournament coverage |
| Data Science Researchers | Benchmark against published Elo and bookmaker models |
| Casual Fans | Explore interactive bracket and Golden Boot predictions |
| Sports Betting Professionals | Compare platform edge against market consensus odds |
| Internal Engineering Team | Monitor model performance, query the API, validate outputs |

### 1.5 Key Deliverables

- Trained and serialized ML models (Match Outcome, xG, Penalty) with calibration wrappers
- DuckDB analytical warehouse with full feature tables and simulation outputs
- FastAPI backend exposing all prediction endpoints
- React frontend dashboard with match predictor, xG sandbox, penalty sandbox, bracket explorer, and Golden Boot page
- Full backtesting report against historical World Cup tournaments (2014, 2018, 2022)
- Model cards and data lineage documentation for all datasets used

---

## 2. Problem Statement

### 2.1 Why Predicting Football Tournaments Is Difficult

Association football is, by design, a low-scoring sport. In international matches, teams average fewer than 2.6 goals combined per 90 minutes, and a meaningful fraction of matches end 0-0 or 1-0. In this environment, the law of large numbers fails the analyst: small samples of goals make it extraordinarily difficult to separate true team quality from match-level variance. A single deflected shot or a referee error can determine the outcome of a match despite one team generating twice the expected scoring chances.

The 2026 World Cup amplifies this difficulty. For the first time, 48 teams will compete across 104 matches spread across three host nations — the United States, Canada, and Mexico — introducing unprecedented logistical and physiological variables. Teams traveling from venues in Vancouver to matches in Mexico City face altitude differentials exceeding 2,200 metres and cross-continental Haversine distances up to 12,866 km. These factors have historically measurable effects on team performance and must be explicitly modeled.

### 2.2 Sources of Uncertainty

**Aleatoric Uncertainty (Irreducible):** Football contains events that are mathematically unpredictable regardless of data quality — early red cards, goalkeeper howlers, deflected own goals, and VAR decisions. These random events permanently alter a match's trajectory and cannot be modeled away.

**Epistemic Uncertainty (Reducible):** This category includes unknowns that arise from data gaps and modeling limitations. Examples include an injured squad member whose absence has not been announced, a head coach's tactical setup that was unreported before the freeze date, or a player's true psychological resilience under penalty shootout pressure.

**Structural Uncertainty:** The 2026 format is unprecedented. The "best third-place team" advancement logic, which ranks 12 third-place finishers from groups A–L simultaneously and advances the top 8, introduces compounding path dependencies that no prior World Cup simulation framework has been validated against at scale.

**Temporal Decay:** International football fixtures are sparse. A qualifying result from November 2025 reflects team quality seven months before the tournament. Models that rely on raw recent form without correcting for latency between fixtures will anchor predictions to stale signals.

### 2.3 Why Probabilistic Forecasting Is Necessary

A deterministic prediction — "France will win the 2026 World Cup" — provides zero information about uncertainty and is falsifiable only at tournament completion. Probabilistic forecasting assigns a distribution of outcomes across all scenarios, which allows analysts to:

- Communicate uncertainty explicitly (e.g., "France has a 17.4% champion probability")
- Identify undervalued teams whose advancement probabilities exceed market-implied odds
- Measure model calibration: if 100 events assigned a 30% probability occur 30% of the time, the model is well-calibrated
- Update priors transparently if the model architecture changes

All outputs from this platform must be probability distributions, not point estimates.

---

## 3. Product Scope

### 3.1 In Scope

The following subsystems and features are in scope for the June 6, 2026 platform launch:

**Match Outcome Predictor:** Pre-match Win/Draw/Loss probability generation for any two international squads, producing calibrated probabilities and top-5 most likely scorelines.

**Expected Goals (xG) Engine:** A shot-level model that assigns a continuous probability (0.00–1.00) to any described shot scenario based on spatial coordinates, shot context, and defensive environment.

**Penalty Shootout Predictor:** A Bayesian hierarchical model that estimates per-player conversion and save rates, enabling full 5-kick and sudden-death shootout simulations with team-level win probabilities.

**Tournament Timeline Simulator:** A 100,000-iteration Monte Carlo engine covering all 104 matches of the 48-team format, including group stage, best-third-place advancement, and full knockout bracket progression through to the Final.

**Team Strength Ratings:** Pre-tournament Elo ratings, squad market valuations, and RAPM-based offensive/defensive ratings for all 48 qualified nations, frozen at the prediction date.

**Player Strength Ratings:** Individual offensive impact ratings (θ_off) for key squad players, combined with historical international caps, penalty histories, and position classifications.

**Golden Boot Projections:** Per-player expected goal tallies derived from team stage-advancement probabilities, player xG rates, and expected minutes.

**Tournament Bracket Explorer:** An interactive frontend tool allowing users to explore simulated bracket paths and view stage-specific probabilities for any of the 48 teams.

**REST API:** A documented FastAPI backend exposing all model outputs.

**Frontend Dashboard:** A React-based web application consuming the API and presenting all predictions interactively.

### 3.2 Out of Scope

The following capabilities are explicitly excluded from this release:

- Live match predictions or in-play probability updates during the tournament
- In-play betting model or odds comparison engine
- Real-time injury tracking or squad news integration after June 6, 2026
- Daily model retraining during the tournament period
- Player transfer activity after the prediction freeze date
- Video or tracking data ingestion (e.g., optical player tracking at 25 fps)
- Social media sentiment modeling
- Mobile native applications (iOS/Android)

---

## 4. Functional Requirements

### 4.1 Match Outcome Predictor

**Purpose:** Given any two international squads, produce calibrated probabilities for all three match outcomes and enumerate the most likely specific scorelines.

**Inputs:**

| Field | Type | Description | Required |
|---|---|---|---|
| `team_a_id` | `string` | Standardized Reep entity ID for Team A | Yes |
| `team_b_id` | `string` | Standardized Reep entity ID for Team B | Yes |
| `venue_id` | `string` | Stadium/venue identifier for altitude and host lookup | Yes |
| `match_context` | `enum` | `group`, `r32`, `r16`, `qf`, `sf`, `final` | Yes |
| `team_a_travel_km` | `float` | Haversine distance (km) traveled by Team A to this venue | Computed |
| `team_b_travel_km` | `float` | Haversine distance (km) traveled by Team B to this venue | Computed |

**Processing Requirements:**

- Load frozen pre-tournament feature vectors for both teams from the DuckDB `dim_teams` table
- Apply `RobustScaler` normalization to continuous features using scaler fitted on training data
- Run `HistGradientBoostingClassifier` inference on the merged feature vector
- Apply Platt Scaling calibration wrapper to convert raw scores to true probabilities
- Ensure Win% + Draw% + Loss% sums to 1.00 (± 0.001 floating point tolerance)
- Generate top-5 scorelines by sampling from the Bivariate Poisson scoreline grid using the derived xG lambda values

**Outputs:**

| Field | Type | Description |
|---|---|---|
| `team_a_win_pct` | `float` | Calibrated probability of Team A win (0.00–1.00) |
| `draw_pct` | `float` | Calibrated probability of draw (0.00–1.00) |
| `team_b_win_pct` | `float` | Calibrated probability of Team B win (0.00–1.00) |
| `most_likely_scorelines` | `array[object]` | Top 5 scorelines with individual probabilities |
| `team_a_xg` | `float` | Expected goals for Team A |
| `team_b_xg` | `float` | Expected goals for Team B |
| `model_version` | `string` | Model artifact version tag |
| `features_snapshot` | `object` | Key feature values used in inference (for auditability) |

**Performance Requirements:**

- Inference latency ≤ 80 ms per prediction
- All three output probabilities must be within 5% of bookmaker consensus closing odds (validation gate)

---

### 4.2 Expected Goals (xG) Engine

**Purpose:** Assign a calibrated xG probability to any described shot scenario. Used as an input to the Match Outcome Predictor and exposed directly via the xG Sandbox in the frontend.

**Inputs:**

| Field | Type | Description | Required |
|---|---|---|---|
| `shot_x` | `float` | X coordinate on the pitch (0–100, goal line = 100) | Yes |
| `shot_y` | `float` | Y coordinate on the pitch (0–100, center = 50) | Yes |
| `situation` | `enum` | `open_play`, `free_kick`, `corner`, `penalty` | Yes |
| `body_part` | `enum` | `right_foot`, `left_foot`, `head` | Yes |
| `goalkeeper_x` | `float` | Goalkeeper X coordinate at shot moment (freeze-frame) | Optional |
| `goalkeeper_y` | `float` | Goalkeeper Y coordinate at shot moment (freeze-frame) | Optional |
| `defenders_in_cone` | `int` | Number of defenders in shooter-to-goalpost triangle | Optional |
| `defensive_pressure_m` | `float` | Distance (metres) to nearest defender | Optional |

**Processing Requirements:**

- Derive `distance_to_goal` and `angle_to_goal` from X/Y coordinates
- When freeze-frame features are absent, use situational priors from training set medians
- Run XGBoost Classifier inference on feature vector
- Apply calibration curve transformation to raw Platt scores

**Outputs:**

| Field | Type | Description |
|---|---|---|
| `xg_value` | `float` | Calibrated expected goal probability (0.00–1.00) |
| `shot_danger_class` | `enum` | `low` (0.00–0.09), `medium` (0.10–0.29), `high` (0.30–1.00) |
| `distance_to_goal_m` | `float` | Derived Euclidean distance to goal centre |
| `angle_to_goal_deg` | `float` | Derived visible angle to goalposts |
| `top_features` | `array[string]` | Top 3 features driving this xG value (SHAP-based) |

---

### 4.3 Penalty Shootout Predictor

**Purpose:** Given two squads in a knockout fixture, simulate a best-of-five (plus sudden death) penalty shootout using Bayesian-smoothed player-level conversion and save rates.

**Inputs:**

| Field | Type | Description | Required |
|---|---|---|---|
| `team_a_id` | `string` | Reep entity ID for Team A | Yes |
| `team_b_id` | `string` | Reep entity ID for Team B | Yes |
| `team_a_shooters` | `array[string]` | Ordered list of up to 11 player Reep IDs | Optional |
| `team_b_shooters` | `array[string]` | Ordered list of up to 11 player Reep IDs | Optional |
| `team_a_goalkeeper_id` | `string` | Reep player ID for Team A's goalkeeper | Optional |
| `team_b_goalkeeper_id` | `string` | Reep player ID for Team B's goalkeeper | Optional |
| `n_simulations` | `int` | Number of shootout simulations to run (default: 10,000) | Optional |

If shooter or goalkeeper lists are absent, the system uses the full registered squad ordered by forward → midfielder → defender position, applying the Bayesian positional priors.

**Processing Requirements:**

- Load Bayesian-smoothed taker conversion rates and goalkeeper save rates from `dim_players`
- For players with zero historical penalty data, apply uninformative positional prior (μ_pos from training distribution)
- Simulate best-of-five sequences; if tied at 5 kicks each, continue in sudden death
- Count advancing team across all simulations; compute win percentages

**Outputs:**

| Field | Type | Description |
|---|---|---|
| `team_a_shootout_win_pct` | `float` | P(Team A wins shootout) across simulations |
| `team_b_shootout_win_pct` | `float` | P(Team B wins shootout) across simulations |
| `team_advantage` | `string` | `team_a`, `team_b`, or `neutral` (if within 2%) |
| `advantage_magnitude` | `float` | Absolute percentage edge |
| `sample_sequences` | `array[object]` | 5 representative simulated shootout sequences (kick-by-kick) |
| `top_takers` | `array[object]` | Top 3 takers per team by Bayesian conversion rate |
| `top_savers` | `array[object]` | Both goalkeepers' smoothed save rates with uncertainty intervals |

---

### 4.4 Tournament Simulator

**Purpose:** Run 100,000 Monte Carlo simulations of the complete 48-team, 104-match tournament and produce stable probabilistic distributions for every team's advancement to each stage.

**Inputs (Pre-loaded at freeze date, no runtime input required):**

| Dataset | Description |
|---|---|
| `dim_teams` (48 rows) | Pre-tournament Elo, squad value, confederation, group, host flag |
| `dim_venues` (16 rows) | Stadium GPS coordinates, altitude, city, host nation |
| `fct_group_assignments` | Mapping of 48 teams to 12 groups (A–L) |
| `match_schedule` | Pre-tournament fixed match schedule (date, venue, group) |
| `travel_matrix` | Precomputed Haversine distance matrix between all 16 venues |

**Processing Requirements:**

Per simulation iteration:

1. Initialize dynamic Elo ratings from frozen pre-tournament baselines
2. Simulate all 72 group stage matches using Bivariate Poisson with Dixon-Coles τ correction; apply altitude friction (A_v) and travel fatigue modifier per match
3. Update dynamic Elo ratings after each simulated match using the standard Elo update formula with Dixon-Coles-adjusted goal difference as the margin input
4. Apply mean-reversion rate γ to pull dynamic Elo back toward pre-tournament baseline after each match
5. Calculate group standings (Points → GD → GF → H2H → Fair Play)
6. Collect all 12 third-place teams; rank by Points → GD → GF; advance top 8
7. Populate the fixed 32-team knockout bracket per FIFA 2026 path rules
8. Simulate R32 through Final matches; trigger Bayesian Penalty Shootout Predictor when knockout matches end level after 120 simulated minutes
9. Record the championship outcome for this iteration

After all 100,000 iterations:

- Aggregate stage-by-stage counts per team and divide by N for probabilities
- Compute Golden Boot goal distribution per player from simulated expected minutes × xG rate × conversion factor
- Write outputs to `team_stage_probabilities`, `matchup_forecasts`, and `golden_boot_distribution` tables

**Outputs:**

| Table | Granularity | Description |
|---|---|---|
| `team_stage_probabilities` | Team × Stage | P(reaching Group, R32, R16, QF, SF, Final, Champion) |
| `matchup_forecasts` | Match | P(Win/Draw/Loss) and most likely scorelines per fixture |
| `golden_boot_distribution` | Player | Simulated goal total distribution (mean, p10, p50, p90) |
| `group_table_distributions` | Team × Position | P(finishing 1st, 2nd, 3rd, 4th in group) |
| `bracket_path_frequencies` | Team × Path | Most frequent bracket routes taken in simulation |

**Performance Requirements:**

- Full 100,000-simulation run must complete in ≤ 4 hours on a machine with 8 CPU cores
- Use `multiprocessing` with 50 simulations per worker chunk
- Champion probability standard deviation across 5 independent 100k-run batches must be < 0.5%

---

## 5. Data Requirements

### 5.1 StatsBomb Open Data

| Attribute | Detail |
|---|---|
| **Purpose** | Deep tactical event-level data for historical national team matches; provides freeze-frame goalkeeper and defender positioning data for advanced xG features |
| **Source** | `github.com/statsbomb/open-data` (Apache 2.0 license) |
| **Key Columns** | `location` (X/Y), `shot.freeze_frame` (defender/GK positions), `shot.statsbomb_xg`, `shot.body_part`, `shot.type`, `team.name`, `match_id`, `minute`, `second` |
| **Update Frequency** | Periodic releases; frozen at June 6, 2026 for this project |
| **Reliability Score** | 9/10 — Gold standard for event-level tracking depth; data quality is rigorously validated by StatsBomb's commercial curation pipeline |
| **Limitations** | Match coverage is selective (top competitions only); not all World Cup qualifying matches are included |

### 5.2 Understat

| Attribute | Detail |
|---|---|
| **Purpose** | Primary source for shot-level coordinate data and situation context for the xG model; also provides supplemental domestic penalty kick histories for the shootout predictor |
| **Source** | `understat.com` via `understatAPI` Python library or `worldfootballR` R wrapper |
| **Key Columns** | `X`, `Y`, `result` (Goal/MissedShot/SavedShot/BlockedShot), `situation` (OpenPlay/SetPiece/Corner/Penalty), `shotType` (LeftFoot/RightFoot/Head), `xG`, `player`, `match_id` |
| **Update Frequency** | Matches scraped within 24 hours of completion; frozen at prediction date |
| **Reliability Score** | 8/10 — Proprietary xG model is well-validated; coordinate accuracy is high; API availability is subject to scraping rate limits |
| **Limitations** | Proprietary xG model may not match the platform's internally trained xG values; use as coordinate source only, not as xG label |

### 5.3 FBref

| Attribute | Detail |
|---|---|
| **Purpose** | Squad-level aggregated statistics (pass completion, progressive carries, pressures, xG totals) for national teams in qualifying and friendlies; also provides penalty kick logs as a secondary dataset |
| **Source** | `fbref.com` via `worldfootballR` or `SoccerData` Python library |
| **Key Columns** | `squad`, `goals`, `xg`, `npxg`, `xa`, `progressive_carries`, `presses`, `penalties_att`, `penalties_scored`, `player`, `minutes`, `age`, `nation`, `pos` |
| **Update Frequency** | Season-level updates; frozen at prediction date |
| **Reliability Score** | 8.5/10 — Powered by Opta's commercial data pipeline; widely used as an authoritative reference in academic football research |
| **Limitations** | Opta-powered data may have licensing restrictions for commercial reuse; player-level granularity is less deep than StatsBomb event data |

### 5.4 Transfermarkt Datasets

| Attribute | Detail |
|---|---|
| **Purpose** | The single source of truth for squad market valuations and international caps; squad total value is the single most predictive structural feature in the match outcome model |
| **Source** | `github.com/dcaribou/transfermarkt-datasets` (community-maintained Kaggle dataset refreshed monthly) |
| **Key Columns** | `player_id`, `team_id`, `market_value_in_eur`, `international_caps`, `international_goals`, `position`, `current_club_id`, `date_of_birth`, `height_in_cm`, `foot` |
| **Update Frequency** | Monthly scrapes; ensure the June 2026 snapshot is used |
| **Reliability Score** | 9/10 — Community-consensus valuations; the most complete open source for market value data. Values are crowdsourced estimates, not transaction prices |
| **Limitations** | Valuations reflect community consensus and lag actual transfer market activity by weeks; not audited financial data |

### 5.5 Football-Data.co.uk

| Attribute | Detail |
|---|---|
| **Purpose** | Historical consensus bookmaker closing odds for international matches; used to validate model probability outputs and as a direct feature (bookmaker implied probability) in the match outcome model |
| **Source** | `football-data.co.uk` (free CSV downloads) |
| **Key Columns** | `HomeTeam`, `AwayTeam`, `Date`, `FTHG` (Full-Time Home Goals), `FTAG`, `FTR` (Full-Time Result), `B365H`, `B365D`, `B365A` (Bet365 odds), `PSH`, `PSD`, `PSA` (Pinnacle odds), `WHH`, `WHD`, `WHA` (William Hill odds) |
| **Update Frequency** | Matches updated within days of completion; frozen at prediction date |
| **Reliability Score** | 9.5/10 — Extremely reliable for historical odds; Pinnacle closing odds are widely accepted as the most accurate market-consensus probability signal available publicly |
| **Limitations** | International match coverage is less complete than domestic league coverage; some qualifying matches may be missing |

### 5.6 Fjelstul World Cup Database

| Attribute | Detail |
|---|---|
| **Purpose** | The definitive academic archive for all historical FIFA World Cup events: matches, goals, squads, and critically, the `penalty_kicks` table isolating every World Cup shootout attempt by taker and outcome |
| **Source** | `github.com/jfjelstul/worldcup` (Joshua Fjelstul, academic public release) |
| **Key Columns (penalty_kicks table)** | `tournament_id`, `match_id`, `team_id`, `player_id`, `kick_number`, `converted` (boolean), `goalkeeper_id`, `saved` (boolean), `minute` |
| **Key Columns (matches table)** | `match_id`, `home_team_id`, `away_team_id`, `home_score`, `away_score`, `stage`, `group`, `date`, `venue` |
| **Update Frequency** | Historical data only; updated post-2022 WC; frozen at prediction date |
| **Reliability Score** | 10/10 — The academic gold standard; hand-validated against official FIFA records; used in peer-reviewed sports analytics research |
| **Limitations** | Covers historical World Cups only; the 2026 format (48 teams) is structurally novel and not represented |

### 5.7 Club Elo

| Attribute | Detail |
|---|---|
| **Purpose** | Provides time-series Elo ratings for international national teams; used as the pre-tournament baseline strength rating and as a training feature in the match outcome model |
| **Source** | `clubelo.com` (free CSV API endpoint) |
| **Key Columns** | `team` (team name), `from` (date), `to` (date), `rank`, `elo` |
| **Update Frequency** | Updated after each international fixture; frozen at prediction date |
| **Reliability Score** | 8/10 — Widely cited; Elo formula is transparent and reproducible; team name matching requires entity resolution care |
| **Limitations** | Does not account for squad composition changes; single scalar rating may mask squad heterogeneity |

### 5.8 SoccerData

| Attribute | Detail |
|---|---|
| **Purpose** | Python scraping library that aggregates FBref, ClubElo, and Sofascore data into standardized Pandas DataFrames; reduces ingestion pipeline complexity |
| **Source** | `github.com/soccerdata` (open-source Python package) |
| **Key Columns** | Inherits columns from underlying sources; standardizes column naming and date formats |
| **Update Frequency** | Library-dependent; follows upstream source refresh cadence |
| **Reliability Score** | 7.5/10 — Convenience layer; introduces abstraction risk if underlying sources change their HTML structure |
| **Limitations** | Not a primary data source; subject to scraping fragility; should always be validated against direct source downloads |

### 5.9 Reep Entity Register

| Attribute | Detail |
|---|---|
| **Purpose** | Cross-provider player and team identity resolution; maps a single canonical player or team entity to its IDs across Transfermarkt, FBref, Understat, Fjelstul, and Club Elo |
| **Source** | Community-maintained CSV register (Reep project) |
| **Key Columns** | `reep_player_id`, `reep_team_id`, `tm_player_id`, `fbref_player_id`, `understat_player_id`, `fjelstul_player_id`, `player_name_canonical`, `team_name_canonical` |
| **Update Frequency** | Manually updated by community contributors |
| **Reliability Score** | 7/10 — Coverage is incomplete for less-prominent international players; manual auditing required for squads from CONCACAF, CAF, and OFC confederations |
| **Limitations** | Gaps in coverage require fallback fuzzy matching; this is the single largest engineering risk in the data pipeline |

---

## 6. Entity Resolution Strategy

### 6.1 The Entity Resolution Problem

Every data source uses a different internal identifier system for teams and players. "Portugal" in Club Elo may appear as "Portugal," "POR," or "Porto National Team" depending on the source. Cristiano Ronaldo has a distinct integer ID in Transfermarkt, FBref, Understat, and the Fjelstul database. Without a single canonical identity layer, dataset joins will silently drop rows or create spurious duplicates, corrupting every downstream model.

### 6.2 Team Matching

**Primary Strategy:** Use the Reep Entity Register's `reep_team_id` as the canonical key. All 48 qualified nations will have a manually validated entry.

**Fallback — Fuzzy String Matching:** For teams absent from the Reep register or where naming conflicts exist (e.g., "Ivory Coast" vs. "Côte d'Ivoire" vs. "CIV"), apply Jaro-Winkler string similarity with a threshold of ≥ 0.92 against a canonical country name list derived from ISO 3166-1. All fuzzy matches must be logged to a `entity_resolution_audit` table for manual review.

**Confederation Flag:** All 48 teams must be tagged with their FIFA confederation (`UEFA`, `CONMEBOL`, `CONCACAF`, `CAF`, `AFC`, `OFC`) as a categorical feature. This is a non-nullable field in `dim_teams`.

### 6.3 Player Matching

**Primary Strategy:** Use Reep `reep_player_id` for all player-level joins. For players present in multiple source datasets, the Reep ID serves as the foreign key in all `fct_` tables.

**Fallback — Multi-field Composite Key:** If a player is absent from Reep, construct a composite lookup key of `(canonical_team_id, birth_date, last_name_normalized)`. The `last_name_normalized` value strips diacritics (e.g., "González" → "Gonzalez") and converts to lowercase.

**Conflict Resolution:** When two candidate player records produce the same composite key (e.g., two players with identical surnames, birth dates, and nationalities), escalate to manual review. Do not auto-merge. Log the conflict to `entity_resolution_audit`.

### 6.4 Cross-Provider ID Map

The following ID map must be maintained in the `dim_entity_map` table:

| Column | Source |
|---|---|
| `reep_player_id` | Canonical (Reep) |
| `tm_player_id` | Transfermarkt |
| `fbref_player_id` | FBref / Opta |
| `understat_player_id` | Understat |
| `fjelstul_player_id` | Fjelstul WC Database |
| `statsbomb_player_id` | StatsBomb |
| `reep_team_id` | Canonical (Reep) |
| `tm_team_id` | Transfermarkt |
| `fbref_team_id` | FBref |
| `fjelstul_team_id` | Fjelstul WC Database |
| `clubelo_team_name` | Club Elo (string key) |

### 6.5 Handling Naming Conflicts

All unresolved naming conflicts must be surfaced in a `data_quality_dashboard` internal tool showing: source system, conflicting names, candidate Reep IDs, similarity scores, and an `is_resolved` boolean flag. No model training or simulation run may proceed while the `is_resolved` flag is False for any of the 48 qualified nations or their first-team squads.

---

## 7. Feature Engineering Specification

### 7.1 Match Outcome Features

The following features are engineered at the match level for the HistGBM Match Outcome Predictor. Features are computed as differentials (Team A minus Team B) unless otherwise noted.

| Rank | Feature Name | Description | Source |
|---|---|---|---|
| 1 | `squad_market_value_diff_eur` | Difference in total squad market valuation (€) | Transfermarkt |
| 2 | `bookmaker_implied_prob_a_win` | Bookmaker consensus implied probability of Team A win (Pinnacle closing odds) | Football-Data.co.uk |
| 3 | `bookmaker_implied_prob_draw` | Bookmaker consensus implied probability of draw | Football-Data.co.uk |
| 4 | `elo_rating_diff` | Difference in pre-tournament Club Elo ratings | Club Elo |
| 5 | `altitude_diff_m` | Venue altitude minus Team A's native training altitude (metres) | Venue DB / Covers.com |
| 6 | `team_a_travel_km` | Haversine distance (km) from Team A's prior match venue | Computed |
| 7 | `team_b_travel_km` | Haversine distance (km) from Team B's prior match venue | Computed |
| 8 | `timezone_crossings_diff` | Difference in time zones crossed since last match | Computed |
| 9 | `rest_day_asymmetry` | Difference in days since each team's prior match | Computed |
| 10 | `host_nation_flag` | 1 if Team A is USA, CAN, or MEX; −1 if Team B; 0 otherwise | Static |
| 11 | `total_caps_diff` | Difference in cumulative squad international caps | Transfermarkt / FBref |
| 12 | `total_intl_goals_diff` | Difference in cumulative squad international goals | Transfermarkt / FBref |
| 13 | `confederation_strength_a` | Historical World Cup round-of-16 reach rate for Team A's confederation | Fjelstul |
| 14 | `confederation_strength_b` | Same for Team B | Fjelstul |
| 15 | `joint_squad_age_diff` | Difference in mean squad age vs. peak age (27 years) | Transfermarkt |
| 16 | `shared_club_minutes` | Average minutes played together at club level (proxy for squad chemistry) | FBref |
| 17 | `avg_squad_height_diff_cm` | Difference in average squad height (cm) | Transfermarkt |
| 18 | `historic_fifa_points_diff` | Difference in cumulative historical FIFA points (5-year window) | FIFA |
| 19 | `match_stage_pressure` | Encoded knockout stage (0=Group, 1=R32 ... 5=Final) | Static |
| 20 | `head_to_head_elo_adjusted_record` | H2H win rate adjusted for opponent Elo at time of match | Fjelstul |

**Features Explicitly Excluded:**

- Raw ball possession percentage (not predictive of match outcome; misleads low-block counter-attack teams)
- Current FIFA Ranking in isolation (schedule-biased; use Elo instead)
- Basic win/loss streak counts (not opponent-quality adjusted)
- Raw "current form" match count metrics (temporal latency in international football renders these near-zero predictive value)

### 7.2 xG Features

| Rank | Feature Name | Description | Source |
|---|---|---|---|
| 1 | `distance_to_goal_m` | Euclidean distance from shot location to goal centre (derived from X/Y) | Computed |
| 2 | `angle_to_goal_deg` | Visible angle subtended by the goalposts from shot location (derived from X/Y) | Computed |
| 3 | `defenders_in_cone` | Count of defenders in the shooter-to-goalpost triangle (freeze-frame) | StatsBomb |
| 4 | `defensive_pressure_m` | Distance (m) from nearest defender at moment of shot (freeze-frame) | StatsBomb |
| 5 | `situation_type` | Encoded: open play / free kick / corner / penalty | Understat |
| 6 | `body_part` | Encoded: right foot / left foot / head | Understat |
| 7 | `shot_x` | Raw X pitch coordinate (0–100) | Understat |
| 8 | `shot_y` | Raw Y pitch coordinate (0–100) | Understat |
| 9 | `goalkeeper_distance_to_shot_line` | Perpendicular distance from GK to ball–goal centre line (freeze-frame) | StatsBomb |
| 10 | `is_first_time_shot` | Binary: 1 if shot was first-touch (from StatsBomb `shot.first_time`) | StatsBomb |

**Derived Engineering Steps:**

```python
import numpy as np

GOAL_X = 100.0
GOAL_Y_LEFT = 36.8
GOAL_Y_RIGHT = 63.2
GOAL_Y_CENTER = 50.0

def compute_distance(x, y):
    return np.sqrt((GOAL_X - x)**2 + (GOAL_Y_CENTER - y)**2)

def compute_angle(x, y):
    a = np.sqrt((GOAL_X - x)**2 + (GOAL_Y_LEFT - y)**2)
    b = np.sqrt((GOAL_X - x)**2 + (GOAL_Y_RIGHT - y)**2)
    c = GOAL_Y_RIGHT - GOAL_Y_LEFT  # goalpost width
    numerator = a**2 + b**2 - c**2
    denominator = 2 * a * b
    cos_angle = np.clip(numerator / denominator, -1.0, 1.0)
    return np.degrees(np.arccos(cos_angle))
```

### 7.3 Penalty Shootout Features

| Rank | Feature Name | Description | Source |
|---|---|---|---|
| 1 | `taker_bayesian_conversion_rate` | Bayesian-smoothed historical penalty conversion rate (partial pooling toward positional mean) | Fjelstul + Understat |
| 2 | `goalkeeper_bayesian_save_rate` | Bayesian-smoothed historical penalty save rate | Fjelstul + Understat |
| 3 | `kick_sequence_number` | Position in shootout order (1–5, then 6+ in sudden death); captures pressure escalation | Computed |
| 4 | `player_position_prior` | Position-level prior: Striker (μ=0.80), Midfielder (μ=0.75), Defender (μ=0.65), Goalkeeper (μ=0.60) | Derived |
| 5 | `international_caps` | Proxy for psychological experience under pressure | Transfermarkt / FBref |
| 6 | `age_vs_peak_delta` | Absolute difference between player age and peak (27); younger/older players show lower conversion | Transfermarkt |
| 7 | `match_context_shootout` | Binary: 1 for World Cup knockout stage (vs. league in-game penalty) | Static |
| 8 | `cumulative_score_pressure` | Running score differential in the shootout at time of kick | Computed per simulation |

---

## 8. Machine Learning Architecture

### 8.1 Match Outcome Model

#### Algorithm Comparison

| Algorithm | Validation Accuracy | Notes |
|---|---|---|
| Logistic Regression | ~52.5% | Cannot capture non-linear interactions (altitude × fatigue × squad depth). Fails on the Draw class. Excluded. |
| Random Forest | ~56.8% | Handles non-linearity well; natural uncertainty quantification via bagging. Computationally heavier; sensitive to class imbalance. |
| XGBoost | ~57.0% | High accuracy on tabular data; requires manual one-hot encoding for categorical features, increasing pipeline complexity. |
| CatBoost | ~57.2% | Excellent native categorical handling; slightly slower than histogram-based methods on large datasets. |
| **HistGradientBoosting (HistGBM)** | **~58.0%** | **Selected.** Fastest training; native handling of missing values and categoricals; best generalization via histogram binning. Restricted `max_depth=3` prevents memorization of noisy signals. |

#### Selected Architecture: HistGradientBoostingClassifier

```python
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline

match_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", RobustScaler()),
    ("model", CalibratedClassifierCV(
        HistGradientBoostingClassifier(
            max_depth=3,
            learning_rate=0.05,
            max_iter=400,
            l2_regularization=0.1,
            categorical_features="from_dtype",
            random_state=42
        ),
        method="sigmoid",  # Platt Scaling
        cv=5
    ))
])
```

#### Train/Test Strategy

- **Chronological Holdout:** Train on international match data from 1993–2018; hold out the 2022 World Cup as the test set. Never shuffle time series data — temporal leakage would inflate validation metrics and yield a model that fails to generalize.
- **Cross-Validation:** 5-fold cross-validation on the training set with `TimeSeriesSplit` for hyperparameter tuning.
- **Hyperparameter Search:** Grid search over `{max_depth: [2,3,4], learning_rate: [0.01, 0.05, 0.1], max_iter: [200, 400], l2_regularization: [0.0, 0.1, 0.5]}`.
- **Class Weighting:** Apply `class_weight="balanced"` equivalent to increase Draw class recall, as the Draw minority class is the most challenging to predict.

#### Calibration Strategy

Apply Platt Scaling (logistic regression on top of raw model scores) wrapped via `CalibratedClassifierCV`. Validate calibration on the 2022 WC holdout using a reliability diagram. Ensure the calibrated Win/Draw/Loss probabilities sum to 1.00 and lie within 5% of Pinnacle market odds on average.

---

### 8.2 xG Model

#### Algorithm Comparison

| Algorithm | Log Loss | Notes |
|---|---|---|
| Logistic Regression | ~0.32 | Underestimates non-linear angle/distance interactions. Historically accurate for simple xG, but outclassed by tree methods. |
| HistGradientBoosting | ~0.27 | Strong performance; slightly less interpretable spatial non-linearity than XGBoost. |
| CatBoost | ~0.27 | Excellent categorical handling for situation/body_part; clean pipeline. Strong alternative. |
| **XGBoost** | **~0.25** | **Selected.** Industry standard for xG modeling; superior handling of spatial non-linearities (sharp angle probability drops, small-box vs. outside-box differentials). |

#### Selected Architecture: XGBoost Classifier

```python
import xgboost as xgb

xg_model = xgb.XGBClassifier(
    objective="binary:logistic",
    n_estimators=500,
    max_depth=5,
    learning_rate=0.03,
    subsample=0.8,
    colsample_bytree=0.8,
    gamma=1.0,
    reg_alpha=0.1,
    reg_lambda=1.0,
    eval_metric="logloss",
    use_label_encoder=False,
    random_state=42
)
```

- **Label:** `goal` (binary: 1 = goal scored, 0 = no goal)
- **Training data:** All shots from Understat for top-5 European leagues + Champions League, last 10 seasons (approximately 1.5 million shot events)
- **Calibration:** Isotonic regression via `CalibratedClassifierCV(method="isotonic")` on a held-out calibration set of 100,000 shots
- **SHAP values:** Computed for all predictions using `shap.TreeExplainer` for frontend feature attribution display

---

### 8.3 Penalty Shootout Model

#### Algorithm Comparison

| Algorithm | Notes |
|---|---|
| Logistic Regression | Assigns 100% conversion rate to a player who is 1-for-1 in career penalties. Statistically absurd for low-frequency events. Excluded. |
| XGBoost / Gradient Boosting | Excellent for complex data; catastrophically prone to overfitting in low-signal environments. Single-digit event counts per player break tree-based categorical pooling. Excluded. |
| **Bayesian Hierarchical Binomial** | **Selected.** Mathematically optimal for low-count events. Partial pooling shrinks extreme individual estimates toward positional means. Natively produces calibrated credible intervals. |

#### Selected Architecture: Hierarchical Bayesian Binomial Model

```python
import pymc as pm

with pm.Model() as penalty_model:
    # Global hyperprior
    mu_global = pm.Beta("mu_global", alpha=75, beta=25)  # ~75% global prior
    kappa = pm.HalfNormal("kappa", sigma=20)  # concentration

    # Position-level priors (partial pooling)
    mu_position = pm.Beta(
        "mu_position",
        alpha=mu_global * kappa,
        beta=(1 - mu_global) * kappa,
        shape=n_positions  # Forward, Mid, Def, GK
    )

    # Player-level rates (shrunk toward positional mean)
    mu_player = pm.Beta(
        "mu_player",
        alpha=mu_position[player_position_idx] * kappa,
        beta=(1 - mu_position[player_position_idx]) * kappa,
        shape=n_players
    )

    # Likelihood
    conversions = pm.Binomial(
        "conversions",
        n=penalty_attempts,
        p=mu_player[player_idx],
        observed=penalty_goals
    )

    trace = pm.sample(2000, tune=1000, target_accept=0.9, cores=4)
```

**Goalkeeper Sub-model:** Mirror structure with a `save_rate` hyperprior anchored at the historical World Cup shootout save rate (~17%).

**Matchup Engine:** Per kick simulation:

```python
p_conversion = (
    base_rate
    + taker_skill_delta     # Taker rate - positional mean
    - goalkeeper_skill_delta  # GK save rate - global mean
    + sequence_pressure_modifier  # Calibrated from Fjelstul kick order data
)
p_conversion = np.clip(p_conversion, 0.05, 0.99)
```

---

### 8.4 Tournament Simulator

#### Monte Carlo Architecture

The simulator is a parallelized Python engine running 100,000 independent tournament replications.

**Parallelization Strategy:**

```python
from multiprocessing import Pool

def simulate_batch(batch_size: int, seed: int) -> list[dict]:
    """Simulate batch_size complete tournaments."""
    np.random.seed(seed)
    results = []
    for _ in range(batch_size):
        results.append(simulate_single_tournament())
    return results

with Pool(processes=8) as pool:
    batches = pool.starmap(
        simulate_batch,
        [(50, seed) for seed in range(2000)]  # 2000 batches × 50 = 100,000 sims
    )
```

#### Scoreline Generation: Bivariate Poisson with Dixon-Coles Correction

The expected goals (λ for home team, μ for away team) are computed from pre-tournament offensive/defensive ratings, adjusted for altitude and travel fatigue:

```
λ = exp(α_home + β_away + H + A_v + travel_fatigue_home)
μ = exp(α_away + β_home + A_v + travel_fatigue_away)
```

The Dixon-Coles correction adjusts the joint probability for low-scoring results:

```
τ(x, y, λ, μ, ρ) =
    1 - λμρ          if x=0, y=0
    1 + λρ           if x=0, y=1
    1 + μρ           if x=1, y=0
    1 - ρ            if x=1, y=1
    1.0              otherwise
```

where ρ (rho) is estimated from historical international match data (typically around −0.13).

#### Dynamic Elo Update

After each simulated match:

```
ΔElo = K × (Actual - Expected)
Expected = 1 / (1 + 10^((Elo_B - Elo_A) / 400))
K = 60  # international matches; higher than club football K-factor
```

Mean reversion after each match:

```
Elo_dynamic_new = Elo_dynamic + γ × (Elo_pretournament - Elo_dynamic)
```

where γ = 0.15 (15% reversion per match toward pre-tournament baseline).

#### Third-Place Advancement Logic

```python
def get_best_third_place_teams(group_standings: dict) -> list[str]:
    all_third_place = [
        group_standings[group][2]  # 3rd place in each group
        for group in "ABCDEFGHIJKL"
    ]
    sorted_third = sorted(
        all_third_place,
        key=lambda t: (t["points"], t["goal_diff"], t["goals_for"]),
        reverse=True
    )
    return [team["team_id"] for team in sorted_third[:8]]
```

---

## 9. Evaluation Strategy

### 9.1 Match Outcome Predictor

| Metric | Target | Rationale |
|---|---|---|
| **Accuracy** | ≥ 57% | Must comfortably exceed random (33.3%) and naive majority-class (52%) baselines |
| **F1-Score (Macro)** | ≥ 0.42 | Macro averaging penalizes failures on the Draw minority class; this metric cannot be gamed by ignoring draws |
| **AUC-ROC (Win class)** | ≥ 0.75 | Measures discrimination ability independent of threshold; target reflects realistic ceiling for football prediction |
| **AUC-ROC (Draw class)** | ≥ 0.58 | Draws are near-random; 0.58 represents meaningful signal above chance |
| **Calibration Error (ECE)** | ≤ 0.04 | Expected Calibration Error; predictions must match observed frequencies within 4% across deciles |
| **vs. Bookmaker Baseline** | Within ±5% on avg | Model-implied probabilities must not diverge materially from Pinnacle consensus odds on average |

**Validation Protocol:** Evaluate exclusively on the 2022 World Cup holdout set (64 matches). Report all metrics stratified by match stage (Group, Knockout) and by bookmaker-implied favourite strength.

### 9.2 xG Model

| Metric | Target | Rationale |
|---|---|---|
| **Log Loss (Cross-Entropy)** | ≤ 0.28 | Primary metric; penalises confident wrong predictions heavily |
| **Brier Score** | ≤ 0.07 | Mean squared probability error; captures overall calibration |
| **Calibration Curve** | Within ±3% at all deciles | 1,000 shots at xG=0.10 must yield ~100 goals ± 30 |
| **AUC-ROC** | ≥ 0.78 | Discrimination ability; higher bar than match outcomes given larger sample |
| **Sum(xG) vs. Actual Goals** | Within ±8% per tournament | Total predicted goals must match total observed goals over a full season holdout |

**Validation Protocol:** Hold out one full season of Understat data (2024–25 season across top-5 leagues) for final evaluation. Do not tune on this season.

### 9.3 Penalty Shootout Model

| Metric | Target | Rationale |
|---|---|---|
| **Log Loss** | ≤ 0.65 | Lower bound given inherent randomness of penalty outcomes |
| **Bayesian Calibration** | Posterior intervals contain observed rate 90% of time | Credible interval coverage is the correct metric for Bayesian models |
| **Conversion Rate vs. Prior** | Posterior mean within ±5% of observed rate by position | Validates positional partial pooling |
| **Team Win% Calibration** | Within ±4% of historical observed shootout win rates | Teams assigned 60% win probability must win ~60% of historical shootouts |

**Validation Protocol:** Leave-one-shootout-out cross-validation on the Fjelstul `penalty_kicks` dataset (all historical World Cup shootouts). For each left-out shootout, predict the outcome using the model fitted on all other shootouts.

### 9.4 Tournament Simulator

| Metric | Target | Rationale |
|---|---|---|
| **Historical Backtest — Champion Probability** | Winner was in top-3 probability teams in ≥ 3 of 4 WC backtests (2010, 2014, 2018, 2022) | Validates structural model plausibility |
| **Probability Calibration — Stage Advancement** | ECE ≤ 0.06 across all stage-advancement predictions | Groups of teams assigned P(QF)=0.30 must reach QF ~30% of the time in backtests |
| **Monte Carlo Convergence** | Champion probability SD < 0.5% across 5 independent 100k-run batches | Ensures statistical stability of simulation output |
| **Brier Score (Stage Advancement)** | ≤ 0.22 | Against historical 2010–2022 stage advancement outcomes |

**Validation Protocol:** Run the full simulation engine against 2014, 2018, and 2022 historical World Cups using only pre-tournament data available before each tournament's opening match. Compare predicted stage-advancement probabilities against observed outcomes.

---

## 10. System Architecture

### 10.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                               │
│  Transfermarkt · Understat · FBref · Fjelstul · Football-Data  │
│  Club Elo · StatsBomb · Reep Register · Covers.com             │
│                         ↓ Dagster                               │
│              Raw Parquet → S3 / Cloudflare R2                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FEATURE LAYER                              │
│           dbt transformations on DuckDB                         │
│  dim_teams · dim_players · dim_venues · dim_entity_map         │
│  fct_matches · fct_shots · fct_penalties                       │
│  feat_match_outcome · feat_xg · feat_penalty                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       MODEL LAYER                               │
│  HistGBM Match Outcome   →  Platt Calibration                  │
│  XGBoost xG Model        →  Isotonic Calibration               │
│  PyMC Bayesian Penalty   →  MCMC Posterior                     │
│  Serialized: joblib / xgb.save_model / ArviZ NetCDF            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    SIMULATION LAYER                             │
│  Bivariate Poisson + Dixon-Coles Scoreline Generator            │
│  Monte Carlo Engine (100,000 iterations · 8 cores)             │
│  Dynamic Elo Updater + Mean Reversion                           │
│  Third-Place Advancement Logic                                  │
│  Penalty Shootout Simulator (Bayesian draw)                     │
│  Output: team_stage_probabilities · golden_boot_distribution   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        API LAYER                                │
│              FastAPI · Uvicorn · DuckDB queries                 │
│  /predictions/winner · /predictions/match/{id}                  │
│  /predictions/xg · /predictions/penalty                         │
│  /players/golden-boot · /teams/{id}/stage-probs                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND LAYER                              │
│           React + Vite · TailwindCSS · Recharts                │
│  Dashboard · Match Predictor · xG Sandbox · Penalty Sandbox    │
│  Bracket Explorer · Golden Boot Dashboard                       │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Data Layer

All raw data is ingested via Python scripts orchestrated by **Dagster**. Each data source has a dedicated Dagster asset with:
- A `freshness_policy` that enforces a June 6, 2026 freeze
- A `metadata` block recording row counts, schema hash, and ingestion timestamp
- A `check` step that validates non-null rates on critical columns

Raw data is stored as partitioned **Parquet files** on S3 (or Cloudflare R2 for cost efficiency), partitioned by `source_name / ingestion_date`.

### 10.3 Feature Layer

**dbt** manages all SQL transformations on DuckDB. The dbt project follows a medallion architecture:

- `stg_*` models: Raw source normalization (type casting, null handling, Reep ID joining)
- `int_*` models: Intermediate business logic (Haversine computation, differential calculation)
- `dim_*` models: Final dimension tables (teams, players, venues, entity map)
- `fct_*` models: Fact tables (matches, shots, penalties)
- `feat_*` models: ML-ready feature tables (one row per training example)

### 10.4 Model Layer

All models are serialized after training:
- HistGBM pipeline: `joblib.dump(match_pipeline, "models/match_outcome_v1.pkl")`
- XGBoost model: `xg_model.save_model("models/xg_model_v1.ubj")`
- PyMC trace: `az.to_netcdf(trace, "models/penalty_trace_v1.nc")`

Model artifacts are versioned with semantic tags (e.g., `v1.0.0`) and stored in a model registry (MLflow or a simple S3 bucket with a `models.json` manifest).

### 10.5 Simulation Layer

The Monte Carlo engine is a standalone Python module (`src/simulator/`) that:
- Reads pre-tournament feature tables from DuckDB at initialization
- Loads all three serialized model artifacts
- Runs 100,000 simulations using `multiprocessing.Pool`
- Writes output tables back to DuckDB on completion

The simulation must be deterministic given a fixed random seed for reproducibility.

### 10.6 API Layer

FastAPI application (`src/api/`) with:
- DuckDB connection pool for sub-100ms query latency on pre-computed simulation tables
- Model inference endpoints that load serialized models on startup and keep them in memory
- Redis cache layer for frequently requested match predictions (TTL: indefinite, frozen at launch date)
- OpenAPI/Swagger documentation auto-generated at `/docs`

### 10.7 Frontend Layer

React application (`src/frontend/`) with:
- Vite build toolchain
- TailwindCSS for styling
- Recharts for probability bar charts and calibration plots
- react-bracket for the tournament bracket explorer
- Deployed to Vercel or Cloudflare Pages

---

## 11. Database Design

All tables reside in DuckDB. Schema uses snake_case naming. Primary keys are denoted `PK`; foreign keys are denoted `FK`.

### `dim_teams`

| Column | Type | Description |
|---|---|---|
| `reep_team_id` PK | `VARCHAR` | Canonical team identifier |
| `team_name_canonical` | `VARCHAR` | Official canonical name |
| `confederation` | `VARCHAR` | FIFA confederation |
| `group_code` | `CHAR(1)` | Group A–L |
| `is_host_nation` | `BOOLEAN` | USA / CAN / MEX |
| `pretournament_elo` | `FLOAT` | Club Elo rating at freeze date |
| `squad_market_value_eur` | `BIGINT` | Total squad Transfermarkt valuation (€) |
| `avg_squad_age` | `FLOAT` | Mean squad age |
| `avg_squad_height_cm` | `FLOAT` | Mean squad height |
| `total_caps` | `INTEGER` | Sum of international caps across squad |
| `historic_fifa_points` | `FLOAT` | Rolling 5-year FIFA points total |
| `tm_team_id` | `VARCHAR` | FK → Transfermarkt |
| `fbref_team_id` | `VARCHAR` | FK → FBref |

### `dim_players`

| Column | Type | Description |
|---|---|---|
| `reep_player_id` PK | `VARCHAR` | Canonical player identifier |
| `reep_team_id` FK | `VARCHAR` | FK → dim_teams |
| `player_name_canonical` | `VARCHAR` | Normalized player name |
| `position` | `VARCHAR` | Forward / Midfielder / Defender / Goalkeeper |
| `age` | `INTEGER` | Age as of June 6, 2026 |
| `height_cm` | `INTEGER` | Player height |
| `market_value_eur` | `INTEGER` | Individual market value (Transfermarkt) |
| `international_caps` | `INTEGER` | Career international appearances |
| `international_goals` | `INTEGER` | Career international goals |
| `bayesian_penalty_conversion` | `FLOAT` | Posterior mean conversion rate |
| `bayesian_penalty_conversion_sd` | `FLOAT` | Posterior standard deviation |
| `bayesian_gk_save_rate` | `FLOAT` | Posterior mean save rate (GKs only) |
| `offensive_rapm` | `FLOAT` | RAPM offensive rating |
| `xg_per_90` | `FLOAT` | Career xG per 90 minutes |
| `tm_player_id` | `VARCHAR` | FK → Transfermarkt |
| `fbref_player_id` | `VARCHAR` | FK → FBref |
| `understat_player_id` | `VARCHAR` | FK → Understat |

### `dim_venues`

| Column | Type | Description |
|---|---|---|
| `venue_id` PK | `VARCHAR` | Unique venue identifier |
| `stadium_name` | `VARCHAR` | Official stadium name |
| `city` | `VARCHAR` | Host city |
| `host_nation` | `VARCHAR` | USA / CAN / MEX |
| `latitude` | `FLOAT` | GPS latitude |
| `longitude` | `FLOAT` | GPS longitude |
| `altitude_m` | `INTEGER` | Altitude above sea level |
| `capacity` | `INTEGER` | Stadium capacity |

### `fct_matches`

| Column | Type | Description |
|---|---|---|
| `match_id` PK | `VARCHAR` | Unique match identifier |
| `home_team_id` FK | `VARCHAR` | FK → dim_teams |
| `away_team_id` FK | `VARCHAR` | FK → dim_teams |
| `venue_id` FK | `VARCHAR` | FK → dim_venues |
| `match_date` | `DATE` | Scheduled match date |
| `stage` | `VARCHAR` | group / r32 / r16 / qf / sf / final |
| `group_code` | `CHAR(1)` | Group code (group stage only) |
| `home_goals_actual` | `INTEGER` | Actual home goals (NULL before match) |
| `away_goals_actual` | `INTEGER` | Actual away goals (NULL before match) |
| `went_to_extra_time` | `BOOLEAN` | Did match go to AET? |
| `went_to_penalties` | `BOOLEAN` | Did match go to penalties? |
| `penalty_winner_team_id` FK | `VARCHAR` | FK → dim_teams (if applicable) |

### `fct_shots`

| Column | Type | Description |
|---|---|---|
| `shot_id` PK | `VARCHAR` | Unique shot identifier |
| `match_id` FK | `VARCHAR` | FK → fct_matches |
| `player_id` FK | `VARCHAR` | FK → dim_players (reep_player_id) |
| `team_id` FK | `VARCHAR` | FK → dim_teams |
| `minute` | `INTEGER` | Match minute |
| `shot_x` | `FLOAT` | X pitch coordinate |
| `shot_y` | `FLOAT` | Y pitch coordinate |
| `distance_to_goal_m` | `FLOAT` | Derived Euclidean distance |
| `angle_to_goal_deg` | `FLOAT` | Derived visible angle |
| `situation` | `VARCHAR` | open_play / free_kick / corner / penalty |
| `body_part` | `VARCHAR` | right_foot / left_foot / head |
| `defenders_in_cone` | `INTEGER` | From freeze-frame (NULL if unavailable) |
| `defensive_pressure_m` | `FLOAT` | Distance to nearest defender |
| `xg_model_output` | `FLOAT` | Platform's trained XGBoost xG value |
| `outcome` | `VARCHAR` | goal / saved / blocked / missed |
| `source` | `VARCHAR` | understat / statsbomb |

### `fct_penalties`

| Column | Type | Description |
|---|---|---|
| `penalty_id` PK | `VARCHAR` | Unique penalty identifier |
| `match_id` FK | `VARCHAR` | FK → fct_matches |
| `taker_player_id` FK | `VARCHAR` | FK → dim_players |
| `goalkeeper_player_id` FK | `VARCHAR` | FK → dim_players |
| `kick_sequence_number` | `INTEGER` | Position in shootout (1–N) |
| `converted` | `BOOLEAN` | Was the penalty scored? |
| `saved` | `BOOLEAN` | Did the goalkeeper save? |
| `minute` | `INTEGER` | Match minute (shootout = 120+) |
| `is_shootout` | `BOOLEAN` | In-game penalty (FALSE) vs. shootout (TRUE) |
| `source` | `VARCHAR` | fjelstul / understat / fbref |

### `team_stage_probabilities`

| Column | Type | Description |
|---|---|---|
| `reep_team_id` FK | `VARCHAR` | FK → dim_teams |
| `sim_run_id` | `VARCHAR` | Simulation batch identifier |
| `p_group_advance` | `FLOAT` | P(advancing from group) |
| `p_r32` | `FLOAT` | P(reaching Round of 32) |
| `p_r16` | `FLOAT` | P(reaching Round of 16) |
| `p_qf` | `FLOAT` | P(reaching Quarterfinal) |
| `p_sf` | `FLOAT` | P(reaching Semifinal) |
| `p_final` | `FLOAT` | P(reaching Final) |
| `p_champion` | `FLOAT` | P(winning the tournament) |
| `p_group_1st` | `FLOAT` | P(finishing 1st in group) |
| `p_group_2nd` | `FLOAT` | P(finishing 2nd in group) |
| `p_group_3rd_advance` | `FLOAT` | P(advancing as best 3rd place) |
| `n_simulations` | `INTEGER` | Number of iterations in this run |
| `computed_at` | `TIMESTAMP` | Simulation completion timestamp |

### `golden_boot_distribution`

| Column | Type | Description |
|---|---|---|
| `reep_player_id` FK | `VARCHAR` | FK → dim_players |
| `sim_run_id` | `VARCHAR` | Simulation batch identifier |
| `mean_goals` | `FLOAT` | Mean simulated goal total |
| `p10_goals` | `FLOAT` | 10th percentile goal total |
| `p50_goals` | `FLOAT` | Median goal total |
| `p90_goals` | `FLOAT` | 90th percentile goal total |
| `p_golden_boot` | `FLOAT` | P(winning Golden Boot outright) |
| `expected_minutes` | `FLOAT` | Mean simulated minutes played |

---

## 12. API Design

All endpoints return `application/json`. All responses include a `meta` object with `model_version`, `computed_at`, and `prediction_freeze_date: "2026-06-06"`.

Base URL: `https://api.wc2026predict.com/v1`

---

### `GET /predictions/winner`

Returns champion probability for all 48 teams from the Monte Carlo simulation.

**Response Schema:**

```json
{
  "meta": { "model_version": "1.0.0", "n_simulations": 100000 },
  "teams": [
    {
      "reep_team_id": "tm_fra",
      "team_name": "France",
      "p_champion": 0.174,
      "p_final": 0.312,
      "p_sf": 0.481,
      "p_qf": 0.631,
      "p_r16": 0.789,
      "p_group_advance": 0.921
    }
  ]
}
```

---

### `GET /predictions/match/{match_id}`

Returns Win/Draw/Loss probabilities and top scorelines for a specific scheduled fixture.

**Path Parameters:** `match_id` (string)

**Response Schema:**

```json
{
  "meta": { "model_version": "1.0.0" },
  "match_id": "wc2026_A01",
  "team_a": { "reep_team_id": "tm_usa", "name": "United States" },
  "team_b": { "reep_team_id": "tm_srb", "name": "Serbia" },
  "probabilities": {
    "team_a_win": 0.412,
    "draw": 0.271,
    "team_b_win": 0.317
  },
  "team_a_xg": 1.43,
  "team_b_xg": 1.21,
  "most_likely_scorelines": [
    { "score": "1-1", "probability": 0.112 },
    { "score": "2-1", "probability": 0.094 },
    { "score": "1-0", "probability": 0.089 },
    { "score": "0-1", "probability": 0.081 },
    { "score": "2-0", "probability": 0.076 }
  ],
  "key_features": {
    "squad_value_diff_eur": 280000000,
    "elo_diff": 42.1,
    "team_a_travel_km": 0,
    "altitude_diff_m": 0
  }
}
```

---

### `GET /predictions/match/custom`

Computes a match prediction for any two arbitrary teams (not necessarily on the schedule).

**Request Body:**

```json
{
  "team_a_id": "tm_bra",
  "team_b_id": "tm_arg",
  "venue_id": "v_metlife",
  "match_context": "sf"
}
```

**Response:** Same schema as `/predictions/match/{match_id}`.

---

### `POST /predictions/xg`

Computes xG for a described shot scenario.

**Request Body:**

```json
{
  "shot_x": 89.3,
  "shot_y": 51.2,
  "situation": "open_play",
  "body_part": "right_foot",
  "defenders_in_cone": 1,
  "defensive_pressure_m": 2.1
}
```

**Response Schema:**

```json
{
  "xg_value": 0.187,
  "shot_danger_class": "medium",
  "distance_to_goal_m": 10.8,
  "angle_to_goal_deg": 28.4,
  "top_features": ["distance_to_goal_m", "angle_to_goal_deg", "defenders_in_cone"]
}
```

---

### `POST /predictions/penalty`

Simulates a penalty shootout between two teams.

**Request Body:**

```json
{
  "team_a_id": "tm_eng",
  "team_b_id": "tm_fra",
  "n_simulations": 10000
}
```

**Response Schema:**

```json
{
  "team_a_shootout_win_pct": 0.463,
  "team_b_shootout_win_pct": 0.537,
  "team_advantage": "team_b",
  "advantage_magnitude": 0.074,
  "top_takers": {
    "team_a": [
      { "player_name": "Harry Kane", "bayesian_conversion_rate": 0.834, "caps": 98 }
    ],
    "team_b": [
      { "player_name": "Kylian Mbappé", "bayesian_conversion_rate": 0.811, "caps": 102 }
    ]
  },
  "sample_sequences": []
}
```

---

### `GET /players/golden-boot`

Returns the Golden Boot probability distribution for all projected starters.

**Query Parameters:** `limit` (int, default 20), `min_p_champion` (float, filter by team champion probability)

**Response Schema:**

```json
{
  "players": [
    {
      "reep_player_id": "pl_mba001",
      "player_name": "Kylian Mbappé",
      "team": "France",
      "p_golden_boot": 0.062,
      "mean_goals": 3.41,
      "p50_goals": 3.0,
      "p90_goals": 7.0,
      "expected_minutes": 534
    }
  ]
}
```

---

### `GET /teams/{team_id}/stage-probs`

Returns full stage probability breakdown for a specific team.

**Response Schema:**

```json
{
  "reep_team_id": "tm_bra",
  "team_name": "Brazil",
  "stage_probabilities": {
    "group_advance": 0.934,
    "r32": 0.891,
    "r16": 0.782,
    "quarterfinal": 0.634,
    "semifinal": 0.489,
    "final": 0.312,
    "champion": 0.158
  },
  "group_finish_distribution": {
    "1st": 0.671,
    "2nd": 0.241,
    "3rd_advance": 0.022,
    "eliminated": 0.066
  }
}
```

---

### `GET /health`

Returns API health status and model readiness.

```json
{
  "status": "ok",
  "models_loaded": {
    "match_outcome": true,
    "xg": true,
    "penalty": true
  },
  "simulation_complete": true,
  "prediction_freeze_date": "2026-06-06"
}
```

---

## 13. Frontend Requirements

### 13.1 Dashboard (Home Page)

The landing page presents the key tournament snapshot at a glance:

- **Champion Probability Bar Chart:** Horizontal bar chart of all 48 teams sorted by `p_champion`. Colour-coded by confederation. Top 10 teams labeled.
- **Top 5 Golden Boot Candidates:** Card row with player photo (where available), team flag, mean expected goals, and P(Golden Boot).
- **Prediction Freeze Banner:** Prominent notice stating all predictions are frozen as of June 6, 2026.
- **Quick Match Navigator:** Search box allowing users to select any scheduled match and jump to the Match Predictor.
- **Model Accuracy Summary:** Backtesting performance card (57.8% accuracy on 2022 WC holdout, AUC 0.76).

### 13.2 Match Predictor

An interactive page for exploring head-to-head match predictions:

- **Team Selector:** Dropdown or search-as-you-type for both Team A and Team B from the 48 qualified nations.
- **Venue Selector:** Dropdown for the 16 tournament venues (auto-populates altitude and Haversine distance for selected teams).
- **Stage Selector:** Dropdown for match context (Group / R32 / R16 / QF / SF / Final).
- **Probability Donut Chart:** Three-segment donut showing Win%/Draw%/Loss% with animated transitions.
- **Scoreline Probability Table:** Top 5 scorelines rendered as a ranked card list with probability percentages.
- **Feature Breakdown Sidebar:** Expandable panel showing the key features that drove this prediction (squad value differential, Elo gap, altitude, travel distance).
- **Bookmaker Comparison Row:** For scheduled fixtures, display the platform's implied odds alongside Pinnacle consensus odds.

### 13.3 xG Sandbox

An interactive tool allowing users to place a shot on a pitch diagram and see the computed xG:

- **Pitch Canvas:** SVG football pitch diagram with click-to-place shot location. Renders X/Y coordinates on click.
- **Context Controls:** Dropdowns for `situation` and `body_part`; sliders for `defenders_in_cone` (0–5) and `defensive_pressure_m` (0–10m).
- **Real-time xG Display:** Large xG value (0.00–1.00) and `shot_danger_class` badge update on every click or control change (debounced API call, 300ms).
- **Pitch Heatmap Mode:** Toggle to display a precomputed xG heatmap overlaid on the pitch for open-play right-foot shots (default context).
- **Feature Attribution:** Small bar chart showing SHAP-derived feature importances for the current shot scenario.

### 13.4 Penalty Sandbox

An interactive shootout simulation tool:

- **Team Selector:** Two team dropdowns (defaults to any knockout-stage pairing).
- **Shootout Win % Gauge:** Animated gauge chart updating Team A and Team B win probabilities.
- **Taker Card Grid:** 5 taker cards per team showing player name, Bayesian conversion rate, and position, in shootout order.
- **Goalkeeper Card:** Single card per team showing GK name and Bayesian save rate.
- **Simulate Button:** Triggers a live single-sequence simulation displayed kick-by-kick with animated outcome icons (⚽ or ✗).
- **Uncertainty Ribbon:** Credible interval ribbon around each player's Bayesian conversion rate, illustrating confidence.

### 13.5 Tournament Bracket Explorer

An interactive 48-team bracket visualization:

- **Full Bracket Canvas:** Horizontally scrollable bracket from Group Stage through Final, showing all 104 match slots.
- **Team Probability Colour Coding:** Each bracket slot is colour-coded by P(advancement) for the team most likely to fill it.
- **Click-to-Drill:** Clicking any match slot opens a drawer showing the Match Predictor output for that fixture.
- **Team Filter:** Search/select a team to highlight their most probable path through the bracket, with stage probabilities labeled at each node.
- **Group Table View:** Toggle to show simulated group finish distributions (P(1st)/P(2nd)/P(3rd)/P(4th)) for all 12 groups.

### 13.6 Golden Boot Dashboard

A dedicated player-level page:

- **Ranked Leaderboard Table:** Players ranked by `p_golden_boot`, showing team, position, mean goals, p10/p50/p90 goal range, and expected minutes.
- **Goal Distribution Chart:** Violin chart for top 10 candidates showing the full simulated goal distribution.
- **Team Stage Filter:** Filter players by their team's minimum P(QF) or P(SF) to surface candidates from teams likely to play more matches.
- **Player Card Modal:** Clicking a player opens a card with full stats: caps, xG per 90, Bayesian penalty conversion rate, and a simulation path summary.

---

## 14. Risks and Limitations

### 14.1 Data Gaps

**Risk:** The Reep Entity Register may be incomplete for squads from smaller confederations (OFC, lower-ranked CAF/CONCACAF nations), leading to entity resolution failures and missing squad market values.

**Mitigation:** Implement fallback fuzzy matching; flag all teams with missing market values for manual data entry before freeze date. Any team with a null squad market value at freeze time will have the global mean imputed and flagged with a `data_quality: imputed` warning in all API responses.

**Risk:** Understat coverage excludes certain qualifying competitions and international friendlies, reducing training data volume for squads from outside the top European leagues.

**Mitigation:** Supplement with FBref and StatsBomb Open Data. Accept lower xG confidence intervals for players from lower-data squads; expose uncertainty levels in the API response.

### 14.2 Penalty Sample Size

The Fjelstul database contains only 396 World Cup shootout kicks — an extremely small corpus for any statistical model. Training a non-Bayesian model on this dataset would produce wildly unreliable estimates.

**Mitigation:** The Bayesian hierarchical model is specifically architected for this constraint. Partial pooling toward positional priors ensures that players with zero or one historical penalty observation receive conservative, plausible estimates rather than extreme values. All penalty predictions should be presented with explicit credible intervals to communicate this uncertainty.

Even with the Bayesian architecture, predictions for sudden-death kicks (6–11) are primarily driven by positional priors alone for most defenders, who have no penalty history. This must be disclosed prominently in the frontend.

### 14.3 International Football Randomness

International football is a uniquely high-variance sport. The model's theoretical accuracy ceiling — based on the information-theoretic entropy of match outcomes — is approximately 62–65% given available public data. The gap between this ceiling and the platform's 57–58% accuracy represents irreducible aleatoric uncertainty driven by random events (referee decisions, in-match injuries, deflections) that no dataset can capture.

**Communication Strategy:** The frontend must never present predictions as certainties. All outputs must include probability distributions, not point predictions. Framing: "France has a 17.4% chance of winning the tournament" — not "France will win."

### 14.4 The 2026 Format Is Unprecedented

The 48-team, 12-group format with "best third-place" advancement and 104 matches has never been played at a World Cup. All historical backtesting is conducted on 32-team tournaments, meaning the simulator's structural rules cannot be validated against direct precedent.

**Mitigation:** The `zvizdo/fifa-wc-2026-simulation` framework provides a pre-validated mathematical mapping of the 48-team structure. Independent structural logic testing must be performed against the official FIFA tournament regulations document before launch.

### 14.5 Frozen Predictions During a Live Tournament

By design, no model retraining or squad updates occur after June 6, 2026. A major pre-tournament injury to a key player announced on June 7 will not be reflected in the platform's predictions.

**Communication Strategy:** The prediction freeze banner on the frontend must state clearly: "These predictions are based exclusively on publicly available information as of June 6, 2026. No in-tournament updates are made." This must be present on every page and in every API response's `meta` object.

### 14.6 Missing Freeze-Frame Features

StatsBomb freeze-frame data (goalkeeper position, defenders in cone) is not available for all historical shots. Approximately 40–60% of the xG training set may lack freeze-frame features.

**Mitigation:** When freeze-frame features are missing, use `SimpleImputer(strategy="median")` fitted on the training set. The `top_features` array in the xG API response will indicate when the prediction relies on imputed contextual features.

---

## 15. Validation and Launch Checklist

### 15.1 Data Layer Validation

- [ ] All 48 qualified nations have a non-null entry in `dim_teams` with a verified `reep_team_id`
- [ ] All 48 teams have a non-null `squad_market_value_eur` and `pretournament_elo`
- [ ] All 16 venues have non-null `latitude`, `longitude`, and `altitude_m`
- [ ] The `travel_matrix` (16×16) contains non-null Haversine distances for all venue pairs
- [ ] Entity resolution audit table contains zero unresolved conflicts for the 48 qualified nations
- [ ] All 396 historical World Cup penalty kicks from the Fjelstul database loaded into `fct_penalties`
- [ ] Understat shot dataset covers at least 8 seasons and 800,000 shots
- [ ] FBref squad statistics loaded for all 48 nations' qualifying campaigns
- [ ] Club Elo ratings loaded for all 48 nations as of June 6, 2026
- [ ] Bookmaker odds loaded for at least the last 3 World Cup tournaments for holdout validation

### 15.2 Feature Engineering Validation

- [ ] `distance_to_goal_m` and `angle_to_goal_deg` are non-null for all shots in `fct_shots`
- [ ] All match-level differentials (`squad_value_diff`, `elo_diff`, etc.) are non-null for all 104 scheduled matches
- [ ] `rest_day_asymmetry` is computed correctly for the group stage schedule
- [ ] Altitude differential is correctly signed (positive = team playing at higher altitude than native)
- [ ] No feature in `feat_match_outcome` has a null rate exceeding 5%

### 15.3 Model Training Validation

- [ ] HistGBM Match Outcome model achieves ≥ 57% accuracy on 2022 WC holdout
- [ ] Match Outcome model AUC-ROC ≥ 0.75 on Win class on holdout
- [ ] Match Outcome calibration curve lies within ±4% of diagonal across all deciles
- [ ] XGBoost xG model achieves Log Loss ≤ 0.28 on held-out 2024–25 season
- [ ] xG model sum(xG) vs. actual goals within ±8% on 2024–25 holdout season
- [ ] Bayesian Penalty model posterior means are within ±5% of observed positional conversion rates
- [ ] Penalty model leave-one-shootout-out calibration is within ±4% of observed shootout win rates
- [ ] All three models are serialized and version-tagged in the model registry

### 15.4 Simulation Validation

- [ ] Simulator correctly implements the 48-team group stage with 12 groups of 4
- [ ] Third-place advancement logic correctly selects top 8 from 12 third-place finishers by Points → GD → GF
- [ ] Knockout bracket pathing matches official FIFA 2026 format specification
- [ ] Champion probability standard deviation < 0.5% across 5 independent 100k-run batches
- [ ] Historical backtest: 2014/2018/2022 WC champion was in top-3 probability teams in ≥ 3 of 3 backtests
- [ ] Total simulated goals across 104 matches is within ±5% of historical 48-team scaling projection

### 15.5 API Validation

- [ ] All endpoints return HTTP 200 with valid JSON for all 48 teams
- [ ] `/health` endpoint confirms all three models are loaded and simulation is complete
- [ ] P95 response time ≤ 400 ms for all prediction endpoints under simulated 100-concurrent-user load
- [ ] Win% + Draw% + Loss% sums to 1.00 ± 0.001 in all `/predictions/match` responses
- [ ] All responses include `prediction_freeze_date: "2026-06-06"` in `meta` object
- [ ] OpenAPI schema is published at `/docs` and passes schema validation

### 15.6 Frontend Validation

- [ ] Dashboard loads in ≤ 2.5 s on a simulated 4G connection
- [ ] Prediction freeze banner is visible on all pages without scrolling
- [ ] Match Predictor returns correct output for all 104 scheduled fixtures
- [ ] xG Sandbox heatmap renders without error across all browsers (Chrome, Firefox, Safari)
- [ ] Tournament bracket correctly displays all 48 teams in their assigned groups
- [ ] Golden Boot leaderboard is sortable by all columns
- [ ] All probability values displayed to 1 decimal place (e.g., "17.4%") — never as false-precision decimals (e.g., "17.413%")

### 15.7 Communication and Legal

- [ ] Model cards published for all three ML models (training data, features, limitations)
- [ ] Data lineage documentation published for all 9 datasets
- [ ] Prediction freeze date prominently disclosed on all pages and in all API responses
- [ ] Legal review of data usage terms for Football-Data.co.uk, Understat, and FBref completed

---

## 16. Future Roadmap

### Phase 2: Live Tournament Updates (Post-Launch)

**Target:** Available within 48 hours of the tournament opening match.

Enable the platform to ingest live tournament results and update team strength ratings in near-real-time. Key changes:

- Replace the static Monte Carlo simulation outputs with a live re-simulation pipeline triggered after each match concludes
- Integrate a live match data feed (official FIFA API or StatsBomb Live) to update group standings and dynamic Elo ratings
- Build a `live_simulation_scheduler` Dagster job that triggers a 10,000-iteration re-simulation within 30 minutes of each full-time whistle
- Add a `simulation_type: live` flag to all API responses and a "Last Updated" timestamp to the frontend dashboard
- All pre-tournament predictions preserved and viewable in a "Pre-Tournament Forecast" tab for comparison

### Phase 3: Injury and Squad News Integration

**Target:** 4 weeks post-tournament.

Integrate a structured injury and squad news feed to automatically adjust squad market values and key player ratings when major absences are confirmed.

- Partner with or scrape a structured injury feed (e.g., TransfermarktInjuries, SkySports squad news)
- Build a `squad_impact_adjuster` module that recomputes team strength when a player's `is_available` flag changes
- Implement a "Shock Scenario" simulator allowing users to model tournament outcomes with a specified player removed
- Expose an `injury_scenario` query parameter on the Match Predictor endpoint

### Phase 4: Real-Time Prediction Engine

**Target:** 6 months post-tournament.

Extend the platform to support in-play win probability updates for live matches.

- Ingest live event streams at 1-second granularity (shots, goals, red cards, substitutions)
- Build an in-play HistGBM model trained on live match state features (current score, minute, recent xG flow, player-count differential)
- Update win probability every 60 seconds during live matches; expose via WebSocket endpoint
- Design the probability curve visualization with a time-series graph showing win probability evolution through the match

### Phase 5: Advanced Player Chemistry Models

**Target:** 12 months post-tournament; pre-2027 Nations League.

Replace the simple `shared_club_minutes` proxy for squad chemistry with a graph-based player synergy model.

- Build a bipartite graph connecting players via shared club team membership, weighted by co-participation minutes
- Compute a `joint_offensive_impact` (JOI) score for player pairs who most frequently combine in the same team's attack
- Train a Graph Neural Network (GNN) on StatsBomb event sequences to learn positional synergy weights from passing and movement data
- Integrate JOI pair scores as additional features in the Match Outcome Predictor
- Extend the Golden Boot model to account for assist probability and shot-creation contribution, not just finishing rates

---

*Document Version 1.0 · Prepared June 6, 2026 · Prediction Freeze Date: June 6, 2026*  
*All models are frozen. No post-freeze updates are incorporated into platform predictions.*
