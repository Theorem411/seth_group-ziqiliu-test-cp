#!/bin/bash

################################
# example call: 
#### individual test perf/analsyis run
# test=delaunayTriangulation mode=1 (r=10) ./prr.sh

#### ran all pbbs_v2 perf experiments 
# mode=1 test=all ./prr.sh 
################################

set -e 

PRR_DIR=/afs/ece/project/seth_group/ziqiliu/static-prr 
CHEETAH_DIR=/afs/ece/project/seth_group/ziqiliu/cheetah/build/
INSTR_DIR=/afs/ece/project/seth_group/ziqiliu/instrument-prr
BASE_DIR=/afs/ece/project/seth_group/ziqiliu/test-cp/pbbs_v2

# compile prr analysis
compileAnalysis() {
    local SRC_ORIG_PATH=$1   # path to <testname>.C
    local TIME_ORIG_PATH=$2  # path to <testname>Time.C

    local EXE=$3      # executable
    local TESTDATA=$4 # testData absolute path
    local testname=$5 # analysis result output name prefix 

    ##### prr analysis: ######
    # NOTE: use -fno-inline to disable all inlining for prr analysis correctness
    #       verbose: no inlining so each cilkfor has a unique parallel_for parent for id

    # ModulePrinter: extract LLVM IR at TapirLateEPCallback extension point
    pushd $BASE_DIR > /dev/null
    echo -e "\n-- make ${EXE}Link.ll\n"
    make $SRC_ORIG_PATH/${EXE}Link.ll
    popd > /dev/null

    pushd $SRC_ORIG_PATH > /dev/null
    # ParallelForDebugInfo: output .cilkfor.json containing all static cilkfor result
    echo -e "\n   deriving ${TESTNAME}.cilkfor.json ..."
    export TESTNAME=$testname
    opt -load $PRR_DIR/libParallelForDebugInfo.so -load-pass-plugin $PRR_DIR/libParallelForDebugInfo.so \
        -passes="pbbsv2-dbg" ${EXE}Link.ll --disable-output \
        2> $SRC_ORIG_PATH/ParallelForDebugInfo.error.txt
    if [ ! -f "${TESTNAME}.cilkfor.json" ]; then
        echo -e "Error: File ${TESTNAME}.cilkfor.json does not exist." >&2
        exit 1
    fi

    # CallgraphExplain: use reverse callgraph showing calling history in source code
    # output .cg.json
    echo -e "\n   deriving ${TESTNAME}.cg.json ..."
    export TESTNAME=$testname
    opt -load $PRR_DIR/libCallgraphExplain.so -load-pass-plugin $PRR_DIR/libCallgraphExplain.so \
        -passes="callgraph-explain" ${EXE}Link.ll --disable-output
    if [ ! -f "${TESTNAME}.cg.json" ]; then
        echo -e "Error: File ${TESTNAME}.cg.json does not exist." >&2
        exit 1
    fi

    # LazydInstrumentLoopPlugin: Instrumentation for checking static analysis correctness and overconservativeness
    # output .instr.json
    ### NOTE: run with -DBUILTIN to turn on instrumentation code
    ### NOTE: ran with 1 worker to ensure instrumentation correctness
    pushd $BASE_DIR > /dev/null
    echo -e "\n--make $EXE-instr\n"
    make $SRC_ORIG_PATH/$EXE-instr
    popd > /dev/null

    echo -e "\n   deriving ${TESTNAME}.instr.json ..."
    TESTNAME=$testname CILK_NWORKERS=1 LD_LIBRARY_PATH=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64:/afs/ece/project/seth_group/ziqiliu/instrument-prr \
        ./$EXE-instr -r 1 -i $TESTDATA
    
    if [ ! -f "${TESTNAME}.instr.json" ]; then
        echo -e "Error: File ${TESTNAME}.instr.json does not exist." >&2
        exit 1
    fi
    popd > /dev/null
}

# compile performance test
compilePerformanceTest() {
    local SRC_ORIG_PATH=$1
    local SRC_TEST_PATH=$2
    local EXE=$3
    local TESTDATA=$4
    local TESTNAME=$5

    # R number of experiment runs
    if [ ! -n "$r" ]; then 
        echo -e "\nexperiment run parameter \$r not defined! Use default 20..."
        local R=20
    else 
        local R=$r
    fi 

    # original library 
    pushd $BASE_DIR > /dev/null
    echo -e "\n-- make orig $EXE"
    make $SRC_ORIG_PATH/$EXE
    popd > /dev/null
    
    pushd $SRC_ORIG_PATH > /dev/null
    local CONTROL_LOG="${BASE_DIR}/data/${TESTNAME}/${DATETIME}.parlaytime.orig.log"
    echo -e "\n-- run control performance executable $EXE, check $CONTROL_LOG\n"
    > $CONTROL_LOG
    local CONTROL_ICACHE="${BASE_DIR}/data/${TESTNAME}/${DATETIME}.icache.orig.txt"
    echo -e "   check $CONTROL_ICACHE"
    > $CONTROL_ICACHE
    for nwkr in 1 2 4 8 14 28; do 
        echo -e "== CILK_WORKERS = ${nwkr} ===================================" >> $CONTROL_LOG
        echo -e "== CILK_WORKERS = ${nwkr} ===================================" >> $CONTROL_ICACHE
        CILK_NWORKERS=${nwkr} LD_LIBRARY_PATH=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64 \
        perf stat -e icache.misses,icache.hit \
            ./$EXE -r $R -i $TESTDATA 1>> $CONTROL_LOG 2>> $CONTROL_ICACHE
    done
    echo -e "Created control group parlaytime log: $CONTROL_LOG"
    echo -e "\n/*** done with control group! ***/\n"
    popd > /dev/null

    # test with modified library
    ### NOTE: ran with -DRUNTIME to turn on optimized parallel_for code
    pushd $BASE_DIR > /dev/null
    echo -e "\n-- make test $EXE\n"
    make $SRC_TEST_PATH/$EXE
    popd > /dev/null

    pushd $SRC_TEST_PATH > /dev/null
    local TEST_LOG="${BASE_DIR}/data/${TESTNAME}/${DATETIME}.parlaytime.test.log"
    echo -e "\n-- run test performance executable $EXE, check $TEST_LOG\n"
    > $TEST_LOG
    local TEST_ICACHE="${BASE_DIR}/data/${TESTNAME}/${DATETIME}.icache.test.txt"
    echo -e "   check $TEST_ICACHE"
    > $TEST_ICACHE
    for nwkr in 1 2 4 8 14 28; do 
        echo -e "== CILK_WORKERS = $nwkr ===================================" >> $TEST_LOG
        echo -e "== CILK_WORKERS = ${nwkr} ===================================" >> $TEST_ICACHE
        CILK_NWORKERS=$nwkr LD_LIBRARY_PATH=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64 \
        perf stat -e icache.misses,icache.hit \
            ./$EXE -r $R -i $TESTDATA 1>> $TEST_LOG 2>>$TEST_ICACHE
    done
    echo -e "Created test group parlaytime log: $TEST_LOG"
    echo -e "\n/*** done with substitute test group! ***/\n"
    popd > /dev/null
}

# compile Performance Profiling
#   dynamic data: entry count, callsite, depth, granularity
#   icache performance: 
compilePerformanceProfile() {
    local SRC_TEST_PATH=$1
    local EXE=$2
    local TESTDATA=$3
    local testname=$4

    # make profiling instrumented test executable 
    pushd $BASE_DIR > /dev/null
    echo -e "\n-- make performance profiling executable $EXE-perf\n"
    make $SRC_TEST_PATH/$EXE-perf
    popd > /dev/null

    pushd $SRC_TEST_PATH > /dev/null
    echo -e "\n-- ran performance profiling for $testname\n"
    TESTNAME=$testname CILK_NWORKERS=1 LD_LIBRARY_PATH=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64:/afs/ece/project/seth_group/ziqiliu/test-cp/instr \
            ./$EXE-perf -r 1 -i $TESTDATA
    if [ ! -f "$testname.perf.log" ]; then 
        echo -e "\nError: File ${testname}.perf.log wasn't created!" >&2
        exit 1
    fi
    # expensive
    echo -e "\n-- compressing ${testname}.perf.log ...\n"
    gzip -f $testname.perf.log

    popd > /dev/null

    # make Callgraph tracing with inlining enabled
    pushd $BASE_DIR > /dev/null
    echo -e "\n-- make ${EXE}Link-perf.ll\n"
    make $SRC_TEST_PATH/${EXE}Link-perf.ll
    popd > /dev/null

    pushd $SRC_TEST_PATH > /dev/null
    export TESTNAME=$testname-perf
    opt -load $PRR_DIR/libCallgraphExplain.so -load-pass-plugin $PRR_DIR/libCallgraphExplain.so \
        -passes="callgraph-explain" ${EXE}Link-perf.ll --disable-output
    if [ ! -f "${TESTNAME}.cg.json" ]; then
        echo -e "Error: File ${TESTNAME}.cg.json does not exist." >&2
        exit 1
    fi
    popd > /dev/null
}

# delaunayTriangulation
delaunayTriangulation() {
    # choose mode: analysis or runtime
    local DELAUNAYTIME_TEST_PATH=$BASE_DIR/delaunayTriangulation-test/bench
    local DELAUNAY_TEST_PATH=$BASE_DIR/delaunayTriangulation-test/incrementalDelaunay
    local DELAUNAYTIME_ORIG_PATH=$BASE_DIR/delaunayTriangulation-cp/bench
    local DELAUNAY_ORIG_PATH=$BASE_DIR/delaunayTriangulation-cp/incrementalDelaunay

    local TEST_DATA="/afs/ece/project/seth_group/pakha/pbbsbench/testData/geometryData/data/2DinCube_100000"
    case "$1" in
        0) 
            # fresh start
            pushd $BASE_DIR > /dev/null
            make CLEAN_DELAUNAY_ANALYSIS
            popd > /dev/null
            # 
            compileAnalysis $DELAUNAY_ORIG_PATH \
                            $DELAUNAYTIME_ORIG_PATH \
                            "delaunay" \
                            $TEST_DATA \
                            "delaunayTriangulation"
            ;;
        1)
            ##### performance experiment: ######
            # fresh start
            pushd $BASE_DIR > /dev/null
            make CLEAN_DELAUNAY_TEST
            popd > /dev/null
            # 
            compilePerformanceTest $DELAUNAY_ORIG_PATH \
                            $DELAUNAY_TEST_PATH \
                            "delaunay" \
                            $TEST_DATA \
                            "delaunayTriangulation"
            ;;
        2)  ##### performance profiling: ######
            # fresh start
            pushd $BASE_DIR > /dev/null
            make CLEAN_DELAUNAY_PERF
            popd > /dev/null
            # 
            compilePerformanceProfile $DELAUNAY_TEST_PATH \
                            "delaunay" \
                            $TEST_DATA \
                            "delaunayTriangulation"

            ;;
        *)
            ;;
    esac
}

# wordCount 
wordCounts() {
    # choose mode: analysis or runtime
    local WCTIME_TEST_PATH=$BASE_DIR/wordCounts-test/bench
    local WC_TEST_PATH=$BASE_DIR/wordCounts-test/histogram
    local WCTIME_ORIG_PATH=$BASE_DIR/wordCounts-cp/bench
    local WC_ORIG_PATH=$BASE_DIR/wordCounts-cp/histogram

    local TEST_DATA=/afs/ece/project/seth_group/pakha/pbbsbench/testData/sequenceData/data/wikipedia250M.txt
    case "$1" in 
        0)
            pushd $BASE_DIR > /dev/null
            make CLEAN_WC_ANALYSIS # fresh start
            popd > /dev/null
            # 
            compileAnalysis $WC_ORIG_PATH \
                            $WCTIME_ORIG_PATH \
                            "wc" \
                            $TEST_DATA \
                            "wordCounts"
            ;;
        1)  ##### Performance Experiment: ######
            # fresh start
            pushd $BASE_DIR > /dev/null
            make CLEAN_WC_TEST
            popd > /dev/null

            # 
            compilePerformanceTest $WC_ORIG_PATH \
                                $WC_TEST_PATH \
                                "wc" \
                                $TEST_DATA \
                                "wordCounts"
            ;;
        2)  ##### performance profiling: ######
            pushd $BASE_DIR > /dev/null
            make CLEAN_WC_PERF
            popd > /dev/null
            # generate runtime trace file
            compilePerformanceProfile $WC_TEST_PATH \
                                "wc" \
                                $TEST_DATA \
                                "wordCounts"
            ;;
        *) 
            ;;
    esac 
}

# classify
classify() {
    # choose mode: analysis or runtime
    local CLASSIFYTIME_TEST_PATH=$BASE_DIR/classify-test/bench
    local CLASSIFY_TEST_PATH=$BASE_DIR/classify-test/decisionTree
    local CLASSIFYTIME_ORIG_PATH=$BASE_DIR/classify-cp/bench
    local CLASSIFY_ORIG_PATH=$BASE_DIR/classify-cp/decisionTree

    local TEST_DATA="/afs/ece/project/seth_group/pakha/pbbsbench/testData/sequenceData/data/covtype.data"
    case "$1" in 
        0)  # mode: prr analysis
            pushd $BASE_DIR > /dev/null
            make CLEAN_CLASSIFY_ANALYSIS # fresh start
            popd > /dev/null
            # run prr analysis and instrumentation
            compileAnalysis $CLASSIFY_ORIG_PATH \
                            $CLASSIFYTIME_ORIG_PATH \
                            "classify" \
                            $TEST_DATA \
                            "classify"
            ;;
        1)
            # mode: perf experiment
            pushd $BASE_DIR > /dev/null
            make CLEAN_CLASSIFY_TEST
            popd > /dev/null

            # run performance test: control vs. test group
            compilePerformanceTest $CLASSIFY_ORIG_PATH \
                            $CLASSIFY_TEST_PATH \
                            "classify" \
                            $TEST_DATA \
                            "classify"
            ;;
        2) 
            # mode: perf profiling 
            pushd $BASE_DIR > /dev/null
            make CLEAN_CLASSIFY_PERF
            popd > /dev/null
            
            # run performance profiling: 
            compilePerformanceProfile $CLASSIFY_TEST_PATH \
                            "classify" \
                            $TEST_DATA \
                            "classify"
            ;;
        *)
            ;;
    esac 
}

# main 
main() {
    # $mode and $test should be provided by env variables
    case "$mode" in 
        0)
            echo -e "Test: ${test}\tMode: static prr\tanalysis & instrumentation\n"
            ;;
        1)
            echo -e "Test: ${test}\tMode: dynamic\tperformance experiment\n"
            ;;
        2)  
            echo -e "Test: ${test}\tMode: dynamic\tperformance profiling\n"
            ;;
        *)  
            echo -e "unknown \$mode supplied"
            exit 1
            ;;
    esac

    # record current utc timestamp for experiment identification
    DATETIME=$(date -u +"%Y-%m-%d.%H:%M:%S")

    # call test
    case "$test" in
        delaunayTriangulation)
            delaunayTriangulation "$mode" 
            ;;
        wordCounts)
            wordCounts "$mode"
            ;;
        classify)
            classify "$mode"
            ;;
        all)
            echo -e "Test all!"
            echo -e "\n==== test=delaunayTriangulation\n"
            delaunayTriangulation "$mode" 
            echo -e "\n==== test=wordCounts\n"
            wordCounts "$mode"
            echo -e "\n==== test=classify\n"
            classify "$mode"
            ;;
        *)
            echo -e "unrecognized test name: $test"
            exit 1
            ;;
    esac

    # print DATETIME as experiment id
    echo -e "\nCheck experiment with id/datetime: ${DATETIME}"
    echo -e "summary:\nmode=$mode\ntest=$test\nr=$r\n"
}

main