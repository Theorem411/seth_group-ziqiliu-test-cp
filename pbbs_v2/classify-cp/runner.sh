#!/bin/bash
set -e

INSTRUMENT_DIR=/afs/ece/project/seth_group/ziqiliu/instrument-test
CHEETAH_DIR=/afs/ece/project/seth_group/ziqiliu/cheetah/build/

clang++ -gdwarf-2 -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -fforkd=lazy -ftapir=serial \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
    -Xclang -fpass-plugin=$INSTRUMENT_DIR/instrument-pass.so \
    -o classifyTime.o -c ./bench/classifyTime.C \
    -L${INSTRUMENT_DIR} -lInstrument

# run static parallel region analysis
TEST_DIR=./decisionTree
pushd $TEST_DIR
######### run runtime parallel region analysis ##############

clang++ -gdwarf-2 -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -fforkd=lazy -ftapir=serial \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
    -Xclang -fpass-plugin=$INSTRUMENT_DIR/instrument-pass.so \
    -c classify.C -o classify.o \
    -L${INSTRUMENT_DIR} -lInstrument

clang++ -o classify ../classifyTime.o classify.o \
    -gdwarf-2 -DPARLAY_OPENCILK -fforkd=lazy -ftapir=serial -ldl -fuse-ld=lld \
    -L/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64 \
    -L${INSTRUMENT_DIR} -lInstrument

CILK_NWORKERS=1 LD_LIBRARY_PATH=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64:/afs/ece/project/seth_group/ziqiliu/instrument-test \
    ./classify -r 1 -i /afs/ece/project/seth_group/pakha/pbbsbench/testData/sequenceData/data/covtype.data

mv ef.csv decisionTree.ef.csv
mv dac.csv decisionTree.dac.csv
mv caller.csv decisionTree.caller.csv


######### run pforinst instrumentation ####################
clang++ -gdwarf-2 -DBUILTIN -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -fforkd=lazy -ftapir=serial \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
    -Xclang -fpass-plugin=$INSTRUMENT_DIR/libBuiltinIntrinsic.so \
    -o classifyTime.o -c ../bench/classifyTime.C \
    -L${INSTRUMENT_DIR} -lPforinst

clang++ -gdwarf-2 -DBUILTIN -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -fforkd=lazy -ftapir=serial \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
    -Xclang -fpass-plugin=$INSTRUMENT_DIR/libBuiltinIntrinsic.so \
    -c classify.C -o classify.o \
    -L${INSTRUMENT_DIR} -lPforinst

clang++ -o classify classifyTime.o classify.o \
    -gdwarf-2 -DBUILTIN -DPARLAY_OPENCILK -fforkd=lazy -ftapir=serial -ldl -fuse-ld=lld \
    -L/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64 \
    -L${INSTRUMENT_DIR} -lPforinst

CILK_NWORKERS=1 LD_LIBRARY_PATH=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64:/afs/ece/project/seth_group/ziqiliu/instrument-test \
    ./classify -r 1 -i /afs/ece/project/seth_group/pakha/pbbsbench/testData/sequenceData/data/covtype.data

mv pforinst.csv decisionTree.pforinst.csv

popd
