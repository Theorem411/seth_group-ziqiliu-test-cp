#!/bin/bash
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
    echo -e "make ${EXE}Link.ll\n"
    make $SRC_ORIG_PATH/${EXE}Link.ll
    popd > /dev/null

    pushd $SRC_ORIG_PATH > /dev/null
    # ParallelForDebugInfo: output .cilkfor.json containing all static cilkfor result
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
    echo -e "make $EXE-instr\n"
    make $SRC_ORIG_PATH/$EXE-instr
    popd > /dev/null

    TESTNAME=$testname CILK_NWORKERS=1 LD_LIBRARY_PATH=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64:/afs/ece/project/seth_group/ziqiliu/instrument-prr \
        ./$EXE-instr -r 1 -i $TESTDATA
    
    if [ ! -f "${TESTNAME}.instr.json" ]; then
        echo -e "Error: File ${TESTNAME}.instr.json does not exist." >&2
        exit 1
    fi
    popd > /dev/null

    # # output keyword substitution worklist to $SRC_ORIG_DIR/$TESTNAME.worklist.txt
    # pushd $BASE_DIR > /dev/null
    # python replacePbbsV2ParallelFor.py -E
    # popd > /dev/null
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
    > $CONTROL_LOG
    for nwkr in 1 2 4 8 14 28; do 
        echo -e "== CILK_WORKERS = ${nwkr} ===================================" >> $CONTROL_LOG
        CILK_NWORKERS=${nwkr} LD_LIBRARY_PATH=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64 \
            ./$EXE -r $R -i $TESTDATA >> $CONTROL_LOG 2>&1
    done
    echo -e "Created control group parlaytime log: $CONTROL_LOG"
    echo -e "\n/*** done with control group! ***/\n"
    popd > /dev/null

    # test with modified library
    ### NOTE: ran with -DRUNTIME to turn on optimized parallel_for code
    pushd $BASE_DIR > /dev/null
    echo -e "\n-- make test $EXE\n"
    if [ -n "$assert" ] && [ "$assert" -eq 1 ]; then
        echo -e "-DASSERT turned on!\n"
        make $SRC_TEST_PATH/$EXE ASSERT=1 
    else 
        make $SRC_TEST_PATH/$EXE ASSERT=0 
    fi
    popd > /dev/null

    pushd $SRC_TEST_PATH > /dev/null
    local TEST_LOG="${BASE_DIR}/data/${TESTNAME}/${DATETIME}.parlaytime.test.log"
    > $TEST_LOG
    for nwkr in 1 2 4 8 14 28; do 
        echo -e "== CILK_WORKERS = $nwkr ===================================" >> $TEST_LOG
        CILK_NWORKERS=$nwkr LD_LIBRARY_PATH=/afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/lib64 \
            ./$EXE -r $R -i $TESTDATA >> $TEST_LOG 2>&1
    done
    echo -e "Created test group parlaytime log: $TEST_LOG"
    echo -e "\n/*** done with substitute test group! ***/\n"
    popd > /dev/null
}

# delaunayTriangulation
delaunayTriangulation() {
    # choose mode: analysis or runtime
    local DELAUNAYTIME_TEST_PATH=$BASE_DIR/delaunayTriangulation-test/bench
    local DELAUNAY_TEST_PATH=$BASE_DIR/delaunayTriangulation-test/incrementalDelaunay
    local DELAUNAYTIME_ORIG_PATH=$BASE_DIR/delaunayTriangulation-cp/bench
    local DELAUNAY_ORIG_PATH=$BASE_DIR/delaunayTriangulation-cp/incrementalDelaunay
    if [ "$1" -eq 0 ]; then 
        # fresh start
        pushd $BASE_DIR > /dev/null
        make CLEAN_DELAUNAY_ANALYSIS
        popd > /dev/null
        # 
        compileAnalysis $DELAUNAY_ORIG_PATH \
                        $DELAUNAYTIME_ORIG_PATH \
                        "delaunay" \
                        /afs/ece/project/seth_group/pakha/pbbsbench/testData/geometryData/data/2DinCube_100000 \
                        "delaunayTriangulation"
        
    else 
        ##### performance experiment: ######
        # fresh start
        pushd $BASE_DIR > /dev/null
        make CLEAN_DELAUNAY_PERF
        popd > /dev/null
        # 
        compilePerformanceTest $DELAUNAY_ORIG_PATH \
                            $DELAUNAY_TEST_PATH \
                            "delaunay" \
                            /afs/ece/project/seth_group/pakha/pbbsbench/testData/geometryData/data/2DinCube_100000 \
                            "delaunayTriangulation"
    fi

}

# wordCount 
wordCounts() {
    # choose mode: analysis or runtime
    local WCTIME_TEST_PATH=$BASE_DIR/wordCounts-test/bench
    local WC_TEST_PATH=$BASE_DIR/wordCounts-test/histogram
    local WCTIME_ORIG_PATH=$BASE_DIR/wordCounts-cp/bench
    local WC_ORIG_PATH=$BASE_DIR/wordCounts-cp/histogram

    if [ $1 -eq 0 ]; then
        pushd $BASE_DIR > /dev/null
        make CLEAN_WC_ANALYSIS # fresh start
        popd > /dev/null
        # 
        compileAnalysis $WC_ORIG_PATH \
                        $WCTIME_ORIG_PATH \
                        "wc" \
                        "/afs/ece/project/seth_group/pakha/pbbsbench/testData/sequenceData/data/wikipedia250M.txt" \
                        "wordCounts"

    else 
        # fresh start
        pushd $BASE_DIR > /dev/null
        make CLEAN_WC_PERF
        popd > /dev/null

        # 
        compilePerformanceTest $WC_ORIG_PATH \
                            $WC_TEST_PATH \
                            "wc" \
                            "/afs/ece/project/seth_group/pakha/pbbsbench/testData/sequenceData/data/wikipedia250M.txt" \
                            "wordCounts"
    fi
}

# classify
classify() {
    # choose mode: analysis or runtime
    local CLASSIFYTIME_TEST_PATH=$BASE_DIR/classify-test/bench
    local CLASSIFY_TEST_PATH=$BASE_DIR/classify-test/decisionTree
    local CLASSIFYTIME_ORIG_PATH=$BASE_DIR/classify-cp/bench
    local CLASSIFY_ORIG_PATH=$BASE_DIR/classify-cp/decisionTree

    if [ $1 -eq 0 ]; then
        pushd $BASE_DIR > /dev/null
        make CLEAN_CLASSIFY_ANALYSIS # fresh start
        popd > /dev/null
        # run prr analysis and instrumentation
        compileAnalysis $CLASSIFY_ORIG_PATH \
                        $CLASSIFYTIME_ORIG_PATH \
                        "classify" \
                        "/afs/ece/project/seth_group/pakha/pbbsbench/testData/sequenceData/data/covtype.data" \
                        "classify"

    else 
        # fresh start
        pushd $BASE_DIR > /dev/null
        make CLEAN_CLASSIFY_PERF
        popd > /dev/null

        # run performance test: control vs. test group
        compilePerformanceTest $CLASSIFY_ORIG_PATH \
                            $CLASSIFY_TEST_PATH \
                            "classify" \
                            "/afs/ece/project/seth_group/pakha/pbbsbench/testData/sequenceData/data/covtype.data" \
                            "classify"
    fi
}

# main 
main() {
    # $mode and $test should be provided by env variables
    if [ "$mode" -eq 0 ]; then 
        echo -e "Test: ${test}\tMode: static prr\tanalysis & instrumentation\n"
    else 
        echo -e "Test: ${test}\tMode: dynamic\tperformance experiment\n"
    fi

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
    echo -e "summary:\nmode=$mode\ntest=$test\nassert=$assert\nr=$r\n"
}

main

################################
# example call: 
#### individual test perf/analsyis run
# test=delaunayTriangulation mode=1 (r=10) (assert=1) ./prr.sh

#### ran all pbbs_v2 perf experiments 
# mode=1 test=all ./prr.sh 
################################