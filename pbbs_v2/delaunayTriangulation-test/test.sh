#!/bin/bash
set -e

PRR_DIR=/afs/ece/project/seth_group/ziqiliu/static-prr
CHEETAH_DIR=/afs/ece/project/seth_group/ziqiliu/cheetah/build/

# run static parallel region analysis
TEST_DIR=./incrementalDelaunay
pushd $TEST_DIR

clang++ -gdwarf-2 -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -ftapir=serial -flto \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
    -S -emit-llvm -o delaunayTime.ll -c ../bench/delaunayTime.C

# clang++ -DPARLAY_OPENCILK -fopencilk \
#     --opencilk-resource-dir=$CHEETAH_DIR \
#     --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
#     -mcx16 -O3 -std=c++17 -DNDEBUG -I . \
#     -S -emit-llvm -o delaunayTime.ll -c ../bench/delaunayTime.C

clang++ -gdwarf-2 -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -ftapir=serial -flto \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
    -S -emit-llvm -c delaunay.C -o delaunay.ll

# clang++ -DPARLAY_OPENCILK -fopencilk \
#     --opencilk-resource-dir=$CHEETAH_DIR \
#     --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
#     -mcx16 -O3 -std=c++17 -DNDEBUG -I . \
#     -S -emit-llvm -c delaunay.C -o delaunay.ll


llvm-link -S delaunay.ll delaunayTime.ll -o delaunayLink.ll

# run prr-stats to produce json statistics on loop and func prstate
# opt --enable-new-pm=0 -load $PRR_DIR/libPrrStatistic.so --prr-stats -test=incrementalDelaunay -debug-only=prr-stats delaunayLink.ll --disable-output
opt -load $PRR_DIR/libPrrStatistic.so -load-pass-plugin $PRR_DIR/libPrrStatistic.so -passes="prr-stats" -test=incrementalDelaunay delaunayLink.ll --disable-output

# run pbbsv2-dbg to run static functon prstate on parallel_for calls specifically 
opt -load $PRR_DIR/libParallelForDebugInfo.so -load-pass-plugin $PRR_DIR/libParallelForDebugInfo.so -passes="pbbsv2-dbg" -test=incrementalDelaunay delaunayLink.ll --disable-output

# run callgraph-explain to generate .cg.csv files 
# opt -load $PRR_DIR/libCallgraphExplain.so -load-pass-plugin $PRR_DIR/libCallgraphExplain.so -passes="callgraph-explain" -test=incrementalDelaunay delaunayLink.ll --disable-output > scc_out.txt

# clang++ -gdwarf-2 -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
#     -fforkd=lazy -ftapir=serial \
#     --opencilk-resource-dir=$CHEETAH_DIR \
#     --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0 \
#     -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld \
#     -Xclang -fpass-plugin=$PRR_DIR/libCallgraphExplain.so \
#     -S -emit-llvm -c delaunayLink.ll -o unused.ll \
#     -L${PRR_DIR} -lCallgraphExplain > scc_out.txt

popd