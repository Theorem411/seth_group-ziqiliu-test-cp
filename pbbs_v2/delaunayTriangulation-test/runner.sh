#!/bin/bash
set -e

INSTRUMENT_DIR=/afs/ece/project/seth_group/ziqiliu/instrument-test
CHEETAH_DIR=/afs/ece/project/seth_group/ziqiliu/cheetah/build/

# run static parallel region analysis
TEST_DIR=./incrementalDelaunay
pushd $TEST_DIR

######### run runtime check instrumentation ##############
clang++ -gdwarf-2 -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -fforkd=lazy -ftapir=serial \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
    -Xclang -fpass-plugin=$INSTRUMENT_DIR/instrument-pass.so \
    -o delaunayTime.o -c ../bench/delaunayTime.C \
    -L${INSTRUMENT_DIR} -lInstrument

clang++ -gdwarf-2 -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -fforkd=lazy -ftapir=serial \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
    -Xclang -fpass-plugin=$INSTRUMENT_DIR/instrument-pass.so \
    -c delaunay.C -o delaunay.o \
    -L${INSTRUMENT_DIR} -lInstrument

clang++ -o delaunay delaunayTime.o delaunay.o \
    -gdwarf-2 -DPARLAY_OPENCILK -fforkd=lazy -ftapir=serial -ldl -fuse-ld=lld \
    -L/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64 \
    -L${INSTRUMENT_DIR} -lInstrument

CILK_NWORKERS=1 LD_LIBRARY_PATH=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64:/afs/ece/project/seth_group/ziqiliu/instrument-test \
    ./delaunay -r 2 -i /afs/ece/project/seth_group/pakha/pbbsbench/testData/geometryData/data/2DinCube_100000

mv ef.csv incrementalDelaunay.ef.csv
mv dac.csv incrementalDelaunay.dac.csv
mv caller.csv incrementalDelaunay.caller.csv

##### run with pforinst instrumentation ############
clang++ -gdwarf-2 -DBUILTIN -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -fforkd=lazy -ftapir=serial \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
    -Xclang -fpass-plugin=$INSTRUMENT_DIR/libBuiltinIntrinsic.so \
    -o delaunayTime.o -c ../bench/delaunayTime.C \
    -L${INSTRUMENT_DIR} -lPforinst

clang++ -gdwarf-2 -DBUILTIN -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -fforkd=lazy -ftapir=serial \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
    -Xclang -fpass-plugin=$INSTRUMENT_DIR/libBuiltinIntrinsic.so \
    -c delaunay.C -o delaunay.o \
    -L${INSTRUMENT_DIR} -lPforinst

clang++ -o delaunay delaunayTime.o delaunay.o \
    -gdwarf-2 -DBUILTIN -DPARLAY_OPENCILK -fforkd=lazy -ftapir=serial -ldl -fuse-ld=lld \
    -L/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64 \
    -L${INSTRUMENT_DIR} -lPforinst

CILK_NWORKERS=1 LD_LIBRARY_PATH=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64:/afs/ece/project/seth_group/ziqiliu/instrument-test \
    ./delaunay -r 2 -i /afs/ece/project/seth_group/pakha/pbbsbench/testData/geometryData/data/2DinCube_100000

mv pforinst.csv incrementalDelaunay.pforinst.csv 

popd

# ----------- POLL0=1 make -------------------------------------------
# clang++ -v -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
#     -fforkd=lazy -ftapir=serial \
#     --opencilk-resource-dir=../../../../cheetah/build/ \
#     --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
#     -mcx16 -O3 -std=c++17 -DNDEBUG -I .  \
#     -o delaunayTime.o -c ../bench/delaunayTime.C
# clang++ -v -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
#     -fforkd=lazy -ftapir=serial \
#     --opencilk-resource-dir=../../../../cheetah/build/ \
#     --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
#     -mcx16 -O3 -std=c++17 -DNDEBUG -I .  \
#     -c delaunay.C -o delaunay.o
# clang++ -v -o delaunay delaunayTime.o delaunay.o \
#     -fforkd=lazy -ftapir=serial -ldl -fuse-ld=lld -L/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64
