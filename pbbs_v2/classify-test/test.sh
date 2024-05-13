#!/bin/bash
set -e

ROOT_DIR=/afs/ece/project/seth_group/ziqiliu
INSTRUMENT_DIR=/afs/ece/project/seth_group/ziqiliu/instrument-test
CHEETAH_DIR=/afs/ece/project/seth_group/ziqiliu/cheetah/build/
PRR_DIR=/afs/ece/project/seth_group/ziqiliu/static-prr

TEST_DIR=./decisionTree

pushd $TEST_DIR
clang++ -gdwarf-2 -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -ftapir=serial -flto -fuse-ld=lld -O3 \
    --opencilk-resource-dir=$CHEETAH_DIR \
    -Wall -O3 -std=c++17 \
    --gcc-toolchain=$ROOT_DIR/GCC-12.2.0 \
    -S -emit-llvm -o classifyTime.ll -c ../bench/classifyTime.C

clang++ -gdwarf-2 -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -ftapir=serial -flto -fuse-ld=lld -O3 \
    --opencilk-resource-dir=$CHEETAH_DIR \
    -Wall -O3 -std=c++17 \
    --gcc-toolchain=$ROOT_DIR/GCC-12.2.0 \
    -c classify.C -S -emit-llvm -o classify.ll

llvm-link -S classify.ll classifyTime.ll -o classifyLink.ll

# opt --enable-new-pm=0 -S --prr -test=classify classifyLink.ll -o classifyLink-pr.ll
opt -load $PRR_DIR/libPrrStatistic.so -load-pass-plugin $PRR_DIR/libPrrStatistic.so -passes="prr-stats" -test="decisionTree" classifyLink.ll --disable-output
# run pbbsv2-dbg to run static functon prstate on parallel_for calls specifically 
opt -load $PRR_DIR/libParallelForDebugInfo.so -load-pass-plugin $PRR_DIR/libParallelForDebugInfo.so -passes="pbbsv2-dbg" -test="decisionTree" classifyLink.ll --disable-output

popd