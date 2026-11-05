# Machine 2 notes

## 2026-11-03 — environment check failed; run anyway at the user's request
Machine 2: Linux x86-64 (Arch), Yosys 0.66 (git sha1 86f2ddebc), yosys-abc built locally (ABC 1.01),
OpenSTA 3.1.0, z3 5.1.0, sby/eqy (local), Icarus 13.0, Verilator 5.052, Claude Code 2.1.312, Python 3.14.8.
`check_env.py` result: 7/10 OK, 3 MISMATCH:
- drrtl_uart: wns -0.65/-0.65 tns -24.15/-24.24 area 800.926/762.622
- drrtl_communication: wns -0.42/-0.43 tns -29.46/-30.72 area 803.32/816.088
- afifo: wns -0.15/-0.15 tns -11.16/-11.21 area 1341.172/1341.172
The user decided to proceed with the installed tools (no exact Yosys build). The queue in
run_machine2.sh was run unchanged except for skipping check_env.py (local wrapper outside the repo).
Results from this machine therefore use Yosys 0.66, not the reference 0.67 commit; baselines of the three
designs above differ from machine 1's.

## 2026-11-03 — network outage stopped the queue (not a code problem)
Around 15:00 IST this machine lost DNS/internet. `drrtl_i2c/aegis.sonnet-5-5.r1` failed after 2528 s with
`aegis_llm.LLMError: LLM call failed after 3 attempts: claude-cli error: API Error: Can't reach the API server — check your internet or DNS (EAI_AGAIN)`.
Then all 5 `drrtl` runs and all 4 `no_guards` runs failed the backend preflight within 126 s each:
`LLM backend unavailable, run not started: ... timed out after 120 seconds`.
run_matrix.sh stopped ("remaining failures are not usage-limit failures"). Finished and valid
(`validate_runs.py` reports nothing invalid): aegis on drrtl_ticket_machine, drrtl_controller, drrtl_uart,
drrtl_communication, drrtl_simple_spi (simple_spi stopped itself after iteration 4: "nothing to dispatch").
16:11 IST: network back (`claude -p "say ok"` answers). Queue restarted unchanged; finished runs are skipped and
the failed runs restart from scratch (aegis_run.py/drrtl_port.py wipe a run dir without summary.json).

## 2026-11-03 — drrtl_i2c/aegis lost 1 candidate to a short network drop; flagged INVALID
16:24–18:04 IST the queue waited out the Claude 5-hour limit ("You've hit your 5-hour limit · resets 6pm"),
as designed. The i2c aegis re-run started 18:04 and finished ok at 20:19 (8117 s, 5 iterations, final v5), but
one candidate (region r_4b58839be6, slot C5, t≈2070 s, about 18:39 IST) failed with
`LLM call failed after 3 attempts: claude-cli error: API Error: Can't reach the API server — check your internet or DNS (EAI_AGAIN)`.
`validate_runs.py` reports `INVALID drrtl_i2c/aegis.sonnet-5-5.r1: 1 llm_error candidates, 1 LLM-failure log lines`.
Per the rules it is not rescued: the queue's final `validate_runs.py --archive` moves it to
flow/runs_archive/invalid/, and it has to be re-run (re-start the queue after it finishes).
Run dir sizes: i2c work/ is 1.6 GB (others 26–487 MB); disk 13 GB free at 20:20.

## 2026-11-03 — drrtl_controller/drrtl lost 20/25 candidates to the 5-hour limit; archived
drrtl_controller/drrtl finished "ok" at about 20:46 (629 s) but 20 candidates failed with
`LLM call failed after 3 attempts: claude-cli error: You've hit your 5-hour limit · resets 11pm (Asia/Kolkata)`
(drrtl_port.py writes summary.json even when candidates are lost, so run_matrix.sh would skip it).
23:01 IST, while the driver slept between passes (no run active): ran `bench/validate_runs.py --archive`, which
moved drrtl_controller/drrtl.sonnet-5-5.r1 and drrtl_i2c/aegis.sonnet-5-5.r1 (see the entry above) to
flow/runs_archive/invalid/. The drrtl driver re-runs controller on its next pass; i2c/aegis needs the queue to be
restarted after it finishes (its Exp 01 aegis stage is already done).

## 2026-11-04 — drrtl_communication/drrtl kept as DEGRADED (1/25 candidates lost)
drrtl_controller/drrtl re-run finished ok 2026-11-03 23:42 (valid). drrtl_communication/drrtl finished ok at about
00:14 (1875 s); one candidate failed with
`LLM call failed after 3 attempts: claude-cli error: You've hit your 5-hour limit · resets 4am (Asia/Kolkata)`.
`validate_runs.py`: `DEGRADED drrtl_communication/drrtl.sonnet-5-5.r1: 1 of 25 candidates lost to LLM errors (kept; noted in RUN_NOTES)`
— within the validator's tolerance, so kept as is (please note it in RUN_NOTES on machine 1).
00:14–04:16 the queue waited out the 5-hour limit (passes 8–19), as designed.

## 2026-11-04 — drrtl_i2c/drrtl INVALID (10/25 candidates lost to the 5-hour limit)
drrtl_simple_spi/drrtl finished ok at about 04:47 (valid). drrtl_i2c/drrtl finished "ok" at 05:27 (2371 s) but
10 candidates failed with
`LLM call failed after 3 attempts: claude-cli error: You've hit your 5-hour limit · resets 9am (Asia/Kolkata)`.
`validate_runs.py`: `INVALID drrtl_i2c/drrtl.sonnet-5-5.r1: 10 llm_error candidates, 0 LLM-failure log lines`.
The Exp 01 drrtl stage already counts it as done, so it will be archived by the queue's final
`validate_runs.py --archive` and re-run (together with drrtl_i2c/aegis) by restarting the queue after it finishes.
05:27–09:11 the no_guards stage waited out the limit (passes 1–11; every attempt stopped at the backend preflight).

## 2026-11-04 09:53 IST — LOCAL CODE CHANGE (user's request): LLM calls wait out the usage limit
The user asked to stop the 5-hour limit from invalidating runs. Changed `aegis_agents/tools/aegis_llm.py` only
(NOT committed; pack_results.sh does not add it). Effect: when the claude CLI reports a usage limit
("...limit ... resets ...") or no connection ("Can't reach the API server", EAI_AGAIN), `call()` no longer gives
up; it sleeps AEGIS_LIMIT_WAIT_S (600 s) and retries the SAME prompt, for at most AEGIS_LIMIT_WAIT_MAX_H (6 h),
without using up one of its 3 attempts. Waits are logged to `<run>/llm_waits.jsonl` (not to llm_calls.jsonl,
so token/cost numbers are unchanged). Prompts, model, candidate budget, tools and every other code path are
unchanged; any other error fails exactly as before. Tested with a fake claude CLI (limit twice then OK -> OK,
1 logged call; real error -> LLMError after 3 attempts).
Runs that use the change: every run STARTED after 09:53 IST 2026-11-04 (axil_cdc/no_guards was already running
with the old code). Machine 1 should decide whether these runs can be mixed with its own.
Diff:
```
diff --git i/aegis_agents/tools/aegis_llm.py w/aegis_agents/tools/aegis_llm.py
index a7c2911..6985964 100644
--- i/aegis_agents/tools/aegis_llm.py
+++ w/aegis_agents/tools/aegis_llm.py
@@ -101,11 +101,32 @@ def _openai(system, prompt, model, temperature, effort, timeout, base_url):
             "tokens_in": u.get("prompt_tokens", 0), "tokens_out": u.get("completion_tokens", 0), "cost_usd": None}
 
 
+def _unavailable(e):
+    """Usage limit or no connection: nothing is wrong with the call, the account/network is just not there yet."""
+    s = str(e).lower()
+    return ("limit" in s and "reset" in s) or "can't reach the api" in s or "eai_again" in s
+
+
+def _wait_note(tag, waited, e):
+    # machine 2 local change: waits go to llm_waits.jsonl, not to llm_calls.jsonl (cost numbers) or the run log
+    path = LOG_PATH or os.environ.get("AEGIS_LLM_LOG")
+    if path:
+        with open(os.path.join(os.path.dirname(os.path.abspath(path)), "llm_waits.jsonl"), "a") as f:
+            f.write(json.dumps({"tag": tag, "waited_s": waited, "reason": str(e)[:300],
+                                "time": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")
+
+
 def call(system, prompt, model, temperature=0.5, backend="claude-cli", effort=None, timeout=1800,
          base_url=None, tag=None, retries=2):
-    """One LLM call. Returns {text, temperature_applied, tokens_in, tokens_out, cost_usd, latency_s}."""
+    """One LLM call. Returns {text, temperature_applied, tokens_in, tokens_out, cost_usd, latency_s}.
+    A usage limit or a lost connection does not use up an attempt: the call waits
+    (AEGIS_LIMIT_WAIT_S between tries, at most AEGIS_LIMIT_WAIT_MAX_H hours) and retries the same prompt."""
     last = None
-    for attempt in range(retries + 1):
+    wait_s = int(os.environ.get("AEGIS_LIMIT_WAIT_S", "600"))
+    max_wait_s = float(os.environ.get("AEGIS_LIMIT_WAIT_MAX_H", "6")) * 3600
+    waited = 0
+    attempt = 0
+    while attempt <= retries:
         t0 = time.time()
         try:
             if backend == "claude-cli":
@@ -126,11 +147,17 @@ def call(system, prompt, model, temperature=0.5, backend="claude-cli", effort=No
             return out
         except (LLMError, subprocess.TimeoutExpired, OSError) as e:
             last = e
-            if "limit" in str(e).lower() and "reset" in str(e).lower():
-                break   # usage limit: retrying only burns time
+            if _unavailable(e):
+                if waited >= max_wait_s:
+                    break
+                _wait_note(tag, waited, e)
+                time.sleep(wait_s)
+                waited += wait_s
+                continue   # same attempt again once the account/network is back
 
             _log({"tag": tag, "backend": backend, "model": model, "error": str(e)[:500], "attempt": attempt})
             time.sleep(5 * (attempt + 1))
+            attempt += 1
     raise LLMError("LLM call failed after %d attempts: %s" % (retries + 1, last))
 
 
```

## 2026-11-04 14:11 — first queue pass done; restarted for the 3 missing runs
Valid since the last entry: axil_cdc/no_guards (ok 11:04, old code, no limit hit), async_fifo/no_guards (ok 11:37,
no limit hit), soc/no_guards (ok 14:11, 9280 s). soc is the first run that hit the limit with the local change:
candidates gen:r_8b5d5686e1:C1/C2 waited 11:44–13:56 (14 waits each, see soc/no_guards.sonnet-5-5.r1/llm_waits.jsonl)
and then completed; 0 errors in llm_calls.jsonl; the run stopped itself after iteration 3 ("nothing to dispatch").
afifo/no_guards failed its preflight at 09:12 (`... timed out after 120 seconds`), so run_matrix.sh stopped
("not usage-limit failures"). The final `validate_runs.py --archive` moved drrtl_i2c/drrtl to runs_archive/invalid/.
14:12: queue restarted unchanged (local wrapper) to run drrtl_i2c/aegis, drrtl_i2c/drrtl, afifo/no_guards.

## 2026-11-05 00:12 — queue done: all 15 runs finished and valid
drrtl_i2c/aegis ok 16:28 (8182 s, no limit hit); drrtl_i2c/drrtl ok 19:46 (11854 s; waited out the limit, 13 waits);
afifo/no_guards ok 00:12 (15991 s; 23 waits; stopped itself after iteration 4, "nothing to dispatch").
`validate_runs.py`: no INVALID runs; one DEGRADED (drrtl_communication/drrtl, 1/25 candidates lost, see above).
Runs that used the local aegis_llm.py wait change and actually waited: soc/no_guards, drrtl_i2c/drrtl,
afifo/no_guards. Other runs started after 09:53 on 2026-11-04 (async_fifo/no_guards, drrtl_i2c/aegis) ran the
changed code but never hit the limit, so the change did nothing there.
Invalid runs kept in aegis_agents/flow/runs_archive/invalid/{20261103-230149,20261104-141124}/.
