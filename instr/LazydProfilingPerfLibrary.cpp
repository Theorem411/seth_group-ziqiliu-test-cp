#include <cassert>
#include <set>
#include <map>
#include <unordered_map>
#include <vector>
#include <mutex>
#include <fstream>
#include <iostream>

/** 
 extern depth variable: definition provided in opencilk.h
*/
extern __thread int delegate_work;

/** base class for log entry type
 */
struct LogEntry {
    LogEntry() {};
    virtual void emit(std::ostream &os) const = 0;
    virtual ~LogEntry() = default;
};

/** used to represent logs generated at __builtin_uli_lazyd_inst callsites
*/
struct LogEntryIntrinsic : public LogEntry {
    LogEntryIntrinsic(int vers, unsigned long tripcount, size_t granularity, int depth, 
            const char *srcCallerName, 
            const char *srcDiloc, const char *inlineDiloc)
            : v(vers), tc(tripcount), g(granularity), d(depth), 
              call(srcCallerName), iloc(inlineDiloc), loc(srcDiloc) {}

    void emit(std::ostream &os) const override {
        os  << "builtin" << ","
            << v << "," // secondary key
            << tc << ","
            << g << ","
            << d << ","
            << call << "," // primary key
            << loc << ","
            << iloc << "\n";
    }
private: 
    int v;
    unsigned long tc;
    size_t g;
    int d;
    std::string loc;
    std::string call;
    std::string iloc;
    std::string icall; 
};

/** used to represent logs generated at callsites of __builtin_uli_lazyd_inst host functions
*/
struct LogEntryCallsite : public LogEntry {
    LogEntryCallsite(const char *callee_link, const char *callsiteLoc, const char *caller_link, int depth) 
        : CalleeLinkName(callee_link), CallsiteLoc(callsiteLoc), CallerLinkName(caller_link), depth(depth) {}

    void emit(std::ostream &os) const override {
        os  << "calledat" << ","
            << CalleeLinkName << ","
            << CallsiteLoc << ","
            << CallerLinkName << ","
            << depth << "\n";
    }
private:
    std::string CalleeLinkName;
    std::string CallsiteLoc;
    std::string CallerLinkName;
    int depth;
};

struct Log {
    Log() {
        // open file "<test>.perf.log"
        std::string testname("undefined");
        const char *env = getenv("TESTNAME");
        assert(env && "no TESTNAME defined!");

        testname = std::string(env);
        fd = std::ofstream (testname + ".perf.log");
        assert(fd.is_open() && "File cannot be opened!");
    }

    ~Log() {
        // close fd
        fd.close();
    }
public:
    void emit(LogEntry *entry) {
        // std::lock_guard<std::mutex> lock(mtx);
        buffer.push_back(entry);
        if (buffer.size() >= bufferSize) {
            flush();
        }
    }
    // called in ~LazydProfilingPerfLibrary, flush the last batch of logs and free memory 
    void lastFlush() {
        flush();
    }
private:
    void flush() {
        for (const LogEntry *log : buffer) {
            log->emit(fd);
        }
        // free current load of buffer
        for (auto *log : buffer) {
            delete log;
        }
        buffer.clear();
    }
private:
    std::ofstream fd;

    std::vector<LogEntry *> buffer;
    const size_t bufferSize = 1000;
};

/****************************
 * main log entry storage 
 ****************************/
struct LazydProfilingPerfLibrary {
    LazydProfilingPerfLibrary() {}
    ~LazydProfilingPerfLibrary() {
        LOG.lastFlush();
    }
public: 
    Log LOG;
};

LazydProfilingPerfLibrary library;

extern "C" {
__attribute__((used))
void lazydProfilingPerf (int vers, unsigned long tripcount, size_t granularity, int depth, 
                        const char *srcCallerName, 
                        const char *srcDiloc, const char *inlineDiloc) {
    auto *entry = new LogEntryIntrinsic(vers, tripcount, granularity, depth, srcCallerName, srcDiloc, inlineDiloc);
    library.LOG.emit(entry);
}

void lazydProfilingCall (const char *calleeLink, const char *callsiteLoc, const char *callerLink) {
    /// DEBUG: only emit Calledat log when it's at EF callsite
    auto *entry = new LogEntryCallsite(calleeLink, callsiteLoc, callerLink, delegate_work);
    library.LOG.emit(entry);

    // auto *entry = new LogEntryCallsite(calleeLink, callsiteLoc, callerLink, delegate_work);
    // library.LOG.emit(entry);
}
}
