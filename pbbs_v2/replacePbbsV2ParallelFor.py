##########################################
# example run: 
# source /afs/ece/project/seth_group/ziqiliu/test-cp/venv/bin/activate
# python replacePbbsV2ParallelFor.py -T=delaunayTriangulation -A (-D)
# python replacePbbsV2ParallelFor.py -T=delaunayTriangulation -P -id=<id like: 2024-05-15.20:04:10> -ece=014
##########################################
from __future__ import print_function

import os 
import re
import json
import argparse
import gzip
import datetime
import pandas as pd
from tqdm import tqdm
from collections import defaultdict, Counter

# base directory for handy path specification
basedir = r'/afs/ece/project/seth_group/ziqiliu/test-cp/pbbs_v2'

###############################################################################
# helper function shared by all 
###############################################################################
# filepath normalize
def normpath(path):
    path = os.path.normpath(path)
    if path.startswith("delaunayTriangulation/bench/parlay"):
        # Replace the first occurrence of prefix_to_replace with new_prefix
        path = path.replace("delaunayTriangulation/bench/parlay", "delaunayTriangulation/incrementalDelaunay/parlay", 1)
    if path.startswith("delaunayTriangulation/bench/common"):
        # Replace the first occurrence of prefix_to_replace with new_prefix
        path = path.replace("delaunayTriangulation/bench/common", "delaunayTriangulation/incrementalDelaunay/common", 1)
    return path

def datetime_utcnow_strftime():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d_%H:%M:%S')

# convert json to hashable string
def jsonstr(json):
    return json.dumps(json, sort_keys=True)

###############################################################################
# main functionality 
###############################################################################
def compileAnalysisAndInstrumentResults(args, workdir=None, test=None):
    def print_call_history(func_name, cg, res_limit=10, indent=0):
        res = set()
        def traversal(f, callpath, res, visited):
            if f not in cg:
                res.add('\n'.join([ '{}{}'.format('\t'*indent, p) for p in callpath ]))
                return (len(res) < res_limit)
            if f in visited:
                return (len(res) < res_limit)
            continued = True
            visited.add(f)
            js = cg[f]
            for js_callsite in js['callsites']:
                file = normpath(js_callsite['file'])
                ln = js_callsite['ln']
                col = js_callsite['col']
                prr = js_callsite['prr']
                caller_name = js_callsite['caller_name']
                # push new path
                new_path = "{}  {}:{}:{}\tcaller: {}".format(prr, file, str(ln), str(col), caller_name)
                if args.v:
                    new_path += '\t{}'.format(js_callsite['caller_mangled_name'])
                callpath.append(new_path)
                continued &= traversal(js_callsite['caller_mangled_name'], callpath, res, visited)
                callpath.pop()
                if not continued: 
                    break
            
            # shrink current visit set
            visited.remove(f)
            return continued

        normal_exit = traversal(func_name, [], res, visited=set())

        return res, normal_exit

    # print calling history of a callsite
    with open(os.path.join(workdir, r'{}.cg.json'.format(test)), 'r') as f:
        cg_json = json.load(f)
        cg = { js['func'] : js for js in cg_json}
        if args.v: print('<< read from {}'.format(os.path.join(workdir, r'{}.cg.json'.format(test))))

    # static analysis result in json
    with open(os.path.join(workdir, r'{}.cilkfor.json'.format(test)), 'r') as f:
        static_analysis_json = json.load(f) 
        static_analysis = { js['ID'] : js for js in static_analysis_json }
        assert(len(static_analysis_json) == len(static_analysis))
        if args.v: print('<< read from {}'.format(os.path.join(workdir, r'{}.cilkfor.json'.format(test))))
        print("{} static cilkfor results".format(len(static_analysis)))
        print("\t{} ef results".format(len([ js for js in static_analysis_json if js['prr'] == 'defef' ])))
        print("\t{} dac results".format(len([ js for js in static_analysis_json if js['prr'] == 'defdac' ])))
        print("\t{} both results".format(len([ js for js in static_analysis_json if js['prr'] == 'both' ])))
        print("\t{} untouched results".format(len([ js for js in static_analysis_json if js['prr'] == 'untouched' ])))

    # instrumentation result in json 
    with open(os.path.join(workdir, r'{}.instr.json'.format(test)), 'r') as f:
        lazyd_instrument_json = json.load(f)
        lazyd_instrument = { js['ID'] : js for js in lazyd_instrument_json }
        assert(len(lazyd_instrument_json) == len(lazyd_instrument))
        if args.v: print('<< read from {}'.format(os.path.join(workdir, r'{}.instr.json'.format(test))))
        print("{} instrumentation cilkfor results".format(len(lazyd_instrument)))

    # check all instrument ID's are in analysis result 
    weird_ids = { id for id in lazyd_instrument if id not in static_analysis }
    if (len(weird_ids) > 0):
        print("There are {} weird instrument entries: ".format(len(weird_ids)))
        print('\n'.join([json.dumps(lazyd_instrument[id], indent=2) for id in weird_ids]))
        exit(1)
    
    # correctness: instrumentation's dac/def counts must coincide with static result's prr
    for id, jsInstr in lazyd_instrument.items():
        jsStatic = static_analysis[id]
        if jsStatic['prr'] == 'defef':
            assert(jsInstr['dac'] == 0)
        elif jsStatic['prr'] == 'defdac':
            assert(jsInstr['ef'] == 0)
        elif jsStatic['prr'] == 'both':
            if args.v:
                if jsInstr['ef'] == 0 and jsInstr['dac'] > 0: 
                    print("\toverconservative-dac: {}".format(id))
                    # print callpaths
                    for js_callsite in jsInstr['caller_DAC']:
                        file = normpath(js_callsite['file'])
                        ln = js_callsite['ln']
                        col = js_callsite['col']
                        caller_link_name = js_callsite['mangled_name']
                        print('\t\t{}:{}:{}\tcaller: {}\tmangled: {}'.format(file, ln, col, js_callsite['caller'], js_callsite['mangled_name']))

                        # print call history of this callsite
                        callhistory, normal_exit = print_call_history(caller_link_name, cg, indent=2)
                        for callpath in callhistory:
                            print("\t- [ ] --\n{}".format(callpath))
                        if not normal_exit:
                            print('\t<!> only show 10 callpaths due to space!')
                        print('\n')
                elif jsInstr['dac'] == 0 and jsInstr['ef'] > 0:
                    print("\toverconservative-ef: {}".format(id))
        
                    # print callpaths
                    for js_callsite in jsInstr['caller_EF']:
                        file = normpath(js_callsite['file'])
                        ln = js_callsite['ln']
                        col = js_callsite['col']
                        caller_link_name = js_callsite['mangled_name']
                        print('\t\t{}:{}:{} \tcaller: {}\tmangled: {}'.format(file, ln, col, js_callsite['caller'], js_callsite['mangled_name']))
                        # print call history of this callsite
                        callhistory, normal_exit = print_call_history(caller_link_name, cg, indent=2)
                        for callpath in callhistory:
                            print("\t- [ ] --\n{}".format(callpath))
                        if not normal_exit:
                            print('\t<!> only show 10 callpaths due to space!')
                        print('\n')
                elif jsInstr['ef'] > 0 and jsInstr['dac'] > 0: 
                    print("\taccurate both: {}".format(id))

                    # print EF callpaths
                    for js_callsite in jsInstr['caller_EF']:
                        file = normpath(js_callsite['file'])
                        ln = js_callsite['ln']
                        col = js_callsite['col']
                        caller_link_name = js_callsite['mangled_name']
                        print('\t\t{}:{}:{} ef \tcaller: {}\tmangled: {}'.format(file, ln, col, js_callsite['caller'], js_callsite['mangled_name']))
                        # print call history of this callsite
                        callhistory, normal_exit = print_call_history(caller_link_name, cg, indent=2)
                        for callpath in callhistory:
                            print("\t- [ ] --\n{}".format(callpath))
                        if not normal_exit:
                            print('\t<!> only show 10 callpaths due to space!')
                        print('\n')
                    # print DAC callpaths
                    for js_callsite in jsInstr['caller_DAC']:
                        file = normpath(js_callsite['file'])
                        ln = js_callsite['ln']
                        col = js_callsite['col']
                        caller_link_name = js_callsite['mangled_name']
                        print('\t\t{}:{}:{} dac \tcaller: {}\tmangled: {}'.format(file, ln, col, js_callsite['caller'], js_callsite['mangled_name']))

                        # print call history of this callsite
                        callhistory, normal_exit = print_call_history(caller_link_name, cg, indent=2)
                        for callpath in callhistory:
                            print("\t- [ ] --\n{}".format(callpath))
                        if not normal_exit:
                            print('\t<!> only show 10 callpaths due to space!')
                        print('\n')

    # output combined result
    combined_json_list = []
    for id, jsInstr in lazyd_instrument.items():
        jsStatic = static_analysis[id]
        jsInstr['prr'] = jsStatic['prr']
        combined_json_list.append(jsInstr)


    print("\t{} ef cilkfors".format(len([ js for js in combined_json_list if js['prr'] == "defef" ])))
    print("\t{} dac cilkfors".format(len([ js for js in combined_json_list if js['prr'] == "defdac" ])))
    print("\t{} both cilkfors".format(len([ js for js in combined_json_list if js['prr'] == "both" ])))
    print("\t{} untouched cilkfors".format(len([ js for js in combined_json_list if js['prr'] == "untouched" ])))

    # print worklist of pfors that need to be changed manually 
    with open(os.path.join(workdir, r'{}.instr.cilkfor.json'.format(test)), 'w') as f:
        f.write(json.dumps(combined_json_list, indent=4))
        print('>> write to {}'.format(os.path.join(workdir, r'{}.instr.cilkfor.json'.format(test))))
    with open(os.path.join(workdir, '{}.worklist.txt'.format(test)), 'w') as f: 
        print("worklist: ", file=f)
        for js in combined_json_list:
            if js['prr'] == "both" or js['prr'] == 'untouched':
                continue
            print("\n- [ ] ======================================", file=f)
            print("\t{}".format(js['ID']), file=f)
            if (js['prr'] == 'defef'):
                for js_callsite in js['caller_EF']:
                    file = normpath(js_callsite['file'])
                    ln = js_callsite['ln']
                    col = js_callsite['col']
                    caller_link_name = js_callsite['mangled_name']
                    print('\tef\t{}:{}:{}\tcaller: {}'.format(file, ln, col, js_callsite['caller']), file=f)

                    # print call history of this callsite
                    callhistory, normal_exit = print_call_history(caller_link_name, cg, indent=2)
                    for callpath in callhistory:
                        print("\n\t- [ ] --\n{}".format(callpath), file=f)
                    if not normal_exit:
                        print('\t<!> only show 10 callpaths due to space!')
                    # collect file mentioned
            elif (js['prr'] == 'defdac'):
                dbg = js['ID'] == '_ZN6parlay12parallel_forIZNS_8sequenceIcNS_9allocatorIcEELb1EE16initialize_rangeIPKcEEvT_S8_St26random_access_iterator_tagEUlmE_EEvmmS8_lb'
                for js_callsite in js['caller_DAC']:
                    file = normpath(js_callsite['file'])
                    ln = js_callsite['ln']
                    col = js_callsite['col']
                    caller_link_name = js_callsite['mangled_name']
                    print('\tdac\t{}:{}:{}\tcaller: {}\t{}'.format(file, ln, col, js_callsite['caller'], caller_link_name), file=f)
                    # print call history of this callsite
                    callhistory, normal_exit = print_call_history(caller_link_name, cg, indent=2) ## DEBUG: 
                    for callpath in callhistory:
                        print("\n\t- [ ] --\n{}".format(callpath), file=f)
                    if not normal_exit:
                        print('\t<!> only show 10 callpaths due to space!')
                    # collect file mentioned
        print('>> write to {}'.format(os.path.join(workdir, '{}.worklist.txt'.format(test))))
    return

def interpretPerfTestResults(args, test=None, res_dir=None, id=None):
    # read entire log as chunks split by double newline
    def parse_parlaytime_log(log_text): 
        run_texts = log_text.split("\n\n")
            # don't process any empty lines before EOF
        if (not run_texts[-1].strip()):
            run_texts.pop()
        # init dataframe
        df = pd.DataFrame(columns=['cilk_workers', 'avg_parlaytime'])

        # split into chunks begining with '== CILK_WORKERS = <d+> ==...'
        r = None
        run_texts = [ t.split('\n') for t in run_texts ]
        for lines in run_texts: 
            # find line starting with "== CILK_WORKERS = "
            i = 0
            while i < len(lines):
                if lines[i].startswith('== CILK_WORKERS = '): break
                i += 1
            if i == len(lines):
                continue
            assert(lines[i].startswith('='))
            # find CILK_WORKDERS 
            CILK_WORKERS = int(re.findall(r'\d+', lines[i])[0])
            # take only "Parlay time: <d+.d+>"
            lines[:] = [ ln for ln in lines if ln.startswith('Parlay time: ') ]
            times = [ float(re.findall(r'\d+.\d+', ln)[0]) for ln in lines ]

            avg_times = pd.Series(times).mean()
            std_times = pd.Series(times).std()

            if r: 
                assert(r == len(times))
            r = len(times)
            # new row of data
            new_row = pd.Series({ 'cilk_workers': CILK_WORKERS, 'avg_parlaytime': avg_times, 'std_parlaytime': std_times })
            df = df.append(new_row, ignore_index=True)
        return df, r

    def parse_icache_txt(icache_text):
        sections = [sec.strip() for sec in icache_text.split('== ') if sec.strip() ]

        cilk_workers_pattern = re.compile(r'CILK_WORKERS\s*=\s*(\d+)')
        icache_misses_pattern = re.compile(r'([\d,]+)\s+icache\.misses:u')
        icache_hits_pattern = re.compile(r'([\d,]+)\s+icache\.hit:u')

        df = pd.DataFrame(columns=['cilk_workers', 'i$_miss', 'i$_hit', 'i$_miss_rate'])

        for section in sections: 
            cilk_workers = int(cilk_workers_pattern.search(section).group(1))
            icache_misses = int(icache_misses_pattern.search(section).group(1).replace(',',''))
            icache_hits = int(icache_hits_pattern.search(section).group(1).replace(',', ''))
            new_row = pd.Series({
                'cilk_workers': cilk_workers, 
                'i$_miss': icache_misses, 
                'i$_hit': icache_hits, 
                'i$_miss_rate': icache_misses / float(icache_misses + icache_hits)
            })
            df = df.append(new_row, ignore_index=True)
        return df

    # parse control group parlaytime & icache result
    orig_time_path = os.path.join(basedir, r'data/{}/{}.parlaytime.orig.log'.format(test, id))
    with open(orig_time_path, 'r') as f: 
        print('<< processed {}'.format(r'data/{}/{}.parlaytime.orig.log'.format(test, id)))
        df_orig, r_orig = parse_parlaytime_log(f.read())
        df_orig.rename(columns={'avg_parlaytime': 'avg_parlaytime_orig', 'std_parlaytime': 'std_parlaytime_orig'}, inplace=True)
    
    orig_icache_path = os.path.join(basedir, r'data/{}/{}.icache.orig.txt'.format(test, id))
    with open(orig_icache_path, 'r') as f:
        print('<< processed {}'.format(r'data/{}/{}.icache.orig.txt'.format(test, id)))
        icache_orig = parse_icache_txt(f.read())
        icache_orig.rename(columns={'i$_miss': 'i$_miss_orig', 'i$_hit': 'i$_hit_orig', 'i$_miss_rate': 'i$_miss_rate_orig'}, inplace=True)
    # parse test group parlaytime & icache result
    test_time_path = os.path.join(basedir, r'data/{}/{}.parlaytime.test.log'.format(test, id))
    with open(test_time_path, 'r') as f:
        print('<< processed {}'.format(r'data/{}/{}.parlaytime.test.log'.format(test, id)))
        df_test, r_test = parse_parlaytime_log(f.read())
        df_test.rename(columns={'avg_parlaytime': 'avg_parlaytime_test', 'std_parlaytime': 'std_parlaytime_test'}, inplace=True)
    
    test_icache_path = os.path.join(basedir, r'data/{}/{}.icache.test.txt'.format(test, id))
    with open(test_icache_path, 'r') as f:
        print('<< processed {}'.format(r'data/{}/{}.icache.test.log'.format(test, id)))
        icache_test = parse_icache_txt(f.read())
        icache_test.rename(columns={'i$_miss': 'i$_miss_test', 'i$_hit': 'i$_hit_test', 'i$_miss_rate': 'i$_miss_rate_test'}, inplace=True)
    
    assert(r_orig == r_test)

    # merge compiled control & test group parlaytime results
    df_merge = df_orig.merge(df_test, on='cilk_workers')
    icache_merge = icache_orig.merge(icache_test, on='cilk_workers')
    # output .perf.csv
    ece_id = int(args.ece)
    parlaytime_out_path = os.path.join(basedir, r'perf/{}/{}.ece{}.r{}.parlay.csv'.format(test, id, ece_id, r_orig))
    print("write performance test results to --> {}".format(parlaytime_out_path))
    df_merge.to_csv(parlaytime_out_path, index=False)

    # output .icache.csv
    icache_out_path = os.path.join(basedir, r'perf/{}/{}.ece{}.r{}.icache.csv'.format(test, id, ece_id, r_orig))
    print("write icache results to --> {}".format(icache_out_path))
    icache_merge.to_csv(icache_out_path, index=False)

def interpretProfilingResults(args, workdir=None, test=None, major_files=None, major_funcs=None):
    with open(os.path.join(workdir, r'{}-perf.cg.json'.format(test)), 'r') as f:
        cg_json = json.load(f)
    cg = { js['func'] : js for js in cg_json}

    # print calling history of a callsite
    def unfold_call_history(func_name, res_limit=10, indent=0):
        res = set()
        def traversal(f, callpath, res, visited, early_stop=False):
            if f not in cg or early_stop:
                res.add('\n'.join([ '{}{}'.format('\t'*indent, p) for p in callpath ]))
                return (len(res) < res_limit)
            ### DEBUG: ###
            if f in visited:
                return (len(res) < res_limit)
            ##############
            continued = True
            visited.add(f)
            js = cg[f]
            for js_callsite in js['callsites']:
                # push new path
                file = normpath(js_callsite['file'])
                ln = js_callsite['ln']
                col = js_callsite['col']
                prr = js_callsite['prr']
                caller_name = js_callsite['caller_name']
                link_name = js_callsite['caller_mangled_name']
                new_path = "-----> {}:{}:{}\tcaller: {}\t{}".format(file, str(ln), str(col), caller_name, link_name)
                callpath.append(new_path)

                early_stop = early_stop or ((caller_name in major_funcs) or (os.path.basename(file) in major_files))
                continued &= traversal(js_callsite['caller_mangled_name'], callpath, res, visited, early_stop=early_stop)
                # backtrack: pop off all callpath added in this iteration
                callpath.pop()
                # if reaches result limit, early break
                if not continued:
                    break

            # shrink visited set 
            visited.remove(f)
            return continued
            
        normal_exit = traversal(func_name, [], res, visited=set())

        res_str = '\n\n'.join(res)
        if not normal_exit:
            res_str += '\n\n{}<!> only {} callpaths is shown!'.format('\t'*indent, res_limit)
        return res_str
    
    def parallel_for_version(version):
        if (version == 0):
            return "parallel_for"
        elif version == 1:
            return "parallel_for_ef"
        elif version == 2: 
            return "parallel_for_dac"
        else:
            exit(1)

    def parse_perf_log(line, perfLogsDict=None):
        # break apart log line
        line = line.split(',')

        version = int(line[0])
        tripcount = int(line[1])
        granularity = int(line[2])
        depth = int(line[3])
        src_loc = line[4]
        src_caller = line[5]
        inline_loc = line[6]
        inline_caller = line[7]
        # check version 
        perfLogsDict_vers = perfLogsDict[version]
        if src_caller not in perfLogsDict_vers:
            perfLogsDict_vers[src_caller] = {
                'src_caller': src_caller,
                'src_locs': set(),
                'inline_locs': set(),
                'inline_callers': set(),
                'version': version,
                'entry': 0,
                'ef_entry': 0,
                'dac_entry': 0,
                'tripcount_sum': 0.0,
                'granularity_sum': 0.0,
                'depth_sum': 0.0
            }
        # add caller (mangled) name
        perfLogsDict_vers[src_caller]['inline_locs'].add(inline_loc)
        perfLogsDict_vers[src_caller]['src_locs'].add(src_loc)
        perfLogsDict_vers[src_caller]['inline_callers'].add(inline_caller)
        # update runtime argument distribution
        perfLogsDict_vers[src_caller]['tripcount_sum'] += tripcount
        perfLogsDict_vers[src_caller]['granularity_sum'] += granularity
        perfLogsDict_vers[src_caller]['depth_sum'] += depth
        # incr entry count
        perfLogsDict_vers[src_caller]['entry'] += 1 
        if (depth > 0):
            perfLogsDict_vers[src_caller]['dac_entry'] += 1
        else: 
            perfLogsDict_vers[src_caller]['ef_entry'] += 1
        
        return 

    try:
        with open(os.path.join(workdir, '{}.perf.short.json'.format(test)), 'r') as f: #.backup
            perfLogs_sorted = json.load(f)
    except:
        file_size = os.path.getsize(os.path.join(workdir, '{}.perf.log.gz'.format(test)))

        perfLogsDict = {0: {}, 1: {}, 2: {}}
        with gzip.open(os.path.join(workdir, '{}.perf.log.gz'.format(test)), 'rt') as f:
            with tqdm(total=file_size, desc='Processing', unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                for line in f: 
                    parse_perf_log(line.strip(), perfLogsDict)
                    pbar.update(len(line.encode('utf-8')))

        perfLogs = []
        for _, perfLogs_vers in perfLogsDict.items(): 
            for log in perfLogs_vers.values():
                log['inline_locs'] = list(log['inline_locs'])
                log['inline_callers'] = list(log['inline_callers'])
                log['src_locs'] = list(log['src_locs'])
                perfLogs.append(log)
        perfLogs_sorted = sorted(perfLogs, key=lambda js:js['entry'])

        # save temporary file
        with open(os.path.join(workdir, '{}.perf.short.json'.format(test)), 'w') as f:
            json.dump(perfLogs_sorted, f, indent=2)

    perfLogs_EF = [ logs for logs in perfLogs_sorted if logs['version'] == 1 ]
    perfLogs_DAC = [ logs for logs in perfLogs_sorted if logs['version'] == 2 ]
    perfLogs_orig = [ logs for logs in perfLogs_sorted if logs['version'] == 0 ]
    def print_perfLogs(perfLogs=None, indent=0):
        for logs in perfLogs:
            caller = logs['src_caller']
            entry = logs['entry']
            avg_tc = "{:.2f}".format(logs['tripcount_sum'] / entry)
            avg_gran = "{:.2f}".format(logs['granularity_sum'] / entry)
            print("{}<{}> entry:{} ef:{} dac:{} avg.tc:{} avg.gran:{}\tcaller: {}".format('\t'*indent, parallel_for_version(logs['version']), logs['entry'], logs['ef_entry'], logs['dac_entry'], avg_tc, avg_gran, caller))
            for sloc in logs['src_locs']:
                print('{}\tsource code at: {}'.format('\t'*indent, sloc))

            for iloc in logs['inline_locs']: 
                print('{}\tinlined at: {}'.format('\t'*indent, iloc))
                if args.v: 
                    if (os.path.basename(iloc.split(':')[0]) not in major_files):
                        print('{}\tinline caller: {}'.format('\t'*indent, caller))
                        print("{}".format(unfold_call_history(caller, indent=2)))
                print('\n')

    # print performance profiling results for parallel_for
    print('-- orig: ')
    print_perfLogs(perfLogs=perfLogs_orig, indent=1)
    # print performance profiling results for parallel_for_ef or parallel_for_dac
    print('-- ef: ')
    print_perfLogs(perfLogs=perfLogs_EF, indent=1)
    print('-- dac: ')
    print_perfLogs(perfLogs=perfLogs_DAC, indent=1)

if __name__ == "__main__":
    # take current timestamp
    dt = datetime_utcnow_strftime()
    # main runner argument parser
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-v", "--verbose", dest='v', help='', action="store_true")
    argParser.add_argument("-T", "--test", dest='test', help='')
    # prr static analysis result parsing
    argParser.add_argument('-A', '--analysis-and-instrument', dest='analysis', help='parse prr static analysis result and generate parallel_for substitution worklist', action='store_true')
    # parlaytime result parsing
    argParser.add_argument('-PARLAY', '--parlaytime-statistic', dest='parlaytime', help='', action='store_true') 
    argParser.add_argument('-id', dest='experiment_id', default=None, help='experiment timestamp for result identification')
    argParser.add_argument('-ece', dest='ece', default=None, help='ece cluster machine number')
    # performance profiling result parsing
    argParser.add_argument('-PROFILE', '--perf-profiling', dest='profile', help='', action='store_true')
    args = argParser.parse_args()
    # os.walk parameters
    exclude_dirs = ['venv']

    #### parse instrumentation result
    def parlaytime_result_dir(testname=None):
        return os.path.join(basedir, 'data/{}'.format(testname))

    if args.parlaytime:
        if not args.experiment_id: 
            print("Must supply experiment id (printed at the end of performance experiment)!")
            exit(1)
        if not args.ece: 
            print("Must supply ece cluster machine id!")
            exit(1)

    if (args.test == "delaunayTriangulation"):
        if args.analysis:
            compileAnalysisAndInstrumentResults(
                args, 
                workdir=os.path.join(basedir, r'delaunayTriangulation-cp/incrementalDelaunay'),
                test=args.test)
        if args.parlaytime: 
            interpretPerfTestResults(
                args,
                test=args.test,
                res_dir=parlaytime_result_dir('delaunayTriangulation'), 
                id=args.experiment_id)
        if args.profile:
            interpretProfilingResults(
                args,
                workdir=os.path.join(basedir, r'delaunayTriangulation-test/incrementalDelaunay'),
                test=args.test,
                major_files=['delaunay.C', 'delaunayTime.C'],
                major_funcs=['delaunay'])
            

    elif (args.test == "wordCounts"):
        if args.analysis:
            compileAnalysisAndInstrumentResults(
                args, 
                workdir=os.path.join(basedir, r'wordCounts-cp/histogram'), 
                test=args.test)
        if args.parlaytime: 
            interpretPerfTestResults(
                args, 
                test=args.test,
                res_dir=parlaytime_result_dir('wordCounts'), 
                id=args.experiment_id)
        if args.profile:
            interpretProfilingResults(
                args,
                workdir=os.path.join(basedir, r'wordCounts-test/histogram'),
                test=args.test,
                major_files=['wc.C', 'wcTime.C'],
                major_funcs=['wordCounts', 'timeWordCounts'])
 
    elif (args.test == "classify"):
        if args.analysis:
            compileAnalysisAndInstrumentResults(
                args,
                workdir=os.path.join(basedir, r'classify-cp/decisionTree'),
                test=args.test)
        if args.parlaytime: 
            interpretPerfTestResults(
                args, 
                test=args.test,
                res_dir=parlaytime_result_dir('classify'), 
                id=args.experiment_id)
        if args.profile:
            interpretProfilingResults(
                args,
                workdir=os.path.join(basedir, r'classify-test/decisionTree'),
                test=args.test,
                major_files=['classify.C', 'classifyTime.C'],
                major_funcs=['classify'])
    else:
        print('Error: wrong test name!')
        exit(1)

    