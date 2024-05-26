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
//== LazydProfilingPerf implementation =============================
struct LazydProfilingPerfImpl {
    LazydProfilingPerfImpl() {}
    bool run(Function &);
};

bool LazydProfilingPerfImpl::run(Function &F) {
    bool Changed = false;
    Module *M = F.getParent();
    LLVMContext &ctx = F.getContext();
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
            /*src diloc*/I8Ptr, 
            /*callerlinkname*/I8Ptr,
            /*inline diloc*/I8Ptr, 
            /*inline callerlinkname*/I8Ptr
        },
        /* isVarArg */false
    );
    PointerType *FnPtrTy = PointerType::get(FnTy, 0);
    
    // collect list of __builtin_uli_lazyd_perf intrinsic for replacement
    CallInst *CI = nullptr;
    Function *Intrinsic = nullptr;
    SmallVector<Instruction *, 8> BUILTIN_ULI_INTRINSICS;
    for (auto It = inst_begin(F), E = inst_end(F); It != E; ++It) {
        Instruction *I = &*It;
        if ((CI = dyn_cast<CallInst>(I))
            && (Intrinsic = CI->getCalledFunction())
            && (Intrinsic->getIntrinsicID() == Intrinsic::uli_lazyd_perf)) 
        {
            BUILTIN_ULI_INTRINSICS.push_back(I);
            /// DEBUG: ////////////
            // I->dump();
            ///////////////////////

            /** libfunc call arguments preparation; checklist (by position)
             * 1. parallel_for version (0/1/2)
             * 2. tripcount
             * 3. granularity
             * 4. depth
             * 5. DILocation of the topmost inlined callsite, in format "<file>:<ln>:<col>"
             * 6. mangled name of the caller of tomost inlined callsite
            */
            Value *FnPtr = CI->getArgOperand(0);
            assert(FnPtr && "fail to recover lazydProfilingPerf from __builtin_uli_lazyd_perf!");
            Value *Callee = builder.CreateBitCast(
                /*Value*/FnPtr, 
                /*DestTy*/FnPtrTy,
                /*Twine:Name*/"lazydProfilingPerf"
            );
            Value *VERSION = CI->getArgOperand(1);
            Value *TRIP_COUNT = CI->getArgOperand(2);
            Value *GRANULARITY = CI->getArgOperand(3);
            Value *DEPTH = CI->getArgOperand(4);

            std::string File, Line, Col, iFile, iLine, iCol;
            StringRef CallerLinkageName, iCallerLinkageName;
            {
                assert(I->getDebugLoc() && I->getDebugLoc().get() && "Found __builtin_uli_lazyd_perf without DebugLoc!");
                DILocation *DIL = I->getDebugLoc().get();
                assert(DIL);
                File = DIL->getScope()->getFilename().str();
                Line = std::to_string(DIL->getLine());
                Col = std::to_string(DIL->getColumn());
                CallerLinkageName = I->getFunction()->getName();
                
                while (DIL->getInlinedAt()) {
                    DIL = DIL->getInlinedAt();
                }
                assert(DIL);
                iFile = DIL->getScope()->getFilename().str();
                iLine = std::to_string(DIL->getLine());
                iCol = std::to_string(DIL->getColumn());

                DIScope *DIS = DIL->getScope();
                while (!dyn_cast<DISubprogram>(DIS)) {
                    DIS = DIS->getScope();
                }
                DISubprogram *DISP = dyn_cast<DISubprogram>(DIS);
                assert(DISP);
                iCallerLinkageName = DISP->getLinkageName();
            }

            std::string SrcLoc = File + ":" + Line + ":" + Col;
            std::string InlineLoc = iFile + ":" + iLine + ":" + iCol;
            I->print(errs());
            errs() << '\n' << SrcLoc << '\n' << InlineLoc << '\n';
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

            GlobalVariable *INLINE_CALLER_LINKAGE_GLOB = builder.CreateGlobalString(
                iCallerLinkageName,
                "inline_caller_linkname",
                0, /* Default AddressSpace */
                M /* this Module */
            );
            Value *INLINE_CALLER_LINKAGE = builder.CreateInBoundsGEP(
                /*Ty*/INLINE_CALLER_LINKAGE_GLOB->getValueType(),
                /*Ptr*/INLINE_CALLER_LINKAGE_GLOB,
                /*IdxList*/{idx_zero, idx_zero}
            );
            // insert call to libfunc at @llvm.uli.lazyd.perf
            builder.SetInsertPoint(I);
            builder.CreateCall(
                /* FTy */FnTy,
                /* Callee */Callee,
                /* Args */
                { 
                    VERSION, 
                    TRIP_COUNT, 
                    GRANULARITY, 
                    DEPTH,
                    SRC_LOC,
                    SRC_CALLER_LINKAGE,
                    INLINE_LOC, 
                    INLINE_CALLER_LINKAGE
                }
            );
        }
    }

    for (auto *I : BUILTIN_ULI_INTRINSICS) {
        I->eraseFromParent();
        Changed = true;
    }

    return Changed;
}

//== LazydProfilingPerf PassInfoMixin register =====================
struct LazydProfilingPerfPass : public PassInfoMixin<LazydProfilingPerfPass> {
    PreservedAnalyses run(Module &M, ModuleAnalysisManager &AM) {
        SmallVector<Function *, 8> WorkList;
        for (Function &F : M) {
            if (!F.empty() && !F.isDeclaration()) {
                WorkList.push_back(&F);
            }
        }
        bool Changed = false;
        for (Function *F : WorkList) {
            Changed |= LazydProfilingPerfImpl().run(*F);
        }
        if (Changed) 
            return PreservedAnalyses::none();
        return PreservedAnalyses::all();
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