PERF ?= 0
# tools: clang++ llvm-link
CXX = clang++
LLVM_LINK = llvm-link

# common directory analysis passes, as well as instrumentation library and passes
BASE_DIR = /afs/ece/project/seth_group/ziqiliu
PRR_DIR = $(BASE_DIR)/static-prr
CHEETAH_DIR = $(BASE_DIR)/cheetah/build/
INSTR_DIR = $(BASE_DIR)/instrument-prr
PROFILE_DIR = $(BASE_DIR)/test-cp/instr
GCC_TOOLCHAIN = $(BASE_DIR)/GCC-12.2.0

WORK_DIR = $(BASE_DIR)/test-cp/pbbs_v2

# Clang++ flags and load dynamic library flags
CXXFLAGS = -DPARLAY_OPENCILK -mllvm -experimental-debug-variable-locations=false \
		   --opencilk-resource-dir=$(CHEETAH_DIR) --gcc-toolchain=$(GCC_TOOLCHAIN) \
           -fforkd=lazy -ftapir=serial -mcx16 -O3 -std=c++17 -DNDEBUG -I . -ldl -fuse-ld=lld

CXXFLAGS_INSTR = $(CXXFLAGS) -gdwarf-2 -fno-inline -DBUILTIN -Xclang -fpass-plugin=$(INSTR_DIR)/LazydInstrumentLoopPlugin.so
# ifeq ($(PERF), 0)
# 	CXXFLAGS_INSTR += -fno-inline -DBUILTIN -Xclang -fpass-plugin=$(INSTR_DIR)/LazydInstrumentLoopPlugin.so
# else
# 	CXXFLAGS_INSTR += -DRUNTIME -DASSERT -Xclang -fpass-plugin=$(PROFILE_DIR)/LazydProfilingPerfPlugin.so
# endif 
CXXFLAGS_PROFILE = $(CXXFLAGS) -gdwarf-2 -DRUNTIME -DASSERT -Xclang -fpass-plugin=$(PROFILE_DIR)/LazydProfilingPerfPlugin.so

CXXFLAGS_LL = $(CXXFLAGS) -gdwarf-2 -fno-inline -Xclang -fpass-plugin=$(PRR_DIR)/libModulePrinter.so
# ifeq ($(PERF), 0) # analysis mode
# 	CXXFLAGS_LL += -fno-inline 
# endif
CXXFLAGS_PROFILE_LL = $(CXXFLAGS) -gdwarf-2 -fno-inline -Xclang -fpass-plugin=$(PRR_DIR)/libModulePrinter.so

CXXFLAGS_RUN = $(CXXFLAGS) -DRUNTIME

LDFLAGS = -L$(GCC_TOOLCHAIN)/lib64
LDFLAGS_INSTR = $(LDFLAGS) -L$(INSTR_DIR) -lLazydInstrumentLoop
# ifeq ($(PERF), 0)
# 	LDFLAGS_INSTR += -L$(INSTR_DIR) -lLazydInstrumentLoop
# else 
# 	LDFLAGS_INSTR += -L$(PROFILE_DIR) -lLazydProfilingPerf
# endif
LDFLAGS_PROFILE = $(LDFLAGS) -L$(PROFILE_DIR) -lLazydProfilingPerf

###############################################################################
# DELAUNAY_TRIANGULATION: intermediate files
###############################################################################
# source code paths: test vs. original
DELAUNAY_ORIG_DIR = $(WORK_DIR)/delaunayTriangulation-cp/incrementalDelaunay
DELAUNAYTIME_ORIG_DIR = $(WORK_DIR)/delaunayTriangulation-cp/bench
DELAUNAY_TEST_DIR = $(WORK_DIR)/delaunayTriangulation-test/incrementalDelaunay
DELAUNAYTIME_TEST_DIR = $(WORK_DIR)/delaunayTriangulation-test/bench

DELAUNAY_ORIG_SRC = $(DELAUNAY_ORIG_DIR)/delaunay.C
DELAUNAYTIME_ORIG_SRC = $(DELAUNAYTIME_ORIG_DIR)/delaunayTime.C
DELAUNAY_TEST_SRC = $(DELAUNAY_TEST_DIR)/delaunay.C
DELAUNAYTIME_TEST_SRC = $(DELAUNAYTIME_TEST_DIR)/delaunayTime.C

# object paths: 3 modes, test, instr, original
DELAUNAY_INSTR_OBJ = $(DELAUNAY_ORIG_DIR)/delaunay-instr.o
DELAUNAYTIME_INSTR_OBJ = $(DELAUNAY_ORIG_DIR)/delaunayTime-instr.o
DELAUNAY_PERF_OBJ = $(DELAUNAY_TEST_DIR)/delaunay-perf.o
DELAUNAYTIME_PERF_OBJ = $(DELAUNAY_TEST_DIR)/delaunayTime-perf.o
DELAUNAY_TEST_OBJ = $(DELAUNAY_TEST_DIR)/delaunay.o
DELAUNAYTIME_TEST_OBJ = $(DELAUNAY_TEST_DIR)/delaunayTime.o
DELAUNAY_OBJ = $(DELAUNAY_ORIG_DIR)/delaunay.o
DELAUNAYTIME_OBJ = $(DELAUNAY_ORIG_DIR)/delaunayTime.o

DELAUNAY_LL = $(DELAUNAY_ORIG_DIR)/delaunay.ll
DELAUNAYTIME_LL = $(DELAUNAY_ORIG_DIR)/delaunayTime.ll
DELAUNAY_PERF_LL = $(DELAUNAY_TEST_DIR)/delaunay-perf.ll
DELAUNAYTIME_PERF_LL = $(DELAUNAY_TEST_DIR)/delaunayTime-perf.ll

# possible targets
DELAUNAY_LINK_LL = $(DELAUNAY_ORIG_DIR)/delaunayLink.ll
DELAUNAY_LINK_PERF_LL = $(DELAUNAY_TEST_DIR)/delaunayLink-perf.ll
DELAUNAY_TEST = $(DELAUNAY_TEST_DIR)/delaunay
DELAUNAY_INSTR = $(DELAUNAY_ORIG_DIR)/delaunay-instr
DELAUNAY_PERF = $(DELAUNAY_TEST_DIR)/delaunay-perf
DELAUNAY = $(DELAUNAY_ORIG_DIR)/delaunay

###############################################################################
# WCCOUNT: intermediate files
###############################################################################
# source code paths: test vs. original
WC_ORIG_DIR = $(WORK_DIR)/wordCounts-cp/histogram
WCTIME_ORIG_DIR = $(WORK_DIR)/wordCounts-cp/bench
WC_TEST_DIR = $(WORK_DIR)/wordCounts-test/histogram
WCTIME_TEST_DIR = $(WORK_DIR)/wordCounts-test/bench

WC_ORIG_SRC = $(WC_ORIG_DIR)/wc.C
WCTIME_ORIG_SRC = $(WCTIME_ORIG_DIR)/wcTime.C
WC_TEST_SRC = $(WC_TEST_DIR)/wc.C
WCTIME_TEST_SRC = $(WCTIME_TEST_DIR)/wcTime.C

# object paths: 4 modes, test, instr, original, perf
WC_INSTR_OBJ = $(WC_ORIG_DIR)/wc-instr.o
WCTIME_INSTR_OBJ = $(WC_ORIG_DIR)/wcTime-instr.o

WC_PERF_OBJ = $(WC_TEST_DIR)/wc-perf.o
WCTIME_PERF_OBJ = $(WC_TEST_DIR)/wcTime-perf.o

# $(info WC_INSTR_OBJ is set to $(WC_INSTR_OBJ))
# $(info WCTIME_INSTR_OBJ is set to $(WCTIME_INSTR_OBJ))

WC_TEST_OBJ = $(WC_TEST_DIR)/wc.o
WCTIME_TEST_OBJ = $(WC_TEST_DIR)/wcTime.o
WC_OBJ = $(WC_ORIG_DIR)/wc.o
WCTIME_OBJ = $(WC_ORIG_DIR)/wcTime.o

WC_LL = $(WC_ORIG_DIR)/wc.ll
WCTIME_LL = $(WC_ORIG_DIR)/wcTime.ll
# ifeq ($(PERF), 1) 
# 	WC_LL = $(WC_TEST_DIR)/wc.ll
# 	WCTIME_LL = $(WC_TEST_DIR)/wcTime.ll
# endif 
WC_PERF_LL = $(WC_TEST_DIR)/wc-perf.ll
WCTIME_PERF_LL = $(WC_TEST_DIR)/wcTime-perf.ll

# possible targets
WC_LINK_LL = $(WC_ORIG_DIR)/wcLink.ll
WC_INSTR = $(WC_ORIG_DIR)/wc-instr

WC_LINK_PERF_LL = $(WC_TEST_DIR)/wcLink-perf.ll
WC_PERF = $(WC_TEST_DIR)/wc-perf

WC_TEST = $(WC_TEST_DIR)/wc
WC = $(WC_ORIG_DIR)/wc

###############################################################################
# Classify: intermediate files
###############################################################################
# source code paths: test vs. original
CLASSIFY_ORIG_DIR = $(WORK_DIR)/classify-cp/decisionTree
CLASSIFYTIME_ORIG_DIR = $(WORK_DIR)/classify-cp/bench
CLASSIFY_TEST_DIR = $(WORK_DIR)/classify-test/decisionTree
CLASSIFYTIME_TEST_DIR = $(WORK_DIR)/classify-test/bench

CLASSIFY_ORIG_SRC = $(CLASSIFY_ORIG_DIR)/classify.C
CLASSIFYTIME_ORIG_SRC = $(CLASSIFYTIME_ORIG_DIR)/classifyTime.C
CLASSIFY_TEST_SRC = $(CLASSIFY_TEST_DIR)/classify.C
CLASSIFYTIME_TEST_SRC = $(CLASSIFYTIME_TEST_DIR)/classifyTime.C

# object paths: 3 modes, test, instr, original
CLASSIFY_INSTR_OBJ = $(CLASSIFY_ORIG_DIR)/classify-instr.o
CLASSIFYTIME_INSTR_OBJ = $(CLASSIFY_ORIG_DIR)/classifyTime-instr.o
CLASSIFY_TEST_OBJ = $(CLASSIFY_TEST_DIR)/classify.o
CLASSIFYTIME_TEST_OBJ = $(CLASSIFY_TEST_DIR)/classifyTime.o
CLASSIFY_OBJ = $(CLASSIFY_ORIG_DIR)/classify.o
CLASSIFYTIME_OBJ = $(CLASSIFY_ORIG_DIR)/classifyTime.o
CLASSIFY_PERF_OBJ = $(CLASSIFY_TEST_DIR)/classify-perf.o
CLASSIFYTIME_PERF_OBJ = $(CLASSIFY_TEST_DIR)/classifyTime-perf.o

CLASSIFY_LL = $(CLASSIFY_ORIG_DIR)/classify.ll
CLASSIFYTIME_LL = $(CLASSIFY_ORIG_DIR)/classifyTime.ll
CLASSIFY_PERF_LL = $(CLASSIFY_TEST_DIR)/classify-perf.ll
CLASSIFYTIME_PERF_LL = $(CLASSIFY_TEST_DIR)/classifyTime-perf.ll

# possible targets
CLASSIFY_LINK_PERF_LL = $(CLASSIFY_TEST_DIR)/classifyLink-perf.ll
CLASSIFY_PERF = $(CLASSIFY_TEST_DIR)/classify-perf

CLASSIFY_LINK_LL = $(CLASSIFY_ORIG_DIR)/classifyLink.ll
CLASSIFY_TEST = $(CLASSIFY_TEST_DIR)/classify
CLASSIFY_INSTR = $(CLASSIFY_ORIG_DIR)/classify-instr
CLASSIFY = $(CLASSIFY_ORIG_DIR)/classify

###############################################################################
# all rule: 
###############################################################################
all: $(DELAUNAY_INSTR) $(DELAUNAY_LINK_LL) $(DELAUNAY) $(DELAUNAY_TEST) $(DELAUNAY_PERF) \
	 $(WC_INSTR) $(WC_LINK_LL) $(WC) $(WC_TEST) $(WC_PERF) \
	 $(CLASSIFY_INSTR) $(CLASSIFY_LINK_LL) $(CLASSIFY) $(CLASSIFY_TEST)

###############################################################################
# CLASSIFY: make rules
###############################################################################
# classifyLink.ll: produced by ModulePrinter.so to ran ParallelForDebugInfo.so to derive .cilkfor.json
$(CLASSIFY_LINK_LL): $(CLASSIFY_LL) $(CLASSIFYTIME_LL)
	$(LLVM_LINK) $^ -S -o $@

$(CLASSIFY_LL): $(CLASSIFY_ORIG_SRC)
	TESTNAME=classify $(CXX) $(CXXFLAGS_LL) -S -emit-llvm -o $(CLASSIFY_ORIG_DIR)/unused.ll -c $< \
		&> $(CLASSIFY_ORIG_DIR)/warning.$(notdir $@).log
	@mv ./classify.ll $@
	@test -f $@ || { echo "Error: $@ was not created."; exit 1; }

$(CLASSIFYTIME_LL): $(CLASSIFYTIME_ORIG_SRC)
	TESTNAME=classifyTime $(CXX) $(CXXFLAGS_LL) -S -emit-llvm -o $(CLASSIFY_ORIG_DIR)/unused.ll -c $< \
		&> $(CLASSIFY_ORIG_DIR)/warning.$(notdir $@).log
	@mv ./classifyTime.ll $@
	@test -f $@ || { echo "Error: $@ was not created."; exit 1; }

# wcLink.ll: produced by ModulePrinter.so to ran ParallelForDebugInfo.so to derive .cilkfor.json
$(CLASSIFY_LINK_PERF_LL): $(CLASSIFY_PERF_LL) $(CLASSIFYTIME_PERF_LL)
	$(LLVM_LINK) $^ -S -o $@

$(CLASSIFY_PERF_LL): $(CLASSIFY_TEST_SRC)
	TESTNAME=classify $(CXX) $(CXXFLAGS_PROFILE_LL) -S -emit-llvm -o $(CLASSIFY_TEST_DIR)/unused.ll -c $< \
		&> $(CLASSIFY_TEST_DIR)/warning.$(notdir $@).log
	@mv ./classify.ll $@
	@test -f $@ || { echo "Error: $@ was not created."; exit 1; }

$(CLASSIFYTIME_PERF_LL): $(CLASSIFYTIME_TEST_SRC)
	TESTNAME=classifyTime $(CXX) $(CXXFLAGS_PROFILE_LL) -S -emit-llvm -o $(CLASSIFY_TEST_DIR)/unused.ll -c $< \
		&> $(CLASSIFY_TEST_DIR)/warning.$(notdir $@).log
	@mv ./classifyTime.ll $@
	@test -f $@ || { echo "Error: $@ was not created."; exit 1; }

# delauany exectuable for instrumentation checking; ran instrumented executable to derive .instr.json
$(CLASSIFY_INSTR): $(CLASSIFYTIME_INSTR_OBJ) $(CLASSIFY_INSTR_OBJ)
	$(CXX) -o $@ $^ $(CXXFLAGS_INSTR) $(LDFLAGS_INSTR) &> $(CLASSIFY_ORIG_DIR)/warning.$(notdir $@).log

$(CLASSIFY_INSTR_OBJ): $(CLASSIFY_ORIG_SRC)
	$(CXX) $(CXXFLAGS_INSTR) -c $< -o $@ &> $(CLASSIFY_ORIG_DIR)/warning.$(notdir $@).log

$(CLASSIFYTIME_INSTR_OBJ): $(CLASSIFYTIME_ORIG_SRC)
	$(CXX) $(CXXFLAGS_INSTR) -c $< -o $@ &> $(CLASSIFY_ORIG_DIR)/warning.$(notdir $@).log

# wc exectuable for experimental group performance measurement
$(CLASSIFY_TEST): $(CLASSIFYTIME_TEST_OBJ) $(CLASSIFY_TEST_OBJ)
	$(CXX) -o $@ $^ $(CXXFLAGS_RUN) $(LDFLAGS) &> $(CLASSIFY_TEST_DIR)/warning.$(notdir $@).log

$(CLASSIFY_TEST_OBJ): $(CLASSIFY_TEST_SRC)
	$(CXX) $(CXXFLAGS_RUN) -c $< -o $@ &> $(CLASSIFY_TEST_DIR)/warning.$(notdir $@).log

$(CLASSIFYTIME_TEST_OBJ): $(CLASSIFYTIME_TEST_SRC)
	$(CXX) $(CXXFLAGS_RUN) -c $< -o $@ &> $(CLASSIFY_TEST_DIR)/warning.$(notdir $@).log

# classify exectuable for control group performance measurement
$(CLASSIFY): $(CLASSIFYTIME_OBJ) $(CLASSIFY_OBJ)
	$(CXX) -o $@ $^ $(CXXFLAGS_RUN) $(LDFLAGS) &> $(CLASSIFY_ORIG_DIR)/warning.$(notdir $@).log

$(CLASSIFY_OBJ): $(CLASSIFY_ORIG_SRC)
	$(CXX) $(CXXFLAGS_RUN) -c $< -o $@ &> $(CLASSIFY_ORIG_DIR)/warning.$(notdir $@).log

$(CLASSIFYTIME_OBJ): $(CLASSIFYTIME_ORIG_SRC)
	$(CXX) $(CXXFLAGS_RUN) -c $< -o $@ &> $(CLASSIFY_ORIG_DIR)/warning.$(notdir $@).log

# classify perf profiling
$(CLASSIFY_PERF): $(CLASSIFYTIME_PERF_OBJ) $(CLASSIFY_PERF_OBJ)
	$(CXX) -o $@ $^ $(CXXFLAGS_PROFILE) $(LDFLAGS_PROFILE) &> $(CLASSIFY_TEST_DIR)/warning.$(notdir $@).log

$(CLASSIFY_PERF_OBJ): $(CLASSIFY_TEST_SRC)
	$(CXX) $(CXXFLAGS_PROFILE) -c $< -o $@ &> $(CLASSIFY_TEST_DIR)/warning.$(notdir $@).log

$(CLASSIFYTIME_PERF_OBJ): $(CLASSIFYTIME_TEST_SRC)
	$(CXX) $(CXXFLAGS_PROFILE) -c $< -o $@ &> $(CLASSIFY_TEST_DIR)/warning.$(notdir $@).log

###############################################################################
# WC_COUNT: make rules
###############################################################################
# wcLink.ll: produced by ModulePrinter.so to ran ParallelForDebugInfo.so to derive .cilkfor.json
$(WC_LINK_LL): $(WC_LL) $(WCTIME_LL)
	$(LLVM_LINK) $^ -S -o $@

$(WC_LL): $(WC_ORIG_SRC)
	TESTNAME=wc $(CXX) $(CXXFLAGS_LL) -S -emit-llvm -o $(WC_ORIG_DIR)/unused.ll -c $< \
		&> $(WC_ORIG_DIR)/warning.$(notdir $@).log
	@mv ./wc.ll $@
	@test -f $@ || { echo "Error: $@ was not created."; exit 1; }

$(WCTIME_LL): $(WCTIME_ORIG_SRC)
	TESTNAME=wcTime $(CXX) $(CXXFLAGS_LL) -S -emit-llvm -o $(WC_ORIG_DIR)/unused.ll -c $< \
		&> $(WC_ORIG_DIR)/warning.$(notdir $@).log
	@mv ./wcTime.ll $@
	@test -f $@ || { echo "Error: $@ was not created."; exit 1; }

# wcLink.ll: produced by ModulePrinter.so to ran ParallelForDebugInfo.so to derive .cilkfor.json
$(WC_LINK_PERF_LL): $(WC_PERF_LL) $(WCTIME_PERF_LL)
	$(LLVM_LINK) $^ -S -o $@

$(WC_PERF_LL): $(WC_TEST_SRC)
	TESTNAME=wc $(CXX) $(CXXFLAGS_PROFILE_LL) -S -emit-llvm -o $(WC_TEST_DIR)/unused.ll -c $< \
		&> $(WC_TEST_DIR)/warning.$(notdir $@).log
	@mv ./wc.ll $@
	@test -f $@ || { echo "Error: $@ was not created."; exit 1; }

$(WCTIME_PERF_LL): $(WCTIME_TEST_SRC)
	TESTNAME=wcTime $(CXX) $(CXXFLAGS_PROFILE_LL) -S -emit-llvm -o $(WC_TEST_DIR)/unused.ll -c $< \
		&> $(WC_TEST_DIR)/warning.$(notdir $@).log
	@mv ./wcTime.ll $@
	@test -f $@ || { echo "Error: $@ was not created."; exit 1; }

# delauany exectuable for instrumentation checking; ran instrumented executable to derive .instr.json
$(WC_INSTR): $(WCTIME_INSTR_OBJ) $(WC_INSTR_OBJ)
	$(CXX) -o $@ $^ $(CXXFLAGS_INSTR) $(LDFLAGS_INSTR) &> $(WC_ORIG_DIR)/warning.$(notdir $@).log
$(WC_INSTR_OBJ): $(WC_ORIG_SRC)
	$(CXX) $(CXXFLAGS_INSTR) -c $< -o $@ &> $(WC_ORIG_DIR)/warning.$(notdir $@).log

$(WCTIME_INSTR_OBJ): $(WCTIME_ORIG_SRC)
	$(CXX) $(CXXFLAGS_INSTR) -c $< -o $@ &> $(WC_ORIG_DIR)/warning.$(notdir $@).log

# wc exectuable for experimental group performance measurement
$(WC_TEST): $(WCTIME_TEST_OBJ) $(WC_TEST_OBJ)
	$(CXX) -o $@ $^ $(CXXFLAGS_RUN) $(LDFLAGS) &> $(WC_TEST_DIR)/warning.$(notdir $@).log

$(WC_TEST_OBJ): $(WC_TEST_SRC)
	$(CXX) $(CXXFLAGS_RUN) -c $< -o $@ &> $(WC_TEST_DIR)/warning.$(notdir $@).log

$(WCTIME_TEST_OBJ): $(WCTIME_TEST_SRC)
	$(CXX) $(CXXFLAGS_RUN) -c $< -o $@ &> $(WC_TEST_DIR)/warning.$(notdir $@).log

# wc exectuable for control group performance measurement
$(WC): $(WCTIME_OBJ) $(WC_OBJ)
	$(CXX) -o $@ $^ $(CXXFLAGS_RUN) $(LDFLAGS) &> $(WC_ORIG_DIR)/warning.$(notdir $@).log

$(WC_OBJ): $(WC_ORIG_SRC)
	$(CXX) $(CXXFLAGS_RUN) -c $< -o $@ &> $(WC_ORIG_DIR)/warning.$(notdir $@).log

$(WCTIME_OBJ): $(WCTIME_ORIG_SRC)
	$(CXX) $(CXXFLAGS_RUN) -c $< -o $@ &> $(WC_ORIG_DIR)/warning.$(notdir $@).log

# wc perf profiling
$(WC_PERF): $(WCTIME_PERF_OBJ) $(WC_PERF_OBJ)
	$(CXX) -o $@ $^ $(CXXFLAGS_PROFILE) $(LDFLAGS_PROFILE) &> $(WC_TEST_DIR)/warning.$(notdir $@).log

$(WC_PERF_OBJ): $(WC_TEST_SRC)
	$(CXX) $(CXXFLAGS_PROFILE) -c $< -o $@ &> $(WC_TEST_DIR)/warning.$(notdir $@).log

$(WCTIME_PERF_OBJ): $(WCTIME_TEST_SRC)
	$(CXX) $(CXXFLAGS_PROFILE) -c $< -o $@ &> $(WC_TEST_DIR)/warning.$(notdir $@).log

###############################################################################
# DELAUNAY_TRIANGULATION: make rule
###############################################################################
# delaunayLink.ll: produced by ModulePrinter.so to ran ParallelForDebugInfo.so to derive .cilkfor.json
$(DELAUNAY_LINK_LL): $(DELAUNAY_LL) $(DELAUNAYTIME_LL)
	$(LLVM_LINK) $^ -S -o $@

$(DELAUNAY_LL): $(DELAUNAY_ORIG_SRC)
	TESTNAME=delaunay $(CXX) $(CXXFLAGS_LL) -S -emit-llvm -o $(DELAUNAY_ORIG_DIR)/unused.ll -c $< \
		&> $(DELAUNAY_ORIG_DIR)/warning.$(notdir $@).log
	@mv ./delaunay.ll $@
	@test -f $@ || { echo "Error: $@ was not created."; exit 1; }

$(DELAUNAYTIME_LL): $(DELAUNAYTIME_ORIG_SRC)
	TESTNAME=delaunayTime $(CXX) $(CXXFLAGS_LL) -S -emit-llvm -o $(DELAUNAY_ORIG_DIR)/unused.ll -c $< \
		&> $(DELAUNAY_ORIG_DIR)/warning.$(notdir $@).log
	@mv ./delaunayTime.ll $@
	@test -f $@ || { echo "Error: $@ was not created."; exit 1; }

# delaunayLink-perf.ll: 
$(DELAUNAY_LINK_PERF_LL): $(DELAUNAY_PERF_LL) $(DELAUNAYTIME_PERF_LL)
	$(LLVM_LINK) $^ -S -o $@

$(DELAUNAY_PERF_LL): $(DELAUNAY_TEST_SRC)
	TESTNAME=delaunay $(CXX) $(CXXFLAGS_PROFILE_LL) -S -emit-llvm -o $(DELAUNAY_TEST_DIR)/unused.ll -c $< \
		&> $(DELAUNAY_ORIG_DIR)/warning.$(notdir $@).log
	@mv ./delaunay.ll $@
	@test -f $@ || { echo "Error: $@ was not created."; exit 1; }

$(DELAUNAYTIME_PERF_LL): $(DELAUNAYTIME_TEST_SRC)
	TESTNAME=delaunayTime $(CXX) $(CXXFLAGS_PROFILE_LL) -S -emit-llvm -o $(DELAUNAY_TEST_DIR)/unused.ll -c $< \
		&> $(DELAUNAY_ORIG_DIR)/warning.$(notdir $@).log
	@mv ./delaunayTime.ll $@
	@test -f $@ || { echo "Error: $@ was not created."; exit 1; }

# delauany exectuable for instrumentation checking; ran instrumented executable to derive .instr.json
$(DELAUNAY_INSTR): $(DELAUNAYTIME_INSTR_OBJ) $(DELAUNAY_INSTR_OBJ)
	$(CXX) -o $@ $^ $(CXXFLAGS_INSTR) $(LDFLAGS_INSTR) &> $(DELAUNAY_ORIG_DIR)/warning.$(notdir $@).log

$(DELAUNAY_INSTR_OBJ): $(DELAUNAY_ORIG_SRC)
	$(CXX) $(CXXFLAGS_INSTR) -c $< -o $@ &> $(DELAUNAY_ORIG_DIR)/warning.$(notdir $@).log

$(DELAUNAYTIME_INSTR_OBJ): $(DELAUNAYTIME_ORIG_SRC)
	$(CXX) $(CXXFLAGS_INSTR) -c $< -o $@ &> $(DELAUNAY_ORIG_DIR)/warning.$(notdir $@).log

# delauany exectuable for experimental group performance measurement
$(DELAUNAY_TEST): $(DELAUNAYTIME_TEST_OBJ) $(DELAUNAY_TEST_OBJ)
	$(CXX) -o $@ $^ $(CXXFLAGS_RUN) $(LDFLAGS) &> $(DELAUNAY_TEST_DIR)/warning.$(notdir $@).log

$(DELAUNAY_TEST_OBJ): $(DELAUNAY_TEST_SRC)
	$(CXX) $(CXXFLAGS_RUN) -c $< -o $@ &> $(DELAUNAY_TEST_DIR)/warning.$(notdir $@).log

$(DELAUNAYTIME_TEST_OBJ): $(DELAUNAYTIME_TEST_SRC)
	$(CXX) $(CXXFLAGS_RUN) -c $< -o $@ &> $(DELAUNAY_TEST_DIR)/warning.$(notdir $@).log

# delauany exectuable for control group performance measurement
$(DELAUNAY): $(DELAUNAYTIME_OBJ) $(DELAUNAY_OBJ)
	$(CXX) -o $@ $^ $(CXXFLAGS_RUN) $(LDFLAGS) &> $(DELAUNAY_ORIG_DIR)/warning.$(notdir $@).log

$(DELAUNAY_OBJ): $(DELAUNAY_ORIG_SRC)
	$(CXX) $(CXXFLAGS_RUN) -c $< -o $@ &> $(DELAUNAY_ORIG_DIR)/warning.$(notdir $@).log

$(DELAUNAYTIME_OBJ): $(DELAUNAYTIME_ORIG_SRC)
	$(CXX) $(CXXFLAGS_RUN) -c $< -o $@ &> $(DELAUNAY_ORIG_DIR)/warning.$(notdir $@).log

# wc perf profiling
$(DELAUNAY_PERF): $(DELAUNAYTIME_PERF_OBJ) $(DELAUNAY_PERF_OBJ)
	$(CXX) -o $@ $^ $(CXXFLAGS_PROFILE) $(LDFLAGS_PROFILE) &> $(DELAUNAY_TEST_DIR)/warning.$(notdir $@).log

$(DELAUNAY_PERF_OBJ): $(DELAUNAY_TEST_SRC)
	$(CXX) $(CXXFLAGS_PROFILE) -c $< -o $@ &> $(DELAUNAY_TEST_DIR)/warning.$(notdir $@).log

$(DELAUNAYTIME_PERF_OBJ): $(DELAUNAYTIME_TEST_SRC)
	$(CXX) $(CXXFLAGS_PROFILE) -c $< -o $@ &> $(DELAUNAY_TEST_DIR)/warning.$(notdir $@).log


# Temporary file
.PHONY: all CLEAN_DELAUNAY_ANALYSIS CLEAN_DELAUNAY_PERF CLEAN_WC_ANALYSIS CLEAN_WC_PERF CLEAN_CLASSIFY_ANALYSIS CLEAN_CLASSIFY_PERF
CLEAN_DELAUNAY_ANALYSIS:
	@echo "Delaunay Analysis Fresh Start..."
	@rm -f $(DELAUNAY_ORIG_DIR)/unused.ll $(DELAUNAY_ORIG_DIR)/*.ll \
		  $(DELAUNAY_INSTR) $(DELAUNAY_INSTR_OBJ) $(DELAUNAYTIME_INSTR_OBJ) \
		  $(DELAUNAY_LINK_LL) $(DELAUNAY_LL) $(DELAUNAYTIME_LL)
CLEAN_DELAUNAY_TEST:
	@echo "Delaunay Performance Experiment Fresh Start..."
	@rm -f $(DELAUNAY) $(DELAUNAY_OBJ) $(DELAUNAYTIME_OBJ) \
		  $(DELAUNAY_TEST) $(DELAUNAY_TEST_OBJ) $(DELAUNAYTIME_TEST_OBJ)
CLEAN_DELAUNAY_PERF:
	@echo "Delaunay Performance Profiling Fresh Start..."
	@rm -f $(DELAUNAY_PERF) $(DELAUNAY_PERF_OBJ) $(DELAUNAYTIME_PERF_OBJ) \
		  $(DELAUNAY_TEST_DIR)/{unused.ll,delaunay-perf.ll,delaunayTime-perf.ll,delaunayLink-perf.ll}
CLEAN_WC_ANALYSIS:
	@echo "WordCounts Analysis Fresh Start..."
	@rm -f $(WC_ORIG_DIR)/unused.ll $(WC_ORIG_DIR)/*.ll \
		$(WC_INSTR) $(WC_INSTR_OBJ) $(WCTIME_INSTR_OBJ) \
		$(WC_LINK_LL) $(WC_LL) $(WCTIME_LL)
CLEAN_WC_TEST:
	@echo "WordCounts Performance Experiment Fresh Start..."
	@rm -f $(WC_TEST) $(WC_TEST_OBJ) $(WCTIME_TEST_OBJ) \
		$(WC) $(WC_OBJ) $(WCTIME_OBJ) 
CLEAN_WC_PERF: 
	@echo "WordCounts Performance profiling Fresh Start..."
	@rm -f $(WC_TEST_DIR)/{unused.ll,*.ll,wc-perf,wc-perf.o,wcTime-perf.o,wcLink.ll,wc.ll,wcTime.ll}

CLEAN_CLASSIFY_ANALYSIS:
	@echo "Classify Analysis Fresh Start..."
	@rm -f $(CLASSIFY_ORIG_DIR)/unused.ll $(CLASSIFY_ORIG_DIR)/*.ll \
		$(CLASSIFY_INSTR) $(CLASSIFY_INSTR_OBJ) $(CLASSIFYTIME_INSTR_OBJ) \
		$(CLASSIFY_LINK_LL) $(CLASSIFY_LL) $(CLASSIFYTIME_LL)
CLEAN_CLASSIFY_TEST:
	@echo "Classify Performance Experiment Fresh Start..."
	@rm -f $(CLASSIFY_TEST) $(CLASSIFY_TEST_OBJ) $(CLASSIFYTIME_TEST_OBJ) \
		$(CLASSIFY) $(CLASSIFY_OBJ) $(CLASSIFYTIME_OBJ)
CLEAN_CLASSIFY_PERF: 
	@echo "classify Performance profiling Fresh Start..."
	@rm -f $(CLASSIFY_TEST_DIR)/{unused.ll,*.ll,classify-perf,classify-perf.o,classifyTime-perf.o,classifyLink.ll,classify.ll,classifyTime.ll}

		