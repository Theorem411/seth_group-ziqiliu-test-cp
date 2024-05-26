#include <cassert>
#include <set>
#include <map>
#include <unordered_map>
#include <vector>
#include <mutex>
#include <fstream>
#include <iostream>

struct LogEntry {
    LogEntry(int vers, unsigned long tripcount, size_t granularity, int depth, 
            const char *srcDiloc, const char *srcCallerName,
            const char *inlineDiloc, const char *inlineCallerName)
            : v(vers), tc(tripcount), g(granularity), d(depth), 
              loc(srcDiloc), call(srcCallerName),
              iloc(inlineDiloc), icall(inlineCallerName) {}

    void emit(std::ostream &os) const {
        os  << v << ","
            << tc << ","
            << g << ","
            << d << ","
            << loc << ","
            << call << ","
            << iloc << ","
            << icall << "\n";
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
    void emit(const LogEntry &entry) {
        // std::lock_guard<std::mutex> lock(mtx);
        buffer.push_back(entry);
        if (buffer.size() >= bufferSize) {
            flush();
        }
    }
    
private:
    void flush() {
        for (const auto &log : buffer) {
            log.emit(fd);
        }
        buffer.clear();
    }
private:
    std::ofstream fd;

    // std::mutex mtx;

    std::vector<LogEntry> buffer;
    const size_t bufferSize = 1000;
};

/****************************
 * main log entry storage 
 ****************************/
Log LOG;

extern "C" {
__attribute__((used))
void lazydProfilingPerf (int vers, unsigned long tripcount, size_t granularity, int depth, 
                        const char *srcDiloc, const char *srcCallerName,
                        const char *inlineDiloc, const char *inlineCallerName) {
    LogEntry entry{vers, tripcount, granularity, depth, srcDiloc, srcCallerName, inlineDiloc, inlineCallerName};
    LOG.emit(entry);
}
}