#!/bin/bash
set -e

PRR_DIR=/afs/ece/project/seth_group/ziqiliu/static-prr
CHEETAH_DIR=/afs/ece/project/seth_group/ziqiliu/cheetah/build/


TEST_DIR=./incrementalDelaunay
pushd $TEST_DIR

clang++ -gdwarf-2 -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -fforkd=lazy -ftapir=serial \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
    -S -emit-llvm -o delaunayTime.ll -c ../bench/delaunayTime.C

clang++ -gdwarf-2 -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -fforkd=lazy -ftapir=serial \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
    -c delaunay.C -S -emit-llvm -o delaunay.ll

llvm-link -S delaunay.ll delaunayTime.ll -o delaunayLink.ll

opt -load $PRR_DIR/libParallelForDebugInfo.so -load-pass-plugin $PRR_DIR/libParallelForDebugInfo.so -passes="pbbsv2-dbg" delaunayLink.ll --disable-output > delaunayLink.src.txt

# strip off all debug info before disaster
opt delaunayLink.ll -strip-debug -o delaunayLink.ll -S

clang++ -o delaunayLink.o -c delaunayLink.ll \
    -gdwarf-2 -DBUILTIN -DPARLAY_OPENCILK -fforkd=lazy -ftapir=serial -ldl -fuse-ld=lld \
    -L/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64

clang++ -o delaunay delaunayLink.o \
    -DBUILTIN -DPARLAY_OPENCILK -fforkd=lazy -ftapir=serial -ldl -fuse-ld=lld \
    -L/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64

# #fake run: no useful info produced
# CILK_NWORKERS=1 LD_LIBRARY_PATH=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64:/afs/ece/project/seth_group/ziqiliu/instrument-test \
#     ./delaunay -r 2 -i /afs/ece/project/seth_group/pakha/pbbsbench/testData/geometryData/data/2DinCube_100000

popd