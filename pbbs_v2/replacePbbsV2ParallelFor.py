##########################################
# example run: 
# source /afs/ece/project/seth_group/ziqiliu/test-cp/venv/bin/activate
# python replacePbbsV2ParallelFor.py -T=delaunayTriangulation -A (-D)
# python replacePbbsV2ParallelFor.py -T=delaunayTriangulation -P -id=<id like: 2024-05-15.20:04:10> -ece=014
##########################################
from __future__ import print_function

import os, sys
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
# compileAnalysisAndInstrumentResults: test=<test> mode=0 ./prr.sh
#   compile static prr analysis and instrumentation results
###############################################################################
def compileAnalysisAndInstrumentResults(args, workdir=None, test=None, major_files=None, major_funcs=None):
    def print_call_history(func_name, cg, res_limit=10, indent=0):
        res = set()
        def traversal(f, callpath, res, visited, early_stop=False):
            if f not in cg or early_stop:
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
                ### DEBUG: ##
                early_stop = early_stop or ((caller_name in major_funcs) or (os.path.basename(file) in major_files))
                #############
                continued &= traversal(js_callsite['caller_mangled_name'], callpath, res, visited, early_stop=early_stop)
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

######################################################################
# interpretPerfTestResults: test=<test> mode=1 ./prr.sh
#   interpret performance test parlaytime and icache results
######################################################################
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


######################################################################
# interpretProfilingResults: test=<test> mode=2 ./prr.sh
#   interpret performance profiling results
######################################################################
class PerfLog:
    def __init__(self, args, workdir, test, major_files=None, major_funcs=None):
        self.args = args
        self.major_files = major_files
        self.major_funcs = major_funcs
        # primary key: host function linkage name
        # secondary key: version 
        # value: accumulative statistics of this intrinsic callsite
        perf_short_json_path = os.path.join(workdir, '{}.perf.short.json'.format(test))
        if not os.path.exists(perf_short_json_path):
            ###### preprocessing self.perfLogDict schema:
                # {
                #     'host': {
                #         0: { <iloc>: { 'entry': i, 'ef_entry': i, 'dac_entry': i, 'tripcount_sum': i, 'granularity_sum': i, 'depth_sum': i } }
                #         1: { ... }
                #         2: { ... }
                #         'origloc': { s }
                #         'ef_callers': {
                #             <ef_caller_name>: [ s ]
                #         }
                #         'dac_callers': {
                #             <dac_caller_name>: [ s ]
                #         }
                #     }
                # }
            def perfLogDict_prep_init():
                version_dict = { # secondary key is version
                    vs: defaultdict( # tertiary key is inline location
                        lambda: {  
                            'entry': 0,
                            'ef_entry': 0,
                            'dac_entry': 0,
                            'tripcount_sum': 0.0,
                            'granularity_sum': 0.0,
                            'depth_sum': 0.0
                        }
                    )
                    for vs in range(3)
                }
                result_dict = { # primary key is host linkname
                    'origloc': set(),
                    'ef_callers': defaultdict(lambda: set()), # key: caller linkname, val: inline location
                    'dac_callers': defaultdict(lambda: set()) # key: caller linkname, val: inline location
                }
                result_dict.update(version_dict)
                return result_dict
            self.perfLogDict_prep = defaultdict(perfLogDict_prep_init)
            
            # read large file .perf.log.gz
            with gzip.open(os.path.join(workdir, '{}.perf.log.gz'.format(test)), 'rt') as f:
                file_size = os.path.getsize(os.path.join(workdir, '{}.perf.log.gz'.format(test)))
                with tqdm(total=file_size, desc='Processing', unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                    for line in f: 
                        self.parseLogLine(line.strip()) # update self.perfLogDict_prep
                        pbar.update(len(line.encode('utf-8')))
                    print("<< done processing {}".format(os.path.join(workdir, '{}.perf.log.gz'.format(test))))

            ##### prepare for serialization
                # self.perfLogDict schema: 
                # {
                #     'host': {
                #         0: [ 
                #             { 
                #                 'iloc': s, 
                #                 (sort_key) 'entry': i, 
                #                 'ef_entry': i, 
                #                 'dac_entry': i, 
                #                 'tripcount_sum': i, 
                #                 'granularity_sum': i, 
                #                 'depth_sum': i 
                #             } 
                #         ]
                #         1: [ ... ]
                #         2: [ ... ]
                #         'origloc': [ s ]
                #         'ef_callers': {
                #             <ef_caller_name>: [ s ]
                #         }
                #         'dac_callers': {
                #             <dac_caller_name>: [ s ]
                #         }
                #     }
                # }
            def perfLogDict_init():
                version_dict = {  # primary key is host linkname
                    # secondary key is version # inline location is expanded into list
                    vs: [] for vs in range(3)
                }
                result_dict = {
                    'origloc': list(),
                    'ef_callers': defaultdict(lambda: list()), # key: caller linkname, val: inline location
                    'dac_callers': defaultdict(lambda: list()) # key: caller linkname, val: inline location
                }
                result_dict.update(version_dict)
                return result_dict

            self.perfLogDict = defaultdict(perfLogDict_init)
            for host, perfLogDict_prep_host in self.perfLogDict_prep.items(): 
                # serialize version 0 - 3
                for v in range(3): 
                    perfLogDict_prep_v = perfLogDict_prep_host[v]
                    for iloc, perfLogDict_prep_iloc in perfLogDict_prep_v.items():
                        perfLogDict_prep_iloc['inline_loc'] = iloc
                        self.perfLogDict[host][v].append(perfLogDict_prep_iloc)
                    self.perfLogDict[host][v].sort(key=lambda js: js['entry'])
                
                # serialize: 'origloc'
                self.perfLogDict[host]['origloc'] = list(perfLogDict_prep_host['origloc'])
                # serialize ef_callers: turn any set() into list()
                for caller, callsites_set in perfLogDict_prep_host['ef_callers'].items():
                    self.perfLogDict[host]['ef_callers'][caller] = list(callsites_set)
                for caller, callsites_set in perfLogDict_prep_host['dac_callers'].items():
                    self.perfLogDict[host]['dac_callers'][caller] = list(callsites_set)
            # save temporary file
            with open(perf_short_json_path, 'w') as f:
                json.dump(self.perfLogDict, f, indent=2)
                print(">> saved shortened perf.log file to {}".format(os.path.join(workdir, '{}.perf.short.json'.format(test))))

        with open(perf_short_json_path, 'r') as f: #.backup
            self.perfLogDict = json.load(f)
        # cg 
        with open(os.path.join(workdir, r'{}-perf.cg.json'.format(test)), 'r') as f:
            cg_json = json.load(f)
        self.cg = { js['func'] : js for js in cg_json}


    def parseLogLine(self, logtxt=None):
        # break apart log line
        line = logtxt.split(',')

        tag = line[0]
        if (tag == "calledat"):
            host = line[1]
            callsite = normpath(line[2])
            callername = line[3]
            depth = int(line[4])
            # update ef/dac caller information
            perfLogDict_host = self.perfLogDict_prep[host]
            if (depth == 0):
                perfLogDict_host['ef_callers'][callername].add(callsite)
            else:
                perfLogDict_host['dac_callers'][callername].add(callsite)

        elif (tag == "builtin"):
            version = int(line[1])
            tripcount = int(line[2])
            granularity = int(line[3])
            depth = int(line[4])
            host = line[5]
            orig_loc = line[6]
            inline_loc = line[7]
            # update perfLogDict -> host -> version -> { accumulative stats }
            perfLogDict_iloc = self.perfLogDict_prep[host][version][inline_loc]
            perfLogDict_iloc['tripcount_sum'] += tripcount
            perfLogDict_iloc['granularity_sum'] += granularity
            perfLogDict_iloc['depth_sum'] += depth
            perfLogDict_iloc['entry'] += 1
            if (depth == 0):
                perfLogDict_iloc['ef_entry'] += 1
            else:
                perfLogDict_iloc['dac_entry'] += 1
            # update perfLogDict -> host -> orig location
            self.perfLogDict_prep[host]['origloc'].add(orig_loc)

        else: 
            print("unknown tag \"{}\" seen in log line!".format(tag))
            exit(1)

    @staticmethod
    def pp_vers(version):
        if (version == '0'):
            return "parallel_for"
        elif version == '1':
            return "parallel_for_ef"
        elif version == '2': 
            return "parallel_for_dac"
        else:
            print('unknown version, cannot call pp_vers')
            exit(1)

    def unfold_call_history(self, func_name, res_limit=10, indent=0, target_caller=None):
        # print calling history of a callsite
        res = set()
        INDENT = '\t'*indent
        def traversal(f, callpath, res, visited, early_stop=False, found_tgt_func=False):
            if f not in self.cg or early_stop:
                # if found_tgt_func:
                res.add('\n'.join([ '{}{}'.format('\t'*indent, p) for p in callpath ]))
                return (len(res) < res_limit)
            ### DEBUG: ###
            if f in visited:
                return (len(res) < res_limit)
            ##############
            continued = True
            visited.add(f)
            js = self.cg[f]
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

                early_stop = early_stop or ((caller_name in self.major_funcs) or (os.path.basename(file) in self.major_files))
                continued &= traversal(js_callsite['caller_mangled_name'], callpath, res, visited, early_stop=early_stop, found_tgt_func=(link_name==target_caller))
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
            res_str += '\n\n{}<!> only {} callpaths is shown!'.format(INDENT, res_limit)
        return res_str
    
    def emit(self, indent=0, file=None):
        ##### printer
        # self.perfLogDict schema: 
        # {
        #     'host': {
        #         0: [ 
        #             { 
        #                 'iloc': s, 
        #                 (sort_key) 'entry': i, 
        #                 'ef_entry': i, 
        #                 'dac_entry': i, 
        #                 'tripcount_sum': i, 
        #                 'granularity_sum': i, 
        #                 'depth_sum': i 
        #             } 
        #         ]
        #         1: [ ... ]
        #         2: [ ... ]
        #         'origloc': [ s ]
        #         'ef_callers': {
        #             <ef_caller_name>: [ s ]
        #         }
        #         'dac_callers': {
        #             <dac_caller_name>: [ s ]
        #         }
        #     }
        # }
        if file is None: 
            file = sys.stdout
        INDENT = '\t' * indent
        # print self.perfLogDict as
        #   primary key: host func link name
        #       secondary key: version
        #           originally defined at: <orig locs>
        #           inlined at: <inline locs>
        #           < <host> : <vers_t> <entry> <ef entry> <dac entry> <avg.tc> <avg.gran> >
        #           if verbose: 
        #               <unfolded ef call path>
        #               <unfolded dac call path>

        for host, perfLog_host in self.perfLogDict.items():
            print('\n{}intrinsic found in: {}'.format(INDENT, host), file=file)
            for orig_loc in perfLog_host['origloc']:
                print('{}\torig defined at: {}'.format(INDENT, orig_loc), file=file)
            # print versioned intrinsics collective stats found in host func
            for v in range(3):
                ### DEBUG:
                # if v != 0: 
                #     continue
                ##########
                v = str(v)
                perfLog_v = perfLog_host[v]
                if (len(perfLog_v) > 0):
                    print('\n{}\t-- v:{}'.format(INDENT, v), file=file)
                for perfLog_iloc in perfLog_v:
                    iloc = perfLog_iloc['inline_loc']
                    entry = perfLog_iloc['entry']
                    ef_entry = perfLog_iloc['ef_entry']
                    dac_entry = perfLog_iloc['dac_entry']
                    avg_tc = perfLog_iloc['tripcount_sum'] / entry
                    avg_gr = perfLog_iloc['granularity_sum'] / entry

                    print('{}\t<{}> entry:{} ef:{} dac:{} avg.tc:{:.2f} avg.gr:{:.2f} inlined at: {}'.format(INDENT, PerfLog.pp_vers(v), entry, ef_entry, dac_entry, avg_tc, avg_gr, iloc), file=file)
            # verbose mode: print unfolded static call history
            if len(perfLog_host['ef_callers']):
                print('\n{}\tEF call paths:'.format(INDENT), file=file)
            for ef_caller, ef_callsites in perfLog_host['ef_callers'].items():
                print('{}\t\tef caller: {}'.format(INDENT, ef_caller), file=file)
                for ef_callsite in ef_callsites:
                    print('{}\t\t\tat: {}'.format(INDENT, ef_callsite), file=file)
                if self.args.v:
                    print('{}\t\tunfold caller\'s static callpaths:'.format(INDENT), file=file)
                    print(self.unfold_call_history(host, indent=indent+2, target_caller=ef_caller), file=file)
            if len(perfLog_host['dac_callers']):
                print('\n{}\tDAC call paths:'.format(INDENT), file=file)
            for dac_caller, dac_callsites in perfLog_host['dac_callers'].items():
                print('{}\t\tdac aller: {}'.format(INDENT, dac_caller), file=file)
                for dac_callsite in dac_callsites:
                    print('{}\t\t\tat: {}'.format(INDENT, dac_callsite), file=file)
                if self.args.v:
                    print('{}\t\tunfold caller\'s static callpaths:'.format(INDENT), file=file)
                    print(self.unfold_call_history(host, indent=indent+2, target_caller=dac_caller), file=file)

def interpretProfilingResults(args, workdir=None, test=None, major_files=None, major_funcs=None):
    perfLog = PerfLog(args, workdir, test, major_files=major_files, major_funcs=major_funcs)
    if args.v:
        with open(r'./{}.runtime.txt'.format(test), 'w') as f:
            perfLog.emit(file=f)
    else:
        perfLog.emit()

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
                test=args.test,
                major_files=['classify.C', 'classifyTime.C'],
                major_funcs=['classify'])
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

    