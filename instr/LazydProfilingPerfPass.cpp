#include "llvm/PassRegistry.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/IR/PassManager.h"
#include "llvm/ADT/SmallSet.h"
#include "llvm/ADT/SmallVector.h"
#include "llvm/ADT/DenseMap.h"
#include "llvm/ADT/Statistic.h"
#include "llvm/ADT/StringRef.h"
#include "llvm/ADT/PostOrderIterator.h"
#include "llvm/IR/Attributes.h"
#include "llvm/IR/CallingConv.h"
#include "llvm/IR/GlobalValue.h"
#include "llvm/IR/DebugLoc.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/InstIterator.h"
#include "llvm/IR/GlobalVariable.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Type.h"
#include "llvm/IR/Intrinsics.h"
#include "llvm/IR/DerivedTypes.h"
#include "llvm/IR/Constant.h"
#include "llvm/IR/CFG.h"
#include "llvm/Analysis/TapirTaskInfo.h"
#include "llvm/Analysis/LoopInfo.h"
#include "llvm/Analysis/LoopIterator.h"
#include "llvm/Transforms/Utils/TapirUtils.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include "llvm/Transforms/Utils.h" // for LoopSimplifyID
#include "llvm/Transforms/Utils/ValueMapper.h"

#define PROFILING_NAME "profile-performance"
#define DEBUG_TYPE PROFILING_NAME

using namespace llvm;

namespace {
//== callgraph utitlities
using ReverseCallGraph = DenseMap<Function *, SmallSet<Instruction *, 4>>;
//== LazydProfilingPerf implementation =============================
struct LazydProfilingPerfImpl {
    LazydProfilingPerfImpl(Module &M, ReverseCallGraph &RCG) 
        : M(M), RCG(RCG) {}
    void preprocess(SmallVector<Function *>& , SmallSet<Function *, 4>& );
    bool run(Function *F, bool mode);
private: 
    // preprocessor functions
    void collectBuiltinIntrinsic(SmallVector<Function *>& , SmallSet<Function *, 4>& );
    // transformer functions
    bool cleanupBuiltinIntrinsic(Function *F);
    bool insertLazydProfilingCall(Function *F);
    bool insertLazydProfilingPerf(Function *F);
private: 
    Module &M;
    ReverseCallGraph &RCG;
    // created by preprocess, consumed by run
    DenseMap<Function *, SmallVector<CallInst *>> INTRINSICS;
    DenseMap<Function *, SmallSet<Instruction *, 4>> CALLSITES;
};

void LazydProfilingPerfImpl::preprocess(SmallVector<Function *> &perfWorkList, SmallSet<Function *, 4> &callWorkSet) {
    /**-- proprocess -----------------------------------
     collect:
     * list of @llvm.uli.lazyd.perf: SmallVector<Instruction *>
     * list of target callsites: SmallVector<Instruction *>
    */
    collectBuiltinIntrinsic(perfWorkList, callWorkSet);
}

void LazydProfilingPerfImpl::collectBuiltinIntrinsic(SmallVector<Function *> &perfWorkList, SmallSet<Function *, 4> &callWorkList) {
    // collect list of __builtin_uli_lazyd_perf intrinsic for replacement
    CallInst *CI = nullptr;
    Function *Intrinsic = nullptr;
    for (Function &F : M) {
        bool modify = false;
        for (auto It = inst_begin(&F), E = inst_end(&F); It != E; ++It) {
            Instruction *I = &*It;
            if ((CI = dyn_cast<CallInst>(I))
                && (Intrinsic = CI->getCalledFunction())
                && (Intrinsic->getIntrinsicID() == Intrinsic::uli_lazyd_perf)) 
            {
                // collect @llvm.uli.lazyd.perf for F
                INTRINSICS[&F].push_back(CI);
                // add this func to worklist
                modify = true;
            }
        }
        if (modify) {
            // F contains @llvm.uli.lazyd.perf; push F to worklist
            perfWorkList.push_back(&F);
            // collect all callsites of F, keyed by their parent (not F!)
            for (Instruction *F_Callsite : RCG[&F]) {
                CALLSITES[F_Callsite->getFunction()].insert(F_Callsite);
                callWorkList.insert(F_Callsite->getFunction());
            }
        }
    }
}

bool LazydProfilingPerfImpl::LazydProfilingPerfImpl::run(Function *F, bool mode) {
    if (mode) {
        /** -- transformation 1 ----------------------------------------
        transform: 
        * replace each @llvm.uli.lazyd.perf with @lazydProfilingPerf (1st arg of @llvm.uli.lazyd.perf)
        */
        return insertLazydProfilingPerf(F);
    } else {
        /** -- transformation 0 ---------------------------------------
        transform: 
        * for each target callsites, insert before it call to @lazydProfilingCall
        - 1st arg: CalleeLink, callsite's getCalledFunction()->getName()
        - 2nd arg: CallerLink, callsite's getParent()->getName()
        */
        return insertLazydProfilingCall(F);
    }
}

bool LazydProfilingPerfImpl::cleanupBuiltinIntrinsic(Function *F) {
    bool Changed = false;
    for (CallInst *I : INTRINSICS[F]) {
        I->eraseFromParent();
        Changed = true;
    }
    return Changed;
}

bool LazydProfilingPerfImpl::insertLazydProfilingCall(Function *F) {
    Module *M = F->getParent();
    LLVMContext &ctx = F->getContext();
    IRBuilder<> builder(ctx);
    // LLVM Data Types and Constant
    IntegerType *I32 = IntegerType::getInt32Ty(ctx);
    IntegerType *I64 = IntegerType::getInt64Ty(ctx);
    Type *I8Ptr = PointerType::get(Type::getInt8Ty(ctx), 0);

    Value *idx_zero = ConstantInt::get(Type::getInt64Ty(ctx), 0);
    // declare FucntionCallee: lazydProfilingCall   
    FunctionType *CallsiteFnTy = FunctionType::get(
        /*Result*/Type::getVoidTy(ctx),
        /*Params*/{ /*calleelink*/I8Ptr, /*callsiteloc*/I8Ptr, /*callerlink*/I8Ptr },
        /*isVarArg*/false
    );
    FunctionCallee LAZYD_PROFILING_CALL = M->getOrInsertFunction(
        "lazydProfilingCall", 
        CallsiteFnTy
    );
    // insert call to @lazydProfilingCall before each target callsites in F
    bool Changed = false;
    for (Instruction *Callsite_I : CALLSITES[F]) {
        Function *Callee = nullptr;
        if (auto *CI = dyn_cast<CallInst>(Callsite_I)) {
            Callee = CI->getCalledFunction();
        } else if (auto *VI = dyn_cast<InvokeInst>(Callsite_I)) {
            Callee = VI->getCalledFunction();
        }
        assert(Callee && "reverse call graph found callsite instruction without callee function!");

        Function *Caller = Callsite_I->getFunction();
        // prep args of library func @lazydProfilingCall(callee_link, caller_link)
        /* 1st arg: calleelink */
        GlobalVariable *CALLEE_LINK_GLOB = builder.CreateGlobalString(
            Callee->getName(),
            "calleelink",
            0, M
        );
        Value *CALLEE_LINK = builder.CreateInBoundsGEP(
            /*Ty*/CALLEE_LINK_GLOB->getValueType(),
            /*Ptr*/CALLEE_LINK_GLOB,
            /*IdxList*/{idx_zero, idx_zero}
        );  

        /* 2nd argument: callsite_loc */
        std::string callsite;
        {
            DILocation *DIL = Callsite_I->getDebugLoc().get();
            while (DIL->getInlinedAt()) {
                DIL = DIL->getInlinedAt();
            }
            assert(DIL);
            std::string file = DIL->getScope()->getFilename().str();
            std::string ln = std::to_string(DIL->getLine());
            std::string col = std::to_string(DIL->getColumn());
            callsite = file + ":" + ln + ":" + col;
        }
        GlobalVariable *CALLSITE_LOC_GLOB = builder.CreateGlobalString(
            StringRef(callsite),
            "callsiteloc",
            0, M
        );
        Value *CALLSITE_LOC = builder.CreateInBoundsGEP(
            /*Ty*/CALLSITE_LOC_GLOB->getValueType(),
            /*Ptr*/CALLSITE_LOC_GLOB,
            /*IdxList*/{idx_zero, idx_zero}
        );  

        /* 3rd arg: callerlink */
        GlobalVariable *CALLER_LINK_GLOB = builder.CreateGlobalString(
            Caller->getName(),
            "callerlink",
            0, M
        );
        Value *CALLER_LINK = builder.CreateInBoundsGEP(
            /*Ty*/CALLER_LINK_GLOB->getValueType(),
            /*Ptr*/CALLER_LINK_GLOB,
            /*IdxList*/{idx_zero, idx_zero}
        );  

        // insert call to library func @lazydProfilingCall
        builder.SetInsertPoint(Callsite_I);
        auto *Inserted = builder.CreateCall(
            /*FunctionCallee*/LAZYD_PROFILING_CALL,
            /*Args*/{ CALLEE_LINK, CALLSITE_LOC, CALLER_LINK }
        );

        Changed = true;
    }
    return Changed;
}

bool LazydProfilingPerfImpl::insertLazydProfilingPerf(Function *F) {
    Module *M = F->getParent();
    LLVMContext &ctx = F->getContext();
    IRBuilder<> builder(ctx);

    // LLVM Data Types and Constant
    IntegerType *I32 = IntegerType::getInt32Ty(ctx);
    IntegerType *I64 = IntegerType::getInt64Ty(ctx);
    Type *I8Ptr = PointerType::get(Type::getInt8Ty(ctx), 0);
    
    Value *idx_zero = ConstantInt::get(Type::getInt64Ty(ctx), 0);

    FunctionType *FnTy = FunctionType::get(
        /* Result */Type::getVoidTy(ctx),
        /* Params */{
            /*version*/I32, 
            /*tripcount*/I64, 
            /*granularity*/I64, 
            /*depth*/I32,
            /*callerlinkname*/I8Ptr,
            /*src diloc*/I8Ptr, 
            /*inline diloc*/I8Ptr
        },
        /* isVarArg */false
    );
    PointerType *FnPtrTy = PointerType::get(FnTy, 0);

    // replace each @llvm.uli.lazyd.perf with @lazydProfilingPerf
    bool Changed = false;
    for (CallInst *Intrinsic : INTRINSICS[F]) {
        /** libfunc call arguments preparation; checklist (by position)
            * 1. parallel_for version (0/1/2)
            * 2. tripcount
            * 3. granularity
            * 4. depth
            * 5. mangled name of the parent function of @llvm.uli.lazyd.perf
            * 6. DILocation of the source callsite, in format "<file>:<ln>:<col>" (usually opencilk.h)
            * 7. DILocation of the most inlined callsite, in format "<file>:<ln>:<col>"
        */
        Value *FnPtr = Intrinsic->getArgOperand(0);
        assert(FnPtr && "fail to recover lazydProfilingPerf from __builtin_uli_lazyd_perf!");
        Value *Callee = builder.CreateBitCast(
            /*Value*/FnPtr, 
            /*DestTy*/FnPtrTy,
            /*Twine:Name*/"lazydProfilingPerf"
        );
        Value *VERSION = Intrinsic->getArgOperand(1);
        Value *TRIP_COUNT = Intrinsic->getArgOperand(2);
        Value *GRANULARITY = Intrinsic->getArgOperand(3);
        Value *DEPTH = Intrinsic->getArgOperand(4);

        std::string File, Line, Col, iFile, iLine, iCol;
        StringRef CallerLinkageName;
        {
            assert(Intrinsic->getDebugLoc() && Intrinsic->getDebugLoc().get() && "Found __builtin_uli_lazyd_perf without DebugLoc!");
            DILocation *DIL = Intrinsic->getDebugLoc().get();
            assert(DIL);
            File = DIL->getScope()->getFilename().str();
            Line = std::to_string(DIL->getLine());
            Col = std::to_string(DIL->getColumn());
            CallerLinkageName = Intrinsic->getFunction()->getName();
        
            while (DIL->getInlinedAt()) {
                DIL = DIL->getInlinedAt();
            }
            assert(DIL);
            iFile = DIL->getScope()->getFilename().str();
            iLine = std::to_string(DIL->getLine());
            iCol = std::to_string(DIL->getColumn());
        }

        std::string SrcLoc = File + ":" + Line + ":" + Col;
        std::string InlineLoc = iFile + ":" + iLine + ":" + iCol;
        // /// DEBUG: 
        // Intrinsic->print(errs());
        // errs() << '\n' << SrcLoc << '\n' << InlineLoc << '\n';
        // //////////
        GlobalVariable *SRC_CALLER_LINKAGE_GLOB = builder.CreateGlobalString(
            CallerLinkageName,
            "caller_linkname",
            0, /* Default AddressSpace */
            M /* this Module */
        );
        Value *SRC_CALLER_LINKAGE = builder.CreateInBoundsGEP(
            /*Ty*/SRC_CALLER_LINKAGE_GLOB->getValueType(),
            /*Ptr*/SRC_CALLER_LINKAGE_GLOB,
            /*IdxList*/{idx_zero, idx_zero}
        );

        GlobalVariable *SRC_LOC_GLOB = builder.CreateGlobalString(
            StringRef(SrcLoc),
            "loc",
            0, /** Default AddressSpace */
            M /** DEBUG: use this module instead of nullptr */
        );
        Value *SRC_LOC = builder.CreateInBoundsGEP(
            /*Ty*/SRC_LOC_GLOB->getValueType(),
            /*Ptr*/SRC_LOC_GLOB,
            /*IdxList*/{idx_zero, idx_zero}
        );

        GlobalVariable *INLINE_LOC_GLOB = builder.CreateGlobalString(
            StringRef(InlineLoc),
            "iloc",
            0, /* Default AddressSpace */
            M /** DEBUG: use this Module instead of nullptr */
        );
        Value *INLINE_LOC = builder.CreateInBoundsGEP(
            /*Ty*/INLINE_LOC_GLOB->getValueType(),
            /*Ptr*/INLINE_LOC_GLOB,
            /*IdxList*/{idx_zero, idx_zero}
        );

        // insert call to libfunc at @llvm.uli.lazyd.perf
        builder.SetInsertPoint(Intrinsic);
        builder.CreateCall(
            /* FTy */FnTy,
            /* Callee */Callee,
            /* Args */
            { 
                VERSION, 
                TRIP_COUNT, 
                GRANULARITY, 
                DEPTH,
                SRC_CALLER_LINKAGE,
                SRC_LOC,
                INLINE_LOC
            }
        );

        Changed = true;
    }

    /** -- cleanup -----------------------------------------------
     cleanup: 
     * all @llvm.uli.lazyd.perf instruction
    */
    Changed |= cleanupBuiltinIntrinsic(F);
    return Changed;
}

//== LazydProfilingPerf PassInfoMixin register =====================
struct LazydProfilingPerfPass : public PassInfoMixin<LazydProfilingPerfPass> {
    PreservedAnalyses run(Module &M, ModuleAnalysisManager &AM) {
        const auto &CG = AM.getResult<CallGraphAnalysis>(M);
        ReverseCallGraph RCG;
        initRCG(CG, RCG);
        /** -- preprocess ---------------------------------------------
        collect:
        * reverse call graph: DenseMap<Function *, SmallSet<Instruction *>> */
        LazydProfilingPerfImpl impl(M, RCG);
        // preprocess intrinsics: found insertion points; generate functions that need to be modified
            // @lazydProfilingCall insertion point must be collected using a set as the access orderr is sporadic
        SmallVector<Function *> perfWorkList;
        SmallSet<Function *, 4> callWorkSet; 
        impl.preprocess(perfWorkList, callWorkSet);
        // run tranformation on target functions
        bool Changed = false;
        for (Function *F : callWorkSet) {
            // -- transform: insert call to @lazydProfilingCall before callsites of @llvm.uli.lazyd.perf's host call
            Changed |= impl.run(F, 0);
        }
        for (Function *F : perfWorkList) {
            // -- transform: replace @llvm.uli.lazyd.perf with call to @lazydProfilingPerf
            Changed |= impl.run(F, 1);
        }

        if (Changed) 
            return PreservedAnalyses::none();
        return PreservedAnalyses::all();
    }
private: 
    void initRCG(const CallGraph &CG, ReverseCallGraph &RCG) {
        for (auto &it : CG) {
            CallGraphNode *CGN = it.second.get();
            Function *Caller = it.second->getFunction();
            if (!Caller) continue;
            if (Caller->isDeclaration()) continue;
            
            for (CallGraphNode::CallRecord &CR : *CGN) {
                if (!CR.first.hasValue()) {
                    continue;
                }
                Instruction *Callsite = dyn_cast<Instruction>(*CR.first);
                assert(Callsite && "Callrecord cannot find callsite!");
                
                Function *Callee = CR.second->getFunction();
                if (!Callee) continue;
                
                RCG[Callee].insert(Callsite);
            }
        }
    }
};

} // end namespace

PassPluginLibraryInfo getPassPluginInfo() {
    const auto callback = [](PassBuilder &PB) {
        PB.registerPipelineParsingCallback(
            [](StringRef Name, ModulePassManager &PM, auto) {
                if (Name == PROFILING_NAME) {
                    PM.addPass(LazydProfilingPerfPass());
                    return true;
                }
                return false;
            }
        );
        PB.registerTapirLateEPCallback([&](ModulePassManager &MPM, auto) {
            MPM.addPass(LazydProfilingPerfPass());
            return true;
        });
    };
    return { LLVM_PLUGIN_API_VERSION, PROFILING_NAME, "0.0.1", callback };
}

extern "C" LLVM_ATTRIBUTE_WEAK PassPluginLibraryInfo llvmGetPassPluginInfo() {
    return getPassPluginInfo();
}