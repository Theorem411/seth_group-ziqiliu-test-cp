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


## Stage 2

- **Implementation details**: separate `build_tree` into seq & par version to create more subsitution opportunitites (breaks apart the SCC). Now has  static phase viable parallel_for substition targets.
- **Library Changes**: Parlay library changes in the test group are preserved.

### stage 2 result: 
#### **static**:

#### **dynamic**:
6 EF, 2831695 DAC, 27750947 not substituted