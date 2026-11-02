# 14. Metastability injection: Dr. RTL's axil_cdc rewrite tears transactions; the original never does

**Status: SUPPORTED (1 design, 10 seeds).** Source: experiments/05_metastability/ (README, results.txt).
Under the standard RTL metastability-injection model (applied identically to both designs), 2000 random AXI-Lite
writes: original 0 corrupted address/data words in all 10 seeds; Dr. RTL's promoted rewrite 1430-1583 of 4000 (~37 %).
Without injection both are perfect (as EQY and simulation say). Worst-case injection: shows the failure mode, not its
silicon rate. Strengthens finding 11 (the paper's headline example).
