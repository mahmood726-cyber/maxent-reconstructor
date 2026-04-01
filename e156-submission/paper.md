Mahmood Ahmad
Tahir Heart Institute
author@example.com

MaxEnt IPD Reconstructor: Maximum Entropy Recovery of Individual Patient Data

Can maximum entropy reconstruction recover individual patient data from summary statistics more accurately than naive normal assumptions for skewed distributions? We implemented a five-stage optimization algorithm constraining reconstructed samples to match reported mean, standard deviation, minimum, maximum, and sample size while maximizing distributional entropy across bounded support. The method sequentially attempts root-finding, least-squares, Nelder-Mead, approximate relaxation, and truncated normal fallback, returning diagnostics including Kolmogorov-Smirnov statistics and quantile concordance across five percentile levels. In 333 simulations of lognormal data the median error was reduced by 76.6 percent at distribution tails, yielding a 94.9 percent win rate with 95% CI 92.1 to 97.0 over naive normal reconstruction. Comparison with the R IPDfromAGD package across 50 benchmark scenarios showed MaxEnt winning all comparisons with 77.8 percent mean error reduction. The reconstructor is deterministic with a fixed random seed and integrates directly into meta-analytic pipelines requiring individual-level inputs. Performance advantage is limited for near-symmetric distributions where normal assumptions already hold.

Outside Notes

Type: methods
Primary estimand: Win rate vs normal
App: MaxEnt IPD Reconstructor v1.0
Data: 333 lognormal simulations, 50 IPDfromAGD benchmarks
Code: https://github.com/mahmood726-cyber/maxent-reconstructor
Version: 1.0
Validation: DRAFT

References

1. Riley RD, Lambert PC, Abo-Zaid G. Meta-analysis of individual participant data: rationale, conduct, and reporting. BMJ. 2010;340:c221.
2. Stewart LA, Tierney JF. To IPD or not to IPD? Advantages and disadvantages of systematic reviews using individual patient data. Eval Health Prof. 2002;25(1):76-97.
3. Borenstein M, Hedges LV, Higgins JPT, Rothstein HR. Introduction to Meta-Analysis. 2nd ed. Wiley; 2021.

AI Disclosure

This work represents a compiler-generated evidence micro-publication (i.e., a structured, pipeline-based synthesis output). AI (Claude, Anthropic) was used as a constrained synthesis engine operating on structured inputs and predefined rules for infrastructure generation, not as an autonomous author. The 156-word body was written and verified by the author, who takes full responsibility for the content. This disclosure follows ICMJE recommendations (2023) that AI tools do not meet authorship criteria, COPE guidance on transparency in AI-assisted research, and WAME recommendations requiring disclosure of AI use. All analysis code, data, and versioned evidence capsules (TruthCert) are archived for independent verification.
