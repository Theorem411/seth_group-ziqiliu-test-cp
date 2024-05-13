#!/bin/bash
set -e

ROOT_DIR=/afs/ece/project/seth_group/ziqiliu
PRR_DIR=$ROOT_DIR/static-prr
INSTRUMENT_DIR=$ROOT_DIR/instrument-test
CHEETAH_DIR=$ROOT_DIR/cheetah/build/

clang++ -gdwarf-2 -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
    -fforkd=lazy -ftapir=serial \
    --opencilk-resource-dir=$CHEETAH_DIR \
    --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0  \
    -mcx16 -O3 -std=c++17 -DNDEBUG -I . \
    -Xclang -fpass-plugin=$INSTRUMENT_DIR/instrument-pass.so \
    -o wcTime.o -c ./bench/wcTime.C \
    -L${INSTRUMENT_DIR} -lInstrument
    
NAMES=("histogram" "histogramStar" "serial")
for TESTNAME in "${NAMES[@]}"
do 
    pushd $TESTNAME


    clang++ -gdwarf-2 -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
        -fforkd=lazy -ftapir=serial \
        --opencilk-resource-dir=$CHEETAH_DIR \
        --gcc-toolchain=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0  \
        -mcx16 -O3 -std=c++17 -DNDEBUG -I . \
        -Xclang -fpass-plugin=$INSTRUMENT_DIR/instrument-pass.so \
        -c wc.C -o wc.o \
        -L${INSTRUMENT_DIR} -lInstrument

    clang++ -o wc ../wcTime.o wc.o \
        -gdwarf-2 -DPARLAY_OPENCILK -fforkd=lazy -ftapir=serial -ldl -fuse-ld=lld \
        -L/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64 \
        -L${INSTRUMENT_DIR} -lInstrument

    CILK_NWORKERS=1 LD_LIBRARY_PATH=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64:/afs/ece/project/seth_group/ziqiliu/instrument-test \
        ./wc -r 2 -i /afs/ece/project/seth_group/pakha/pbbsbench/testData/sequenceData/data/wikipedia250M.txt
    
    mv ef.csv $TESTNAME.ef.csv
    mv dac.csv $TESTNAME.dac.csv

    echo "$TESTNAME done!"
    popd
done