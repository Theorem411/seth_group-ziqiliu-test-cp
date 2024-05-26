all: LazydProfilingPerfPlugin.so libLazydProfilingPerf.so

CXX = /afs/ece/project/seth_group/ziqiliu/GCC-12.2.0/bin/g++-12.2.0
CXXFLAGS = -rdynamic $(shell llvm-config --cxxflags) -gdwarf-2 -O0 -fPIC -I/afs/ece/project/seth_group/ziqiliu/json/single_include

LazydProfilingPerfPlugin.so: LazydProfilingPerfPass.cpp
	$(CXX) $(CXXFLAGS) -c $^ -o temp.o
	$(CXX) -fPIC -dylib -shared temp.o -o $@
	
libLazydProfilingPerf.so: LazydProfilingPerfLibrary.cpp
	$(CXX) $(CXXFLAGS) -c $^ -o temp.o
	$(CXX) -fPIC -dylib -shared temp.o -o $@
	
.INTERMEDIATE: temp.o
post-build:
	@rm -f temp.o

.PHONY: clean all

clean: 
	@echo "clean performance instrumentation library..."
	@rm -f LazydProfilingPerfPlugin.so libLazydProfilingPerf.so