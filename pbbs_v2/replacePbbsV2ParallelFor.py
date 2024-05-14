from __future__ import print_function

import os 
import re
import json
import argparse
import zipfile
import pandas as pd
from collections import defaultdict

PARALLELFOR_SOURCE_LOC = "opencilk.h:517:5"
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

# convert json to hashable string
def jsonstr(json):
    return json.dumps(json, sort_keys=True)

def compileAnalysisAndInstrumentResults(args, workdir=None, test=None):
    def print_call_history(func_name, cg, indent=0):
        res = set()
        def traversal(f, callpath, res, visited):
            if f not in cg:
                res.add('\n'.join([ '{}{}'.format('\t'*indent, p) for p in callpath ]))
                return
            ### DEBUG: ###
            if args.debug:
                if f in visited:
                    return
            ##############

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

                traversal(js_callsite['caller_mangled_name'], callpath, res, visited)
                callpath.pop()
        traversal(func_name, [], res, visited=set())

        return res

    # print calling history of a callsite
    with open(os.path.join(workdir, r'{}.cg.json'.format(test)), 'r') as f:
        cg_json = json.load(f)
        cg = { js['func'] : js for js in cg_json}

    # static analysis result in json
    with open(os.path.join(workdir, r'{}.cilkfor.json'.format(test)), 'r') as f:
        static_analysis_json = json.load(f) 
        static_analysis = { js['ID'] : js for js in static_analysis_json }
        assert(len(static_analysis_json) == len(static_analysis))

        print("{} static cilkfor results".format(len(static_analysis)))
        print("\t{} ef results".format(len([ js for js in static_analysis_json if js['prr'] == 'defef'])))
        print("\t{} dac results".format(len([ js for js in static_analysis_json if js['prr'] == 'defdac'])))
        print("\t{} both results".format(len([ js for js in static_analysis_json if js['prr'] == 'both'])))
        print("\t{} untouched results".format(len([ js for js in static_analysis_json if js['prr'] == 'untouched'])))

    # instrumentation result in json 
    with open(os.path.join(workdir, r'{}.instr.json'.format(test)), 'r') as f:
        lazyd_instrument_json = json.load(f)
        lazyd_instrument = { js['ID'] : js for js in lazyd_instrument_json }
        assert(len(lazyd_instrument_json) == len(lazyd_instrument))

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
                        callhistory = print_call_history(caller_link_name, cg, indent=2)
                        for callpath in callhistory:
                            print("\n- [ ] --\n{}".format(callpath))
                        print('\n')
                elif jsInstr['dac'] == 0 and jsInstr['ef'] > 0:
                    print("\toverconservative-ef: {}".format(id))
        
                    # print callpaths
                    for js_callsite in jsInstr['caller_EF']:
                        file = normpath(js_callsite['file'])
                        ln = js_callsite['ln']
                        col = js_callsite['col']
                        caller_link_name = js_callsite['mangled_name']
                        print('\t\t{}:{}:{}\tcaller: {}\tmangled: {}'.format(file, ln, col, js_callsite['caller'], js_callsite['mangled_name']))
                        # print call history of this callsite
                        callhistory = print_call_history(caller_link_name, cg, indent=2)
                        for callpath in callhistory:
                            print("\n- [ ] --\n{}".format(callpath))
                        print('\n')
    # output combined result
    combined_json_list = []
    for id, jsInstr in lazyd_instrument.items():
        jsStatic = static_analysis[id]
        jsInstr['prr'] = jsStatic['prr']
        combined_json_list.append(jsInstr)

    with open(os.path.join(workdir, r'{}.instr.cilkfor.json'.format(test)), 'w') as f:
        f.write(json.dumps(combined_json_list, indent=4))

    print("\t{} ef cilkfors".format(len([ js for js in combined_json_list if js['prr'] == "defef" ])))
    print("\t{} dac cilkfors".format(len([ js for js in combined_json_list if js['prr'] == "defdac" ])))
    print("\t{} both cilkfors".format(len([ js for js in combined_json_list if js['prr'] == "both" ])))
    print("\t{} untouched cilkfors".format(len([ js for js in combined_json_list if js['prr'] == "untouched" ])))

    # print worklist of pfors that need to be changed manually 
    with open(os.path.join(workdir, '{}.worklist.txt'.format(test)), 'w') as f: 
        print("worklist: ", file=f)
        for js in combined_json_list:
            if js['prr'] == "both":
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
                    callhistory = print_call_history(caller_link_name, cg, indent=2)
                    for callpath in callhistory:
                        print("\n\t- [ ] --\n{}".format(callpath), file=f)
                    # collect file mentioned
            elif (js['prr'] == 'defdac'):
                for js_callsite in js['caller_DAC']:
                    file = normpath(js_callsite['file'])
                    ln = js_callsite['ln']
                    col = js_callsite['col']
                    caller_link_name = js_callsite['mangled_name']
                    print('\tdac\t{}:{}:{}\tcaller: {}'.format(file, ln, col, js_callsite['caller']), file=f)
                    # print call history of this callsite
                    callhistory = print_call_history(caller_link_name, cg, indent=2)
                    for callpath in callhistory:
                        print("\n\t- [ ] --\n{}".format(callpath), file=f)
                    # collect file mentioned
    return

def interpretPerfTestResults(args, test=None, orig_time=None, test_time=None):
    def parse_parlaytime_log(log_text): 
        # read entire log as chunks split by double newline
        run_texts = log_text.split("\n\n")
            # don't process any empty lines before EOF
        if (not run_texts[-1].strip()):
            run_texts.pop()
        # init dataframe
        df = pd.DataFrame(columns=['cilk_workers', 'avg_parlaytime'])

        # split into chunks begining with '== CILK_WORKERS = <d+> ==...'
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

            # new row of data
            new_row = pd.Series({ 'cilk_workers': CILK_WORKERS, 'avg_parlaytime': avg_times })
            df = df.append(new_row, ignore_index=True)
        return df

    with open(orig_time, 'r') as f: 
        df_orig = parse_parlaytime_log(f.read())
        df_orig.rename(columns={'avg_parlaytime': 'avg_parlaytime_orig'}, inplace=True)
    with open(test_time, 'r') as f:
        df_test = parse_parlaytime_log(f.read())
        df_test.rename(columns={'avg_parlaytime': 'avg_parlaytime_test'}, inplace=True)

    df_merge = df_orig.merge(df_test, on='cilk_workers')
    print("write performance test results to --> ./{}.perf.csv".format(test))
    df_merge.to_csv(r'./{}.perf.csv'.format(test), index=False)

if __name__ == "__main__":
    exclude_dirs = ['venv']
    # replace_parallel_for(exclude_dirs=exclude_dirs)
    
    # main runner argument parser
    argParser = argparse.ArgumentParser()
    argParser.add_argument("--redo-ast", dest="redo", help='regenerate fresh .ast.json using clang ast-dump', action="store_true")
    argParser.add_argument("-v", "--verbose", dest='v', help='', action="store_true")
    argParser.add_argument("-T", "--test", dest='test', help='')
    argParser.add_argument('-A', '--analysis-and-instrument', dest='analysis', help='', action='store_true')
    argParser.add_argument('-P', '--parlaytime-statistic', dest='parlaytime', help='', action='store_true') 
    argParser.add_argument('-D', '--debug', dest='debug', help='', action='store_true')
    args = argParser.parse_args()
    #### parse instrumentation result
    # delaunay
    basedir = r'/afs/ece/project/seth_group/ziqiliu/test-cp/pbbs_v2'
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
                orig_time=os.path.join(basedir, r'delaunayTriangulation-cp/incrementalDelaunay/delaunayTriangulation.parlaytime.orig.log'),
                test_time=os.path.join(basedir, r'delaunayTriangulation-test/incrementalDelaunay/delaunayTriangulation.parlaytime.test.log'))

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
                orig_time=os.path.join(basedir, r'wordCounts-cp/histogram/wordCounts.parlaytime.orig.log'),
                test_time=os.path.join(basedir, r'wordCounts-test/histogram/wordCounts.parlaytime.test.log'))

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
                orig_time=os.path.join(basedir, r'classify-cp/decisionTree/classify.parlaytime.orig.log'),
                test_time=os.path.join(basedir, r'classify-test/decisionTree/classify.parlaytime.test.log'))
    else:
        print('Error: wrong test name!')
        exit(1)












# def parse_ast_json_experiment(args):
#     ############################################################################
#     # This function parses source code ast generated using "clang -Xclang -ast-dump"
#     # and performs source code keyword substitution
#     ############################################################################

#     # targeted kinds
#     target_kinds = {
#         'FunctionDecl', 'FunctionTemplateDecl', 'ClassTemplateDecl', 'CXXRecordDecl',
#         'LambdaExpr', 'CXXMethodDecl'
#     }
#     # ast-traversal logic
#     def ast_traversal_recursive(js, default_file, kinds=set(), files=set(), jsacc=[], file_name=None):
#         file_name_old = file_name
#         if isinstance(js, dict):
#             # use new "file" for subtree if "loc" has "file"
#             if js.get('loc') and js.get('loc').get('file'):
#                 file_name = normpath(js.get('loc').get('file'))
#                 if file_name.startswith('delaunayTriangulation/'): 
#                     files.add(file_name)
#             ### DEBUG: 
#             # if js.get('name') == "parallel_for_static":
#             #     js.pop('inner', None)
#             #     js['orig_file'] = file_name if file_name != None else "null"
#             #     print(json.dumps(js, indent=4))
#             #########
            
#             if js.get('kind'):
#                 kinds.add(js.get('kind'))
#                 if js.get('loc') and js.get('range') and js.get('name') \
#                         and (js.get('kind') in target_kinds):
#                     js_record = dict()
#                     js_record['kind'] = js.get('kind')
#                     # js_record['file'] = file_name
#                     if not file_name:
#                         js_record['file'] = default_file
#                     else: 
#                         js_record['file'] = file_name
#                     js_record['range'] = js.get('range')
#                     js_record['name'] = js.get('name')
#                     js_record['loc'] = js.get('loc')
  
#                     if js.get('mangled_name'):
#                         js_record['mangled_name'] = js.get('mangled_name')
                    
#                     jsacc.append(js_record)

#             for _, jsv in js.items():
#                 if isinstance(jsv, (dict, list)):
#                     ast_traversal_recursive(jsv, default_file, kinds=kinds, files=files, jsacc=jsacc, file_name=file_name)
        
#         elif isinstance(js, list):
#             for js_item in js:
#                 ast_traversal_recursive(js_item, default_file, kinds=kinds, files=files, jsacc=jsacc, file_name=file_name)

#     def ast_traversal(default_file, json_path=None):
#         with open(json_path, 'r') as f: 
#             ast_json = json.load(f)

#         kinds, files, jsacc = set(), set(), []
#         ast_traversal_recursive(ast_json, default_file, kinds=kinds, files=files, jsacc=jsacc)

#         print("{} done".format(json_path))
#         return kinds, files, jsacc

#     if args.redo:
#         delaunay_kinds, delaunay_files, delaunay_jsacc = \
#             ast_traversal(default_file=r'delaunayTriangulation/incrementalDelaunay/delaunay.C', json_path=r'./delaunay.ast.json')
#         delaunayTime_kinds, delaunayTime_files, delaunayTime_jsacc = \
#             ast_traversal(default_file=r'delaunayTriangulation/bench/delaunayTime.C',json_path=r'./delaunayTime.ast.json')
#         # print out the kind's encountered in ast nodes
#         kinds = [ kd for kd in delaunay_kinds.union(delaunayTime_kinds) if "Decl" in kd ]
#         # print files encountered during ast traversal, compare with those in results
    
#         # collect json objects depending on target types
#         delaunay_jsacc_str = set([ json.dumps(js, sort_keys=True) for js in delaunay_jsacc ])
#         delaunayTime_jsacc_str = set([ json.dumps(js, sort_keys=True) for js in delaunayTime_jsacc ])

#         js_of_all_kinds = { kd : [] for kd in target_kinds }
#         for js_string in delaunay_jsacc_str.union(delaunayTime_jsacc_str): 
#             js = json.loads(js_string)
#             js_of_all_kinds[js['kind']].append(js)

#         with open(r'./delaunayTriangulation.short.ast.json', 'w') as f:
#             f.write(json.dumps(js_of_all_kinds, indent=4))
   
#         if args.error:
#             print('kinds: {}'.format(len(kinds)))
#             print('\n'.join(kinds))
#             files_in_ast_traversal = list(delaunayTime_files.union(delaunay_files))
#             print('files during ast traversal: {}'.format(len(files_in_ast_traversal)))
#             print('\n'.join(sorted(files_in_ast_traversal)))

#     # open shortened ast result:
#     with open(r'./delaunayTriangulation.short.ast.json', 'r') as f:
#         short_ast_json = json.load(f)
#     # open all mentioned source files as array of lines
#     allowed_source_files = {}
#     ### TODO: dict from (file, start_ln, start_col) to js
#     ast_node_query = defaultdict(lambda:(defaultdict(lambda:[])))
#     for kd in target_kinds:
#         for js in short_ast_json[kd]:
#             file = normpath(js['file'])
#             if not file.startswith('delaunayTriangulation/'):
#                 continue
#             # test if file can be opened
#             try: 
#                 with open(file, 'r') as f: 
#                     allowed_source_files[file] = f.readlines()
#             except: 
#                 raise ValueError("{} cannot be opened!".format(file))
#             # 
#             begin_ln = js.get('range').get('begin').get('line')
#             if not begin_ln: 
#                 begin_ln = js.get('loc').get('line')
#             end_ln = js.get('range').get('end').get('line')
#             if not end_ln:
#                 end_ln = js.get('loc').get('line')
#             f = js.get('file')
#             if f and begin_ln and end_ln:
#                 ast_node_query[f][(begin_ln, end_ln)].append(js)
#     if args.error:
#         # print('files in result: {}'.format(len(allowed_source_files)))
#         # print('\n'.join(sorted(list(allowed_source_files.keys()))))
#         pass
    
#     # open cilkfor encountered in llvm passes
#     with open(r"./delaunayTime.cilkfor.json", 'r') as f: 
#         delaunayTime_C_cilkfor_json = json.load(f)
#     with open(r'./delaunay.cilkfor.json', 'r') as f:
#         delaunay_C_cilkfor_json = json.load(f)
    
#     # error checking: files mentioned in cilkfor.json should all appeared in ast with source code info
#     # error checking: every location mentioned in cilkfor.json shoudl
#     if args.error:
#         files_count = defaultdict(lambda: 0, **{ f : 0 for f in allowed_source_files })
#         for js in delaunayTime_C_cilkfor_json:
#             mentioned_files = set()
#             for inlineJs in js['inlineHistory']:
#                 mentioned_files.add(normpath(inlineJs['file']))
#             for file_path in mentioned_files:
#                 files_count[file_path] += 1

#         for js in delaunay_C_cilkfor_json:
#             mentioned_files = set()
#             for inlineJs in js['inlineHistory']:
#                 mentioned_files.add(normpath(inlineJs['file']))
#             for file_path in mentioned_files:
#                 files_count[file_path] += 1

#         # evaluate missing file impact on cilkfor substitution
#         missing_files = dict()
#         missing_reference = 0
#         used_files = dict()
#         used_reference = 0
#         unused_files = dict()
#         unused_reference = 0
#         for file in files_count: 
#             if file not in allowed_source_files:
#                 missing_reference += files_count[file]
#                 missing_files[file] = files_count[file]
#             elif files_count[file] > 0: 
#                 used_reference += files_count[file]
#                 used_files[file] = files_count[file]
#             else: 
#                 unused_reference += files_count[file]
#                 unused_files[file] = files_count[file]
        
#         # print("---- missing files: {} files, {} cilkfor references ----------------".format(len(missing_files), missing_reference))
#         # print('\n'.join(sorted(list([ "{}:\t{}".format(cnt, f) for f, cnt in missing_files.items()]))))
#         # print("---- used files:    {} files, {} cilkfor references ----------------".format(len(used_files), used_reference))
#         # print('\n'.join(sorted(list([ "{}:\t{}".format(cnt, f) for f, cnt in used_files.items()]))))
#         # print("---- unused files:  {} files, {} cilkfor references ----------------".format(len(unused_files), unused_reference))
#         # print('\n'.join(sorted(list([ "{}:\t{}".format(cnt, f) for f, cnt in unused_files.items()]))))
    
#         # every location mentioned in cilkfor.json should be accessible
#         js = delaunay_C_cilkfor_json[0]

#         keyword = "parallel_for"
#         for inlineJs in js.get('inlineHistory'):
#             ln = inlineJs['inlinedAt'] # 1-index, remember offset
#             col = inlineJs['col']
#             filename = normpath(inlineJs['file'])
#             try: 
#                 with open(filename, 'r') as f:
#                     source_file = f.readlines()
#             except: 
#                 raise ValueError("cannot open {}".format(filename))
#             print("file {}\t keyword {}\t found: {}".format(filename, keyword, source_file[ln-1][col-1:col-1+len(keyword)]))

#             #### update keyword
#             # find tightest enclosing construct
#             bestKey = None
#             for key in ast_node_query[filename]:
#                 if not (key[0] <= ln <= key[1]):
#                     continue
#                 if bestKey is None or (key[1]-key[0]) < (bestKey[1] - bestKey[0]):
#                     bestKey = key
#             if not bestKey:
#                 raise ValueError("cannot find tightest enclosing constructs for {}".format(keyword))
#             js_collection = ast_node_query[filename][bestKey]

#             for js in js_collection:
#                 # print(json.dumps(js, indent=4))
#                 ln = js.get('loc').get('line')
#                 col = js.get('loc').get('col')
#                 tokLen = js.get('loc').get('tokLen')
#                 keyword = js.get('name')
#                 kind = js.get('kind')
#                 print("--> new keyword: {} with kind = {}".format(keyword, kind))
#                 print(json.dumps(js, indent=2))

#     # print('\n'.join([ "{}:\n{}".format(k, json.dumps(v, indent=2)) for k, v in ast_node_query.items()]))
#     return 

    