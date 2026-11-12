---
name: investigate-performance
description: >
  Use when the user says "this is slow", "why is this endpoint slow", "reduce
  the latency", "memory keeps growing" or "make it faster", and the cause must
  be located and proven. Do not use for optimization without a measured problem,
  or for wrong results (use debug-from-evidence).
---

# Investigate performance

## Purpose

Locate the dominant cost with measurement, change one thing at a time, and prove the gain against a recorded baseline.

## Inputs needed

- A target stated as a number, a percentile and a load: for example "`GET /search` p95 under 300 ms at 200 requests per second on 1 million documents".
- A way to run the workload repeatedly: script, load tool or benchmark.
- A representative dataset and an environment that resembles production.
- Access to profilers, traces, query plans and metrics.

## Steps

1. Write the target and the current number. If there is no number, stop and get one (see "When to stop and ask").
2. Build a repeatable measurement: fixed dataset, a warm-up whose results are discarded, at least 30 iterations or 60 seconds, the same hardware each time. Record p50, p95, p99, throughput, error rate, CPU and memory.
3. Run the baseline twice. If the two runs differ by more than 5%, fix the environment (noisy neighbors, background jobs, thermal limits) before continuing. Store the results with the commit hash.
4. Split the time by segment: client, network, application, database, outbound calls. Use traces or timers. Only a segment that holds more than 30% of the total is worth work.
5. Profile that segment with a real tool: a sampling profiler or flame graph for CPU, an allocation profile for memory, `EXPLAIN ANALYZE` for queries. Write down the top three hot spots with their percentage share.
6. Classify the cause: algorithmic (quadratic loop), I/O (N+1 queries, missing index, chatty calls), contention (locks, exhausted pools), memory and garbage collection, serialization, or cache misses. Compute the ceiling: speeding up a 20% segment by half gains at most 10%.
7. Change one thing, with a predicted gain written down first. Re-run the same measurement. Keep the change only if the gain is at least twice the noise you measured in step 3 and p99 did not get worse. Revert changes that miss.
8. Check side effects after each kept change: tests pass, memory did not grow, behavior under concurrent load is intact, and a better p50 did not hide a worse p99.
9. Repeat from step 4 until the target is met, or until every remaining hot spot holds less than 10% of the total.
10. Lock the result in: a benchmark or a performance test that fails at a threshold with some margin (for example 20% over the new number), or an alert on the production metric.
11. Write a before and after table with the numbers, the changes kept, the changes reverted, and the hot spots left alone.

### Example results table (illustrative numbers)

```
Run                    p50      p95      p99     change vs baseline (noise 4%)
baseline (a1b2c3d)     210 ms   840 ms   1.4 s   -
index on docs.owner    190 ms   610 ms   1.1 s   p95 -27%: keep
batch the 30 lookups   185 ms   600 ms   1.2 s   p95 -2%: inside noise, revert
```

## Output

Return a results table with one row per kept change: metric, baseline, result, gain, measured noise and commit hash. Add the harness command, the profile evidence for the hot spot, what you tried and reverted, and the benchmark threshold or alert that now guards the gain. If the target was missed, give the shortfall and the next hot spot. End with the exit criteria below as a checklist, each marked met or not met with one line of evidence.

## Exit criteria

- [ ] Baseline and final numbers were produced by the same harness and are stored with commit hashes.
- [ ] The target is met, or the shortfall is quantified and the next hot spot is named.
- [ ] Each kept change shows a gain of at least twice the measured noise.
- [ ] p99 and memory are no more than 5% worse than baseline.
- [ ] The test suite passes.
- [ ] A benchmark threshold or an alert guards the improvement.

## Failure modes

- **Optimizing by intuition.** The slow part is rarely the part that looks slow. Profile first.
- **Misleading micro-benchmark.** The compiler removes the work, the cache is always warm, or the data is tiny. Benchmark with realistic data and check that the work happens.
- **Averages only.** Users feel the tail. Report percentiles.
- **Several changes at once.** You cannot tell which one helped. One change per experiment.
- **Noisy environment.** A laptop with other programs running gives numbers that differ by 20% between runs. Measure the noise first.
- **Cache hides the cost.** A cache makes the benchmark pass and adds invalidation bugs. Measure the cold path too.
- **Load generator saturated.** The tool, not the service, is the limit. Watch the generator's own CPU.
- **Different configuration.** A debug build, a smaller pool or another region. Match production settings.
- **Coordinated omission.** A load tool that waits for slow responses before sending the next request under-reports latency. Use a fixed arrival rate.

## When to stop and ask

- No target exists, or two stakeholders give different targets.
- The fix needs new infrastructure, a new dependency or an architectural change beyond the task.
- The load test would run against production or a shared environment.
- The gain requires weakening consistency, durability or a correctness check.
- The measured cause lies in a system owned by another team.
