# Parallel_for Manual Substitution Project

## Goal

**GOAL**: Reduce data redundancy caused by the global counter <u>*delegate_work*</u>.

PBBS_V2 benchmarks _(classify, delaunayTriangulation, wordCounts)_ use `parallel_for` as a wrapper for `cilk_for`, which internally uses the `delegate_work` counter (also known as the parallel region depth) to choose between `parallel_for_EF` and `parallel_for_dac`.

This project aims to migrate the functionality of `delegate_work` from the dynamic phase to a static LLVM analysis pass using static analysis (**prr**).

## Overview

### Static Analysis Phase

A static-phase instrumentation pass:
- Finds all `parallel_for` calls dynamically in the source code with definite static results (e.g., definitely EF or DAC).
- Uses **LLVM's source-level debug metadata** to backtrack parlay library functions that use them as well as their eventual callsites in `classify.C` or `classifyTime.C`.
- Manually replicates the parlay functions mentioned in the call paths into EF and DAC clones.
- Finally replaces their callsites with the version befitting their static analysis results.

### Dynamic Analysis Phase

A dynamic-phase instrumentation pass is run to analyze metrics of the substituted `parallel_for` calls, such as:
- Dynamic entry count
- Average trip count
- Granularity (arguments of `parallel_for` calls)


## Stage 1

- **Implementation details**: only 1 viable parallel_for substition target because the majority `parallel_for` are called in build_tree defined in `classify.C`, which is involved in a SCC that has both DAC and EF callsites (hence Both status propagates, resulting in overconservativeness).
- **Library Changes**: Parlay library changes in the test group are preserved.

### stage 1 result: 
#### **static**:
25 instrumentation cilkfor results:
- 1 ef cilkfors
- 0 dac cilkfors
- 24 both cilkfors
- 0 untouched cilkfors
#### **dynamic**:
1 EF, 0 DAC, 30599798 not substituted.