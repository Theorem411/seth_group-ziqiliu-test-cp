#!/bin/bash
set -e

PRR_DIR=/afs/ece/project/seth_group/ziqiliu/static-prr
CHEETAH_DIR=/afs/ece/project/seth_group/ziqiliu/cheetah/build/

# run static parallel region analysis
TEST_DIR=./incrementalDelaunay
pushd $TEST_DIR

clang++ -DLAZYD_STRATEGY -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -fforkd=lazy -ftapir=serial \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
    -Xclang -fpass-plugin=$PRR_DIR/LazyDStrategy.so \
    -o delaunayTime.o -c ../bench/delaunayTime.C

clang++ -DLAZYD_STRATEGY -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -fforkd=lazy -ftapir=serial \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
    -Xclang -fpass-plugin=$PRR_DIR/LazyDStrategy.so \
    -c delaunay.C -o delaunay.o

clang++ -o delaunay delaunayTime.o delaunay.o \
    -DLAZYD_STRATEGY -DPARLAY_OPENCILK -fforkd=lazy -ftapir=serial -ldl -fuse-ld=lld \
    -L/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64



popd