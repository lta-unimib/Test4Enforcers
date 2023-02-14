import json
import os
import os.path
from pprint import pprint
from random import randrange
import re
import shutil
import subprocess
import time

import networkx as nx
from dotenv import dotenv_values
from natsort import natsorted
from config import get_config_for_policy

import hsi
import utils


def run_droidbot(apk_path, output_folder, replay_folder=None, events_count=20):
    command = [
        'droidbot',
        f'-a {apk_path}',
        f'-o {output_folder}',
        '-keep_app',
        '-use_method_profiling full',
    ]

    if device_is_emulator:
        command += [
            '-is_emulator'
        ]

    if replay_folder is not None:
        command += [
            '-policy replay',
            '-keep_env',
            '-grant_perm',
            f'-replay_output {replay_folder}',
        ]
    else:
        command += [
            '-policy bfs_greedy',
            f'-count {events_count}',
        ]

    print('  Command', '(REPLAY):' if replay_folder is not None else '(EXPLORE):', command)
    subprocess.call(' '.join(command), shell=True)


def add_android_method(G, event_list):
    print('> Annotate G with api_method_names:')

    events_path = os.path.join(output_path, 'events')

    global root

    path_root = os.path.join(events_path, list(natsorted(os.listdir(events_path)))[1])
    root = None
    try:
        with open(path_root) as r:
            entrypoint = json.load(r)
        root = entrypoint['start_state']
    except json.decoder.JSONDecodeError:
        print(f' ! Invalid json file: {path_root}')

    has_root = False
    for source, _ in G.edges():
        if source == root:
            has_root = True

    if not has_root:
        print(' ! Invalid root found. Picking a new root node')
        for source, _, data in G.edges(data=True):
            if 'start' in data['event']:
                root = source
    print(f' - Root node: {root}')

    # Per ogni evento recupero il .trace corrispondente, poi per ogni
    # event in event_list, se questo è presente nel contenuto della trace
    # aggiungo nel grafo
    for filename in natsorted(os.listdir(events_path)):
        event_path = os.path.join(events_path, filename)

        try:
            with open(event_path) as f:
                event = json.load(f)
        except:
            print(f' ! Invalid json file: {filename}')
            continue

        # tag = event['tag']
        # event_id = tag[tag.find('_') + 1:]

        trace_filename = filename.replace('event_', 'event_trace_').replace('.json', '.trace')
        trace_path = os.path.join(output_path, 'traces', trace_filename)

        print(f' - Checking {trace_filename}:')
        if not os.path.exists(trace_path):
            print(f'   Trace file {trace_filename} does not exist')
            continue

        with open(trace_path, encoding='utf-8', errors='ignore') as f:
            trace = f.read()

        android_method = []
        start_state = event['start_state']
        stop_state = event['stop_state']

        if not G.has_edge(start_state, stop_state):
            print(f'    ! Edge not found: {start_state} -> {stop_state} in G. Skipping trace')
            continue
        elif 'key' in G[start_state][stop_state][0]:
            android_method = G[start_state][stop_state][0]['key']

        has_at_least_one_trace = len(android_method) > 0
        for e in event_list:
            if e in trace:
                has_at_least_one_trace = True

                # Costruisco dinamicamente la lista di stringhe da mettere come secondo
                # attributo dell'arco prendendo il nome del metodo delimitato tra i due tab
                result = extract_method_name(e)
                android_method.append(result)
                print('    [FOUND]', result)

        # Se in una traccia non ho alcun metodo, inserisco 'None'
        if not has_at_least_one_trace:
            android_method = ['None']

        G[start_state][stop_state][0]['key'] = list(set(android_method))

    for start_state, stop_state, data in G.edges(data=True):
        if 'key' not in data:
            G[start_state][stop_state][0]['key'] = ['None']


def find_path_nodes(G, event_list):
    print()

    api_method_names = [re.search('\t(.*)\t', event).group(1) for event in event_list]
    print(f'# Find path nodes: {api_method_names}')

    #creo lista di nomi dei file json per replay
    json_name_full_list = []
    api_list = []
    json_final_list = []

    cut = False

    t = []
    # Trovo sorgente e calcolo tutti i possibili path dalla radice al primo evento
    print()
    print(f'Root method: {api_method_names[0]}')
    for sorg, target_first, data in G.edges(data=True):
        print(sorg, target_first, data['key'])
        if 'key' in data and api_method_names[0] in data['key']:
            print(f'- Edge: {sorg} -> {target_first}')
            t.append(target_first)

            event_api = data['event'] #passo a find_path l'api dell'ultimo evento che chiama il metodo target
            temp_api = api_method_names[0]
            print(f'- Event: ', data['event'])

            find_path(
                G,
                root,
                sorg,
                target_first,
                json_name_full_list,
                event_api,
                api_list,
                temp_api,
                api_method_names
            )
            print("----------------")

    if len(t) == 0:
        print('Start event of trace not found')
        return False

    temp = t[0]

    # Calcolo tutti i path dal nodo target dell'evento precendente al nuovo nodo target
    if len(api_method_names) > 1:
        for i, api_method in enumerate(api_method_names[1:], start=1):
            for sorg, target, data in G.edges(data=True):
                if api_method in data['key']:
                    print(f'Next method: {api_method}')
                    print(f'- Edge: {sorg} -> {target}')
                    # Passo a find_path l'api dell'ultimo evento che chiama il metodo target
                    event_api = data['event']
                    temp_api = api_method
                    print(f'- Event: ', data['event'])

                    find_path(
                        G,
                        temp,
                        sorg,
                        target,
                        json_name_full_list,
                        event_api,
                        api_list,
                        temp_api,
                        api_method_names
                    )

                    if i < len(api_method_names) - 1:
                        if api_method == api_method_names[i+1]:
                            print("stesso sorg")
                            if len(t) > 1:
                                temp = t[1]
                        else:
                            temp = target

                    print("----------------")

    print(f'- Lista temporanea nomi json degli eventi (length={len(json_name_full_list)}):', json_name_full_list)

    # os.system.exit()

    #gestione del numero di archi con release+onpause per evitare path doppi
    if len(json_name_full_list) == 1:
        for i in range(0, len(json_name_full_list)):
            json_final_list.append(json_name_full_list[i])
    else:
        for i in range(0, len(json_name_full_list)):
            # if (i % el): #MODIFICARE
            json_final_list.append(json_name_full_list[i])

    print("LISTA FINALE DI JSON: ")
    print(json_final_list)

    create_replay_folders(json_final_list, cut)

    return True


def create_replay_folders(json_name_full_list, cut):
    folderPath = os.sep.join([ output_path, 'events'])
    destinationPath = os.sep.join([output_path, 'replay_folder'])
    if not os.path.exists(destinationPath):
        os.makedirs(destinationPath)

    #CREO FOLDER PER OGNI PATH DI OGNI METODO
    #il carattere 'ch' serve per dare il nome ad ogni json, es. [a1.json, a2.json, b1.json, b2.json]
    ch= "a"
    for sublist in json_name_full_list:
        print(str(json_name_full_list.index(sublist)))
        path = os.sep.join([destinationPath, "folder" + str(json_name_full_list.index(sublist))])
        if not os.path.exists(path):
            os.makedirs(path)

        for subsublist in sublist:
            second_path = os.sep.join([path, "path" + str(sublist.index(subsublist))])
            if not os.path.exists(second_path):
                os.makedirs(second_path)
            print(second_path)
            x = chr(ord(ch) + json_name_full_list.index(sublist))
            for j in range(0, len(subsublist)):
                if subsublist[j] in list(natsorted(os.listdir(folderPath))):
                    name = os.path.join(folderPath, subsublist[j])
                    print(name)
                    destination_name = os.path.join(second_path, x + str(j) + ".json")
                    if os.path.isfile(name):
                        try:
                            #copio il file json nella cartella corretta
                            shutil.copy(name, destination_name)

                        except shutil.SameFileError:
                            # code when Exception occur
                            pass
                    else:
                        print
                        'file does not exist', name

    #creo cartella dove ci sarà il path finale da testare con droidbot
    target_path = os.sep.join([output_path, 'c_temp'])
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    print()
    #creo una lista che contiene i path dei folder
    folder_list = fast_scandir(destinationPath)
    print()

    if cut:
        folder_list.pop(-2)


    if os.path.exists(os.sep.join([destinationPath, "folder0", "path0", "a0.json"])):
        with open(os.sep.join([destinationPath, "folder0", "path0", "a0.json"])) as f:
            event = json.load(f)
            if event['start_state'] == root:
                f.close()
                if os.path.exists(os.sep.join([destinationPath, "folder1", "path0", "b0.json"])):
                    with open(os.sep.join([destinationPath, "folder1", "path0", "b0.json"])) as j:
                        event = json.load(j)
                        if event['start_state'] == root:
                            folder_list.pop(0)
                            j.close()
                            if os.path.exists(os.sep.join([destinationPath, "folder2", "path0", "c0.json"])):
                                with open(os.sep.join([destinationPath, "folder2", "path0", "c0.json"])) as g:
                                    event = json.load(g)
                                    if event['start_state'] == root:
                                        folder_list.pop(1)
                                        g.close()
            else:
                folder_list.pop(0)
    if os.path.exists(os.sep.join([destinationPath, "folder2", "path0", "c0.json"])):
        with open(os.sep.join([destinationPath, "folder2", "path0", "c0.json"])) as g:
            event = json.load(g)
            if event['start_state'] == root:
                folder_list.pop(0)
                g.close()


    #CREO I FOLDER CON I PATH COMPLETI
    #j rappresenta le combinazioni di path
    for j in range(5):
        #creo path finale es. events/0, events/1 ...
        final_path = os.sep.join([target_path, str(j), "events"])

        if not os.path.exists(final_path):
            os.makedirs(final_path)

        #metto due json extra all'inizio di ogni path che verranno saltati in automatico da droidbot
        try:
            if len(list(natsorted(os.listdir(os.sep.join([destinationPath, 'folder0','path0']))))) != 0:
                shutil.copy(os.sep.join([destinationPath, 'folder0', 'path0', 'a0.json']), os.sep.join([final_path, '0.json']))
                shutil.copy(os.sep.join([destinationPath, 'folder0', 'path0', 'a0.json']), os.sep.join([final_path, '1.json']))
                shutil.copy(os.sep.join([destinationPath, 'folder0', 'path0', 'a0.json']), os.sep.join([final_path, '2.json']))
            elif os.path.exists(os.sep.join([destinationPath, 'folder0', 'path1'])):
                if len(list(natsorted(os.listdir(os.sep.join([destinationPath, 'folder0', 'path1']))))) != 0:
                    shutil.copy(os.sep.join([destinationPath, 'folder0', 'path1', 'a0.json']), os.sep.join([final_path, '0.json']))
                    shutil.copy(os.sep.join([destinationPath, 'folder0', 'path1', 'a0.json']), os.sep.join([final_path, '1.json']))
                    shutil.copy(os.sep.join([destinationPath, 'folder0', 'path1', 'a0.json']), os.sep.join([final_path, '2.json']))
            else:
                try:
                    shutil.copy(os.sep.join([destinationPath, 'folder1', 'path0', 'b0.json']), os.sep.join([final_path, '0.json']))
                    shutil.copy(os.sep.join([destinationPath, 'folder1', 'path0', 'b0.json']), os.sep.join([final_path, '1.json']))
                    shutil.copy(os.sep.join([destinationPath, 'folder1', 'path0', 'b0.json']), os.sep.join([final_path, '2.json']))
                except:
                    print()
                    print("---------->        NON è possibile trovare un path         <-----------")
                    print()
                    return
        except shutil.SameFileError:
            pass
        #riempio una cartella events/x alla volta prendendo da ogni folder un path casuale
        for folder in folder_list:
            #prendo la lista di cartelle contenute in ogni folder
            path_list = second_fast_scandir(folder)
            # scelgo un path random per ogni metodo
            if (len(path_list)<=1):
                random_path = 0
            else:
                random_path = randrange(len(path_list) )
            for el in natsorted(os.listdir(path_list[random_path])):
                src = os.path.join(path_list[random_path], el)
                if os.path.isfile(src):
                    try:
                        # copio i file json nella cartella con il path completo da testare
                        shutil.copy(src, final_path)
                    except shutil.SameFileError:
                        pass

    for folder in natsorted(os.listdir(target_path)):
        n_folder = os.path.join(target_path, folder)
        if os.path.exists(os.sep.join([n_folder, "events", "a0.json"])):
            with open(os.sep.join([n_folder, "events", "a0.json"])) as f:
                event = json.load(f)
                if event['start_state'] != root:
                    print(event['start_state'])
                    print(root)
                    f.close()
                    shutil.rmtree(n_folder, ignore_errors=True)
                    pprint('RIMOSSO NFOLDER')


#metodo usato per ottenere il path di folder0, folder1 ecc
def fast_scandir(dirname):
    return [f.path for f in os.scandir(dirname) if f.is_dir()]


#metodo usato per ottenere i path di quello che è contenuto in folder0, folder1 ecc
def second_fast_scandir(dirname):
    subfolders = fast_scandir(dirname)
    for dirname in list(subfolders):
        subfolders.extend(fast_scandir(dirname))
    return subfolders


def find_path(G, root, sorg, target, json_name_full_list, event_api, api_list, temp_api, api_method_names):
    print()
    print(f'{root} -> {sorg}')
    print(f'{sorg} -> {target}')

    #ottengo la copia del grafo G senza gli archi dei i metodi che non mi interessano
    H = filter_paths(G, temp_api, api_method_names)

    print()

    # All unique single paths, like in nx.DiGraph
    unique_single_paths = set(
        # Sets can't be used with lists because they are not hashable
        tuple(path) for path in nx.all_simple_paths(H, source=root, target=sorg)
    )
    print('- Unique single paths:', unique_single_paths)

    print()
    is_unique = True
    # Check if we have two consecutive method calls
    for i, event in enumerate(api_method_names):
        if i > 0 and api_method_names[i - 1] == event:
            is_unique = False

    json_name_list = []
    # Se il metodo che cerco ha un arco solo aggiungo direttamente il json dell'arco
    if len(api_method_names) == 1:
        if len(unique_single_paths) == 0:
            json_name = []
            for filename in natsorted(os.listdir(os.sep.join([output_path, 'events']))):
                with open(os.path.join(output_path, 'events', filename)) as f:
                    event = json.load(f)
                if event['start_state'] == root and event['stop_state'] == target and event['event_str'] == event_api:
                    json_name.append(filename)

            json_name_list.append(json_name)
    else:
        if len(unique_single_paths) == 0:
            json_name = []
            for filename in natsorted(os.listdir(os.sep.join([output_path, 'events']))):
                with open(os.path.join(output_path, 'events', filename)) as f:
                    event = json.load(f)
                if event['start_state'] == sorg and event['stop_state'] == target and event['event_str'] == event_api and is_unique:
                    json_name.append(filename)

            if not json_name:
                print()
                print("---------->        NON è possibile trovare un path         <-----------")
                # quit()
            json_name_list.append(json_name)

    print('- JSON name list:', json_name_list)

    print('- Temp api:', temp_api)
    #creo lista di con i metodi uguali ma diversi che sono stati trovati es. ['open', 'open', 'release', 'release', 'onPause', 'onPause']
    if temp_api != '':
        api_list.append(temp_api)

    combined_single_paths = []
    for path in unique_single_paths:
        # Get all node pairs in path:
        # [1,2,3,4] -> [[1,2],[2,3],[3,4]]
        pairs = [path[i: i + 2] for i in range(len(path) - 1)]
        #creo una lista di liste dei nomi dei file json che appartengono agli eventi dei path
        json_name = []
        #prendo gli eventi
        for pair in pairs:
            print("PAIR")
            print(pair)
            for filename in natsorted(os.listdir(os.sep.join([output_path, 'events']))):
                event_path = os.sep.join(([output_path, 'events', filename]))
                with open(event_path) as f:
                    event = json.load(f)
                    if event['start_state']==pair[0] and event['stop_state']==pair[1] and event['event_str']==H[pair[0]][pair[1]][0]['event']:
                        json_name.append(filename)

        #aggiungo ultimo evento che chiama il metodo effettivo
        for filename in natsorted(os.listdir(os.sep.join([output_path, 'events']))):
            event_path = os.sep.join([output_path, 'events', filename])
            with open(event_path) as f:
                event = json.load(f)
                if event['start_state']==sorg and event['stop_state']==target and event['event_str'] == event_api:
                    json_name.append(filename)

        json_name_list.append(json_name)

        print("LISTA")
        print(json_name_list)
        # Construct the combined list for path
        combined_single_paths.append([
            (pair, H[pair[0]][pair[1]])  # Pair and all node between these nodes
            for pair in pairs
        ])

    print()
    print('- Lista dei nomi dei file JSON:', json_name_list)
    json_name_full_list.append(json_name_list)

    # unisco le liste che hanno ad esempio due open diversi
    if len(api_list) > 1:
        if (api_list[-1] == api_list[-2]):
            print(api_list[-1], 'AND', api_list[-2])
            json_name_full_list[-1].extend(json_name_full_list[-2])

    # print(sorg)
    # print(target)
    print()

    combined_single_paths.append(G.get_edge_data(sorg, target))
    # print(combined_single_paths)

    # # Stampo l'ultimo arco del path che ovviamente conosco a priori
    # print(G.get_edge_data(sorg, target))
    # print()
    # pos = nx.spring_layout(G)
    # nx.draw(G)
    # plt.show()


def format_events(events):
    """Transform the input method call into the following structure: package.Activity\tmethod\t(I?)
    This will be used in further stage to lookup for events in the recorded trace files

    Args:
        events (list): The api call strings to transform

    Returns:
        list: The transformed list of events.
    """
    formatted = []

    for event in events:
        method_call = '\t'.join(event.rsplit('.', 1))
        args = method_call.rindex('(')
        method_call = method_call[:args] + '\t' + method_call[args:]

        formatted.append(method_call)

    return formatted


def format_traces(event_list):
    """Transform the input method call into the following structure: package.Activity\tmethod\t(I?)
    This will be used in further stage to lookup for events in the recorded trace files

    Args:
        events (list): The api call strings to transform

    Returns:
        list: The transformed list of events and the transformed traces with outputs.
    """
    traces = []
    traces_with_output = []

    for event, value in event_list:
        method_call = '\t'.join(event.rsplit('.', 1))
        args = method_call.rindex('(')
        method_call = method_call[:args] + '\t' + method_call[args:]

        traces.append(method_call)
        traces_with_output.append((method_call, value))

    return traces, traces_with_output


#metodo per filtrare gli eventi che vogliamo escludere dai path finali
def filter_paths(G, current_api_method_name, api_method_names):
    """Filter edges in G which doesn't contain current_api_method_name in edge data.

    Args:
        current_api_method_name (string): The api_method_name to preserve
        api_method_names (string): The possible api_method_name stored in edges

    Returns:
        nx.MultiDiGraph: Networkx instance with only edges which contains the searched method name.
    """
    H = G.copy()

    print()
    print('## Filter paths')
    print('- Current event:', current_api_method_name)
    print('- Simple event list:', api_method_names)

    api_method_names_to_exclude = set()
    for _, _, data in G.edges(data=True):
        if ('None' not in data['key']) and (current_api_method_name not in data['key']):
            for api_method_name in data['key']:
                api_method_names_to_exclude.add(api_method_name)

    print('- Api method names to exclude:', api_method_names_to_exclude)

    for api_method_name in api_method_names_to_exclude:
        excluded_edges = [(u, v) for u, v, e in H.edges(data=True) if api_method_name in e['key']]
        print(f'- Removed edges for method \'{api_method_name}\': {excluded_edges}')
        H.remove_edges_from(excluded_edges)

    return H


def replay_stuff(event_list_formatted, index, skip_method):
    path_to_replay = os.sep.join([output_path, "c_temp"])

    final_result = os.sep.join([output_path, "final_result" + str(index)])
    if not os.path.exists(final_result):
        os.makedirs(final_result)
    else:
        print('Skipping replay_stuff as final_result already exists')
        return

    folders_num = len(next(os.walk(path_to_replay))[1])
    print(path_to_replay)
    print(f'Folder num: {folders_num}')
    for i in range(folders_num - 1):
        print(f'\n> Replaying folder: {i}')

        final_output = os.sep.join([output_path, "replay_folder", "final_output", str(i)])
        if not os.path.exists(final_output):
            os.makedirs(final_output)

        # subprocess.call("droidbot -replay_output " + path_to_replay + str(i) + " -grant_perm -a C:\\Users\\User\\PycharmProjects\\generateEventSequences\\fooCam-debug.apk -o " + final_output + " -use_method_profiling full -policy replay -keep_app -keep_env -is_emulator")
        path_to_replay  = os.sep.join([os.sep.join([output_path, "c_temp"]), str(i)])
        # subprocess.call("droidbot -replay_output " + path_to_replay  + " -grant_perm -a " + apk_path + " -o " + final_output + " -use_method_profiling full -policy replay -keep_app -keep_env -is_emulator", shell=True)
        run_droidbot(apk_path, final_output, replay_folder=path_to_replay)
        path_to_check = os.sep.join([final_output, "events"])

        #creo una lista temporanea con gli eventi da controllare senza doppioni
        temp_list = event_list_formatted[:]
        temp_list = list(dict.fromkeys(temp_list))
        print(temp_list)

        methods_checked = []
        if (len(temp_list) > 0):
            if os.path.exists(path_to_check):
                for j in range(0, len(temp_list)):
                        for trace in natsorted(os.listdir(path_to_check)):
                            if "trace" in trace:
                                trace_path = os.path.join(path_to_check, trace)
                                with open(trace_path, encoding='utf-8', errors='ignore') as tr:
                                    read_t = tr.read()
                                    if temp_list[j] in read_t:
                                        methods_checked.append(temp_list[j])

        print(methods_checked)
        # metto i path corretti in un folder dedicato
        if (len(set(event_list_formatted)) == len(set(methods_checked))):
            print(True)
            dest_dir = os.sep.join([final_result, "events"])
            print(dest_dir)
            shutil.copytree(path_to_check, dest_dir)
            if skip_method:
                skip = check_skip(dest_dir, skip_method)
                if skip:
                    print()
                    print("Non è stato possibile trovare un path che escludesse " + skip_method)
                    shutil.rmtree(dest_dir, ignore_errors=True)

            return

        else:
            print(False)


def check_skip(path, skip_method):
    skip = False
    for trace in natsorted(os.listdir(path)):
        trace_path = os.path.join(path, trace)
        with open(trace_path, encoding='utf-8', errors='ignore') as tr:
            read_t = tr.read()
            if skip_method in read_t:
               skip=True
    return skip


def replay_stuff_enforcer(event_list_formatted, index, enabled_modules_path, enforcer_apk_path, disable_when_done=True, should_enable_enforcer=True):
    if not os.path.isdir(os.sep.join([output_path, "final_result" + str(index), "events"])):
        # subprocess.call("adb reboot", shell=True)
        # time.sleep(25)
        print('! final_result folder does not exist!')
        return

    if os.path.isdir(os.sep.join([output_path, "final_result_enforcer" + str(index), "events"])):
        print(f'! final_result_enforcer{index} folder already exist!')
        return

    print()

    if should_enable_enforcer:
        print('Enabling enforcer on connected device. The device will reboot itself.')
        utils.enable_enforcer(enabled_modules_path, enforcer_apk_path)
    else:
        subprocess.call('adb reboot', shell=True)
    time.sleep(droidbot_reboot_delay)

    path_to_replay = os.path.join(output_path, 'c_temp')
    final_result = os.path.join(output_path, f'final_result_enforcer{index}')
    if not os.path.exists(final_result):
        os.makedirs(final_result)

    folders_num = len(next(os.walk(path_to_replay))[1])
    print(path_to_replay)
    print(folders_num)

    for i in range(folders_num):
        final_output = os.path.join(output_path, 'replay_folder', f'final_output_enforcer{index}', str(i))
        if not os.path.exists(final_output):
            os.makedirs(final_output)

        path_to_replay = os.path.join(output_path, 'c_temp', str(i))
        # subprocess.call('droidbot -replay_output ' + path_to_replay + ' -grant_perm -a ' + apk_path + ' -o ' + final_output + ' -use_method_profiling full -policy replay -keep_app -keep_env -is_emulator', shell=True)
        run_droidbot(apk_path, final_output, replay_folder=path_to_replay)
        path_to_check = os.path.join(final_output, 'events')

        #creo una lista temporanea con gli eventi da controllare senza doppioni
        unique_api_methods = event_list_formatted[:]
        print('Unique API methods:', unique_api_methods)

        executed_methods = []
        if (len(unique_api_methods) > 0):
            if os.path.exists(path_to_check):
                for api_method in unique_api_methods:
                    for trace in natsorted(os.listdir(path_to_check)):
                        if 'trace' in trace:
                            trace_path = os.path.join(path_to_check, trace)
                            with open(trace_path, encoding='utf-8', errors='ignore') as tr:
                                read_t = tr.read()
                            if api_method in read_t:
                                executed_methods.append(api_method)
        print('Executed methods:', executed_methods)

        if any([
            enforcer_action == 'add_call' and len(set(event_list_formatted)) == len(set(executed_methods)),
            enforcer_action == 'replace_call' and len(set(unique_api_methods) - set(executed_methods)) == len(unique_api_methods),
            enforcer_action == 'prevent_call' and len(set(unique_api_methods) - set(executed_methods)) < len(unique_api_methods)
        ]):
            dest_dir = os.path.join(final_result, 'events')
            print(dest_dir)

            os.system(f'adb pull "{xposed_log_file}" "{final_result}/xposed.log"')

            try:
                shutil.copytree(path_to_check, dest_dir)
            except FileExistsError:
                print(f'! Error while copying tree to destination dir {dest_dir}. Directory already exists!')

            if disable_when_done:
                device_disable_enforcer(enabled_modules_path, enforcer_apk_path)
            return

        print(False)


def device_disable_enforcer(enabled_modules_path, enforcer_apk_path):
    print()
    print('Disabling enforcer on connected device.')
    utils.disable_enforcer(enabled_modules_path, enforcer_apk_path, wait_for_device=False)
    time.sleep(droidbot_reboot_delay)


def check_methods(event_list):
    simple_event_list = []
    for i in range(0, len(event_list)):
        result = re.search('\t(.*)\t', event_list[i])
        simple_event_list.append(result.group(1))

    if not(len(simple_event_list) == 3 and simple_event_list[1] != simple_event_list[2]):
        return True

    for _, _, data in G.edges(data=True):
        if simple_event_list[1] in data['key']:
            print(data['key'])
            return True

    print()
    print("---------->        NON è possibile trovare un path         <-----------")
    print()
    return False


def process_droidbot_outputs(output_path):
    """Remove duplicate events (and their associated .trace file) with same start, stop and event_str, but different tags.
    Then separate the remaining .trace files from events by moving them to the 'traces' folder.

    In case of empty event json files, ignore the error and delete the file. This would prevent errors at later stages.
    Empty files are often generated by droidbot when starting the application activity with the profiler flags.

    Args:
        output_path (string): The base droidbot output folder with events and traces
    """
    events_path = os.path.join(output_path, 'events')
    traces_path = os.path.join(output_path, 'traces')

    assert os.path.exists(events_path)
    utils.create_path(traces_path)

    events = {}
    traces = {}
    # Read all events/traces files
    for filename in natsorted(os.listdir(events_path)):
        path = os.path.join(events_path, filename)

        try:
            with open(path) as f:
                if filename.lower().endswith('.json'):
                    events[filename] = json.load(f)
                elif filename.lower().endswith('.trace'):
                    traces[filename] = path
                else:
                    print(f'! Unrecognized file in events folder: {filename}')
        except json.decoder.JSONDecodeError:
            # raise Exception(f'Invalid JSON file contents: {filename}')
            print(f'Skipping invalid JSON file contents: {filename}')
            os.remove(path)

    # Remove event/trace files if same event with
    # different tags has been recorded
    event_items = list(events.items())
    for i in range(len(event_items)):
        for j in range(i, len(event_items)):
            f1, e1 = event_items[i]
            f2, e2 = event_items[j]

            if all([
                f2 in events,
                f1 != f2,
                e1['tag'] != e2['tag'],
                e1['start_state'] == e2['start_state'],
                e1['stop_state'] == e2['stop_state'],
                e1['event_str'] == e2['event_str'],
            ]):
                os.remove(os.path.join(events_path, f2))
                events.pop(f2)

                t2 = f2.replace('event_', 'event_trace_').replace('.json', '.trace')
                os.remove(os.path.join(events_path, t2))
                traces.pop(t2)

    # Move remaining .trace files
    for filename in traces:
        source = os.path.join(events_path, filename)
        target = os.path.join(traces_path, filename)
        shutil.move(source, target)
        traces[filename] = target


def check_replay_output(sequence_with_flags, api_methods, index):
    final_result = os.sep.join([output_path, 'final_result' + str(index), 'events'])
    final_result_enf = os.sep.join([output_path, 'final_result_enforcer' + str(index), 'events'])

    if not os.path.isdir(final_result) or not os.path.exists(final_result_enf):
        print('---------->        NON è possibile trovare un path         <-----------')
        return

    #trasformo la lista di tuple in una lista di stringhe
    sequence = [api_method for api_method, _ in sequence_with_flags]

    print(' - API methods        :', api_methods)
    print(' - Sequence with flags:', sequence_with_flags)
    print(' - Sequence           :', sequence)

    if enforcer_action == 'prevent_call':
        method_calls = []
        method_calls_enf = []

        for event in sequence_with_flags:
            matches, fname = check_replay_traces(event, api_methods, final_result, False, True)
            matches_enf, fname_enf = check_replay_traces(event, api_methods, final_result_enf, False, True)

            for call in matches:
                method_calls.append(call)
            for call in matches_enf:
                method_calls_enf.append(call)

        # method_calls = list(map(lambda x: x[2], sorted(method_calls)))
        # method_calls_enf = list(map(lambda x: x[2], sorted(method_calls_enf)))
        method_calls = list(sorted(method_calls))
        method_calls_enf = list(sorted(method_calls_enf))

        print('Matches:', list(map(lambda x: x[2], method_calls)))
        print('Matches enf:', list(map(lambda x: x[2], method_calls_enf)))

        i = j = 0

        for method, should_skip in sequence_with_flags:
            while i+1 < len(method_calls) and method_calls[i+1][2] == method:
                i += 1

            had_call_enf = method_calls_enf[j][2] == method
            while j+1 < len(method_calls_enf) and method_calls_enf[j+1][2] == method:
                had_call_enf = True
                j += 1

            print()
            print(f'# Checking method call match: method = {method}')

            if should_skip and had_call_enf:
                print(f'Method call "{method}" should have not happened.')
            elif should_skip and not had_call_enf:
                print(f'Method call "{method}" has been prevented.')
            elif not should_skip and not had_call_enf:
                print(f'Method call "{method}" is unexpectedly missing.')


            start_state, stop_state = check_replay_json(method_calls[i][0], final_result)
            start_state_enf, stop_state_enf = None, None
            if had_call_enf:
                start_state_enf, stop_state_enf = check_replay_json(method_calls_enf[j][0], final_result_enf)

            print('Start and stop states are', end=' ')
            if start_state == start_state_enf and stop_state == stop_state_enf:
                print('EQUAL')
            else:
                print('DIFFERENT')

            print()

            print('Regular states:')
            print(f' - Start = {start_state}')
            print(f' - Stop  = {stop_state}')

            print('States with enforcer enabled: ')
            print(f' - Start = {start_state_enf}')
            print(f' - Stop  = {stop_state_enf}')

        print()
        # print(method_calls[i])
        # print(method_calls_enf[j])

    else:
        for event in sequence_with_flags:
            method_call, should_differ = event

            print()
            print(f'# Checking method call match: method = {event}')

            start_state, stop_state = (None, None)
            start_state_enf, stop_state_enf = (None, None)

            if enforcer_action == 'add_call':
                # lista di api trovate senza enforcer e nome del json associato alla trace
                matches, fname = check_replay_traces(event, api_methods, final_result, should_differ)
                # lista di api trovate con enforcer e nome del json associato alla trace
                matches_enf, fname_enf = check_replay_traces(event, api_methods, final_result_enf, should_differ)

                difference_matches = list(set(matches_enf) - set(matches))

                start_state, stop_state = check_replay_json(fname, final_result)
                start_state_enf, stop_state_enf = check_replay_json(fname_enf, final_result_enf)

            elif enforcer_action == 'replace_call':
                matches, event_state = check_replay_traces_with_event(method_call, final_result)
                matches_enf, event_state_enf = find_event_for_state(method_call, event_state, final_result_enf, api_methods)

                difference_matches = method_call in matches and method_call not in matches_enf

                if event_state is not None:
                    start_state, stop_state = event_state['start_state'], event_state['stop_state']
                if event_state_enf is not None:
                    start_state_enf, stop_state_enf = event_state_enf['start_state'], event_state_enf['stop_state']

            print('The trace between normal replay and replay with enforcer is: ', end=' ')
            if should_differ and difference_matches:
                print('DIFFERENT and a difference WAS expected!')
            elif should_differ and not difference_matches:
                if not target_is_faulty:
                    print('EQUAL')
                else:
                    print('EQUAL, but a difference WAS expected!')

            if not should_differ and difference_matches:
                print('DIFFERENT, but a difference WAS NOT expected!')
            elif not should_differ and not difference_matches:
                print('EQUAL, and a difference WAS NOT expected')

            print()
            print('Regular execution:', matches)
            print('Enforcer execution:', matches_enf)
            print()

            print('Start and stop states are', end=' ')
            if start_state == start_state_enf and stop_state == stop_state_enf:
                print('EQUAL')
            else:
                print('DIFFERENT')

            print()

            print('Regular states:')
            print(f' - Start = {start_state}')
            print(f' - Stop  = {stop_state}')

            print('States with enforcer enabled: ')
            print(f' - Start = {start_state_enf}')
            print(f' - Stop  = {stop_state_enf}')

        print()

        extra = False
        extra_enf = False

        # Metodo extra che ci si aspetta di trovare solo nell'esecuzione con l'enforcer se l'app è buggata
        extra_methods = list(set(api_methods) - set(sequence))
        if extra_methods and enforcer_action == 'add_call':
            print(f'- Extra method: {extra_methods}')

            for trace in natsorted(os.listdir(final_result)):
                trace_path = os.path.join(final_result, trace)
                with open(trace_path, encoding='utf-8', errors='ignore') as tr:
                    read_t = tr.read()
                if extra_methods[0] in read_t:
                    extra = True
                    break

            for trace in natsorted(os.listdir(final_result_enf)):
                trace_path = os.path.join(final_result_enf, trace)
                with open(trace_path, encoding='utf-8', errors='ignore') as tr:
                    read_t = tr.read()
                if extra_methods[0] in read_t:
                    extra_enf = True
                    break

        if not extra and extra_enf:
            print()
            print('The replay with enforcer execution resulted in the execution of additional method calls:', extra_methods)

        # extra XNOR extra_enf === true iff both input are equal
        # if not(extra ^ extra_enf):
        if (not extra and not extra_enf) or (extra and extra_enf):
            print('Non ci sono differenze extra tra le due esecuzioni.')

        print()

def check_replay_traces_with_event(method_call, path):
    matches = set()
    target_state = None

    for trace in natsorted(os.listdir(path)):
        if ".trace" not in trace:
            continue

        trace_path = os.path.join(path, trace)
        with open(trace_path, encoding='utf-8', errors='ignore') as tr:
            read_t = tr.read()

        if method_call not in read_t:
            continue
        else:
            matches.add(method_call)

        event = trace.replace('event_trace', 'event').replace('.trace', '.json')
        event_path = os.path.join(path, event)
        with open(event_path, encoding='utf-8', errors='ignore') as ev:
            read_e = ev.read()
        target_state = json.loads(read_e)
        return matches, target_state

    return matches, target_state


def find_event_for_state(method_call, event_state, path, api_methods):
    matches = set()
    target_state = None

    if not os.path.exists(path):
        return matches, None

    for event in natsorted(os.listdir(path)):
        if "trace" in event:
            continue

        event_path = os.path.join(path, event)
        with open(event_path, encoding='utf-8', errors='ignore') as ev:
            read_e = ev.read()
        candidate_state = json.loads(read_e)

        if event_state is not None and 'start_state' in event_state and 'stop_state' in event_state and any([
            event_state['start_state'] != candidate_state['start_state'],
            event_state['stop_state'] != candidate_state['stop_state'],
        ]):
            continue

        target_state = candidate_state
        trace = event.replace('event_', 'event_trace_').replace('.json', '.trace')
        trace_path = os.path.join(path, trace)
        if not os.path.exists(trace_path):
            continue

        with open(trace_path, encoding='utf-8', errors='ignore') as tr:
            read_t = tr.read()
        for method_call in api_methods:
            if method_call in read_t:
                matches.add(method_call)

    return matches, target_state


def check_replay_output_with_mutations(sequence_with_flags, api_methods, mutation_indexes):
    for m_index in natsorted(mutation_indexes):
        print(f'### Comparing mutation {m_index} output')
        check_replay_output(sequence_with_flags, api_methods, m_index)


def check_replay_json(fname, path):
    for file_json in natsorted(os.listdir(path)):
        event_path = os.path.join(path, file_json)
        if fname in file_json and "trace" not in file_json:
            try:
                with open(event_path) as f:
                    event = json.load(f)
                start_state = event['start_state']
                stop_state = event['stop_state']
            except:
                return [None, None]

    return start_state, stop_state


#metodo per cercare le api nelle tracce associate ai metodi con True
def check_replay_traces(event, sequence, path, should_differ=False, keep_tuple=False):
    matches = set()
    fname = None

    if not os.path.exists(path):
        return matches, None

    for trace in natsorted(os.listdir(path)):
        trace_path = os.path.join(path, trace)

        with open(trace_path, encoding='utf-8', errors='ignore') as tr:
            read_t = tr.read()

        match_at = read_t.find(event[0])
        if len(event) > 0 and match_at != -1:
            fname_temp = re.search('event_trace_(.*).trace', trace)
            fname = fname_temp.group(1)
            matches.add((fname, match_at, event[0]))
            if should_differ:
                for api_method in sequence:
                    if api_method != event:
                        inner_match_at = read_t.find(api_method)
                        if inner_match_at != -1:
                            matches.add((fname, inner_match_at, api_method))
            # break

    if not keep_tuple:
        matches = list(map(lambda x: x[2], sorted(list(matches))))

    return matches, fname


def build_utg_graph(utg_path):
    """Convert an utg.js file to a networkx graph instance preserving nodes and edges.

    Args:
        utg_path (string): The original js graph file

    Returns:
        MultiDiGraph: Networkx graph instance of the utg file
    """
    G = nx.MultiDiGraph()

    with open(utg_path) as utg:
        data = utg.read()
        utg_json = json.loads(data[data.index('{') : data.rindex('}')+1])

        for node in utg_json['nodes']:
            G.add_node(node['id'])

        for edge in utg_json['edges']:
            G.add_edge(edge['from'], edge['to'],
                       event=edge['events'][0]['event_str'])

    return G


def extract_method_name(api_method):
    return re.search('\t(.*)\t', api_method).group(1)


def run(event_list, sequences_with_flag, api_methods):
    not_found_sequences = []

    print('> Searching events')
    for index, raw_sequence in enumerate(sequences_with_flag):
        print()
        print('### Current sequence:', raw_sequence)

        sequence, sequence_with_flag = format_traces(raw_sequence)
        print(' - Sequence:        ', sequence)
        print(' - Sequence w/ flag:', sequence_with_flag)

        if not find_path_nodes(G, sequence):
            print('> Sequence not found in traces. Skipping replay.')
            not_found_sequences.append(sequence)
            continue

        # REPLAY
        if check_methods(sequence):
            skip_list = []
            if event_list[0] not in raw_sequence[0]:
                skip_list = [event_list[0]]
                print(' - Skip list: ', skip_list)

            if not skip_list:
                replay_stuff(sequence, index, skip_list)
                replay_stuff_enforcer(sequence, index, enabled_modules_path, enforcer_apk_path)

                check_replay_output(sequence_with_flag, api_methods, index)
            else:
                skip_list_formatted = format_events(skip_list)
                replay_stuff(sequence, index, skip_list_formatted[0])
        else:
            print('>>> Check methods: FALSE. Skipping replay.')

        shutil.rmtree(os.path.join(output_path, 'c_temp'), ignore_errors=True)
        if index != len(sequences_with_flag) - 1:
            shutil.rmtree(os.path.join(output_path, 'replay_folder'), ignore_errors=True)


def test_enforcer(env, enforcer_package, sequences_with_flag, api_methods):
    mutations_path = env['MUTATIONS_PATH']
    if not os.path.exists(mutations_path):
        mutations_path = os.path.join(os.getcwd(), mutations_path)
        if not os.path.exists(mutations_path):
            print('! Invalid mutations path.')
            return

    not_found_sequences = []
    mutations = os.listdir(mutations_path)

    print('> Searching events')
    for index, raw_sequence in enumerate(sequences_with_flag):
        print()
        print('### Current sequence:', raw_sequence)

        if index <= mutations_skip_sequence_index:
            continue

        sequence, sequence_with_flag = format_traces(raw_sequence)
        print(' - Sequence:        ', sequence)
        print(' - Sequence w/ flag:', sequence_with_flag)

        if not find_path_nodes(G, sequence):
            print('> Sequence not found in traces. Skipping replay.')
            not_found_sequences.append(sequence)
            continue

        # REPLAY
        if check_methods(sequence):
            replay_stuff(sequence, index, [])

            mutation_indexes = set()
            source_path = os.path.join(output_path, f'final_result{index}')
            should_enable_enforcer = True

            for mutation_apk in natsorted(mutations):
                m_id, _ = mutation_apk.split('.')
                m_index = f'{index}_{m_id}'

                # Will be used for replay and evaluation
                dest_path = os.path.join(output_path, f'final_result{m_index}')

                mutation_indexes.add(m_index)
                if int(m_id) <= mutations_skip_until:
                    continue

                print()
                print(f'### Analyzing mutation {m_index}')

                shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                replace_installed_enforcer(enforcer_package, os.path.join(mutations_path, mutation_apk))
                replay_stuff_enforcer(sequence, m_index, enabled_modules_path, enforcer_apk_path, disable_when_done=False, should_enable_enforcer=should_enable_enforcer)
                should_enable_enforcer = False

            if not should_enable_enforcer:
                device_disable_enforcer(enabled_modules_path, enforcer_apk_path)
            check_replay_output_with_mutations(sequence_with_flag, api_methods, mutation_indexes)
        else:
            print('>>> Check methods: FALSE. Skipping replay.')

        shutil.rmtree(os.path.join(output_path, 'c_temp'), ignore_errors=True)
        if index != len(sequences_with_flag) - 1:
            shutil.rmtree(os.path.join(output_path, 'replay_folder'), ignore_errors=True)


def replace_installed_enforcer(enforcer_package, mutation_file):
    print(f'Uninstalling current enforcer: {enforcer_package}')
    subprocess.call(f'adb uninstall {enforcer_package}', shell=True)
    time.sleep(4)
    print(f'Installing mutated enforcer: {mutation_file}')
    subprocess.call(f'adb install {mutation_file}', shell=True)


def main():
    env = dotenv_values('.env')

    global output_path
    output_path = env['OUTPUT_PATH']
    utils.create_path(output_path)

    global enabled_modules_path, xposed_log_file
    enabled_modules_path = env['XPOSED_FOLDER'] + '/conf/modules.list'
    xposed_log_file = env['XPOSED_FOLDER'] + '/log/error.log'

    global target_is_faulty
    target_is_faulty = env['TARGET_POLICY_FAULTY'].lower() == 'true'
    config = get_config_for_policy(env['TARGET_POLICY'], target_is_faulty)

    global apk_path, enforcer_apk_path
    apk_path = config['target_apk']
    enforcer_apk_path = config['enforcer_apk_path']
    enforcer_package = config['enforcer_package']

    global droidbot_reboot_delay
    droidbot_reboot_delay = int(env['DROIDBOT_REBOOT_DELAY'])

    global device_is_emulator
    device_is_emulator = env['DEVICE_IS_EMULATOR'].lower() == 'true'

    global enforcer_action
    enforcer_action = config['enforcer_action']

    global skip_droidbot_exploration
    skip_droidbot_exploration = env['SKIP_DROIDBOT_EXPLORATION'].lower() == 'true'

    global mutations_skip_until
    mutations_skip_until = int(env['MUTATIONS_SKIP_UNTIL']) if 'MUTATIONS_SKIP_UNTIL' in env else 0

    global mutations_skip_sequence_index
    mutations_skip_sequence_index = int(env['MUTATIONS_SKIP_SEQUENCE_INDEX'])  if 'MUTATIONS_SKIP_SEQUENCE_INDEX' in env else -1

    # Esplorazione iniziale di droidbot
    if not skip_droidbot_exploration:
        print('> Running droidbot')
        run_droidbot(apk_path, output_path)

        # Smisto eventi di droidbot in events e traces, rimuovendo gli eventi duplicati.
        print('> Processing droidbot output')
        process_droidbot_outputs(output_path)
    else:
        shutil.rmtree(os.path.join(output_path, 'c_temp'), ignore_errors=True)
        shutil.rmtree(os.path.join(output_path, 'replay_folder'), ignore_errors=True)

    # Costruzione del grafo
    print('> Building UTG graph')
    global G
    G = build_utg_graph(os.path.join(output_path, 'utg.js'))

    # List of method FQDN followed by
    # List of SEQUENCEs. Each SEQUENCE is a list of Tuple(API_METHOD, boolean).
    # The boolean states whether that API_METHOD behaviour will be modified by
    # the enforcer during the execution (True) or not (False).

    automaton_path = config['automaton']
    event_list, sequences_with_flag = hsi.get_suite(automaton_path)
    print('Event List:', event_list)
    print('Sequences:', sequences_with_flag)

    # HSI generated event_list and sequences to speed up execution (unfeasible sequences are not included)

    # Camera
    event_list = ['android.hardware.Camera.open(I)', 'android.hardware.Camera.release()', 'android.app.Activity.onPause()']
    sequences_with_flag = [
        [('android.hardware.Camera.open(I)', False), ('android.app.Activity.onPause()', True)],
        [('android.hardware.Camera.open(I)', False), ('android.hardware.Camera.release()', False), ('android.app.Activity.onPause()', False)]
    ]

    # Camera Preview
    # event_list = ['android.hardware.Camera.startPreview()', 'android.hardware.Camera.stopPreview()', 'android.app.Activity.onPause()']
    # sequences_with_flag = [
    #     [('android.hardware.Camera.startPreview()', False), ('android.app.Activity.onPause()', True)],
    #     [('android.hardware.Camera.startPreview()', False), ('android.hardware.Camera.stopPreview()', False), ('android.app.Activity.onPause()', False)]
    # ]

    # Bluetooth Adapter - not working on Genymotion, missing Bluetooth support
    # event_list = ['android.bluetooth.BluetoothAdapter.enable()', 'android.bluetooth.BluetoothAdapter.disable()', 'android.app.Activity.onDestroy()']
    # sequences_with_flag = [
    #     [('android.bluetooth.BluetoothAdapter.enable()', False), ('android.app.Activity.onDestroy()', True)],
    #     [('android.bluetooth.BluetoothAdapter.enable()', False), ('android.bluetooth.BluetoothAdapter.disable()', False), ('android.app.Activity.onDestroy()', False)]
    # ]

    # Location Manager
    # event_list = [
    #     'android.location.LocationManager.requestLocationUpdates(Ljava/lang/String;JFLandroid/location/LocationListener;)',
    #     'android.location.LocationManager.removeUpdates(Landroid/location/LocationListener;)',
    #     'android.app.Activity.onPause()',
    # ]
    # sequences_with_flag = [
    #     [
    #         ('android.location.LocationManager.requestLocationUpdates(Ljava/lang/String;JFLandroid/location/LocationListener;)', False),
    #         ('android.app.Activity.onPause()', True)
    #     ],
    #     [
    #         ('android.location.LocationManager.requestLocationUpdates(Ljava/lang/String;JFLandroid/location/LocationListener;)', False),
    #         ('android.location.LocationManager.removeUpdates(Landroid/location/LocationListener;)', False),
    #         ('android.app.Activity.onPause()', False)
    #     ],
    # ]

    # Location Manager Service
    # event_list = [
    #     'android.location.LocationManager.requestLocationUpdates(Ljava/lang/String;JFLandroid/location/LocationListener;)',
    #     'android.location.LocationManager.removeUpdates(Landroid/location/LocationListener;)',
    #     'android.app.Service.onDestroy()',
    # ]
    # sequences_with_flag = [
    #     [
    #         ('android.location.LocationManager.requestLocationUpdates(Ljava/lang/String;JFLandroid/location/LocationListener;)', False),
    #         ('android.app.Service.onDestroy()', True)
    #     ],
    #     [
    #         ('android.location.LocationManager.requestLocationUpdates(Ljava/lang/String;JFLandroid/location/LocationListener;)', False),
    #         ('android.location.LocationManager.removeUpdates(Landroid/location/LocationListener;)', False),
    #         ('android.app.Service.onDestroy()', False)
    #     ],
    # ]

    # Sensor Manager
    # event_list = [
    #     'android.hardware.SensorManager.registerListener(Landroid/hardware/SensorEventListener;Landroid/hardware/Sensor;I)',
    #     'android.hardware.SensorManager.unregisterListener(Landroid/hardware/SensorEventListener;Landroid/hardware/Sensor;)',
    #     'android.app.Activity.onPause()',
    # ]
    # sequences_with_flag = [
    #     [
    #         ('android.hardware.SensorManager.registerListener(Landroid/hardware/SensorEventListener;Landroid/hardware/Sensor;I)', False),
    #         ('android.app.Activity.onPause()', True)
    #     ],
    #     [
    #         ('android.hardware.SensorManager.registerListener(Landroid/hardware/SensorEventListener;Landroid/hardware/Sensor;I)', False),
    #         ('android.hardware.SensorManager.unregisterListener(Landroid/hardware/SensorEventListener;Landroid/hardware/Sensor;)', False),
    #         ('android.app.Activity.onPause()', False)
    #     ],
    # ]

    # Sensor Manager Service
    # event_list = [
    #     'android.hardware.SensorManager.registerListener(Landroid/hardware/SensorEventListener;Landroid/hardware/Sensor;I;I;)',
    #     'android.hardware.SensorManager.unregisterListener(Landroid/hardware/SensorEventListener;Landroid/hardware/Sensor;)',
    #     'android.app.Service.onDestroy()',
    # ]
    # sequences_with_flag = [
    #     [
    #         ('android.hardware.SensorManager.registerListener(Landroid/hardware/SensorEventListener;Landroid/hardware/Sensor;I;I;)', False),
    #         ('android.app.Service.onDestroy()', True)
    #     ],
    #     [
    #         ('android.hardware.SensorManager.registerListener(Landroid/hardware/SensorEventListener;Landroid/hardware/Sensor;I;I;)', False),
    #         ('android.hardware.SensorManager.unregisterListener(Landroid/hardware/SensorEventListener;Landroid/hardware/Sensor;)', False),
    #         ('android.app.Service.onDestroy()', False)
    #     ]
    # ]

    # Remote Callback List
    # event_list = [
    #     'android.os.RemoteCallbackList.register(Landroid/os/IInterface;)',
    #     'android.os.RemoteCallbackList.unregister(Landroid/os/IInterface;)',
    #     'android.app.Activity.onPause()'
    # ]
    # sequences_with_flag = [
    #     [
    #         ('android.os.RemoteCallbackList.register(Landroid/os/IInterface;)', False),
    #         ('android.app.Activity.onPause()', True)
    #     ],
    #     [
    #         ('android.os.RemoteCallbackList.register(Landroid/os/IInterface;)', False),
    #         ('android.os.RemoteCallbackList.unregister(Landroid/os/IInterface;)', False),
    #         ('android.app.Activity.onPause()', False)
    #     ],
    # ]

    # Remote Callback List Service
    # event_list = [
    #     'android.os.RemoteCallbackList.register(Landroid/os/IInterface;)',
    #     'android.os.RemoteCallbackList.unregister(Landroid/os/IInterface;)',
    #     'android.app.Service.onDestroy()'
    # ]
    # sequences_with_flag = [
    #     [
    #         ('android.os.RemoteCallbackList.register(Landroid/os/IInterface;)', False),
    #         ('android.app.Service.onDestroy()', True)
    #     ],
    #     [
    #         ('android.os.RemoteCallbackList.register(Landroid/os/IInterface;)', False),
    #         ('android.os.RemoteCallbackList.unregister(Landroid/os/IInterface;)', False),
    #         ('android.app.Service.onDestroy()', False)
    #     ],
    # ]

    # Media Player Constructor
    # event_list = ['android.media.MediaPlayer.<init>()', 'android.media.MediaPlayer.release()', 'android.app.Activity.onPause()']
    # sequences_with_flag = [
    #     [('android.media.MediaPlayer.<init>()', False), ('android.app.Activity.onPause()', True)],
    #     [('android.media.MediaPlayer.<init>()', False), ('android.media.MediaPlayer.release()', False), ('android.app.Activity.onPause()', False)],
    # ]

    # Media Player Create
    # event_list = ['android.media.MediaPlayer.create(Landroid/content/Context;Landroid/net/Uri;)', 'android.media.MediaPlayer.release()', 'android.app.Activity.onPause()']
    # sequences_with_flag = [
    #     [('android.media.MediaPlayer.create(Landroid/content/Context;Landroid/net/Uri;)', False), ('android.app.Activity.onPause()', True)],
    #     [('android.media.MediaPlayer.create(Landroid/content/Context;Landroid/net/Uri;)', False), ('android.media.MediaPlayer.release()', False), ('android.app.Activity.onPause()', False)],
    # ]

    # Media Recorder Camera
    # event_list = ['android.media.MediaRecorder.start()', 'android.hardware.Camera.lock()', 'android.media.MediaRecorder.stop()']
    # sequences_with_flag = [
    #     [('android.hardware.Camera.lock()', False)], [('android.media.MediaRecorder.start()', False), ('android.hardware.Camera.lock()', True)],
    #     [('android.media.MediaRecorder.start()', False), ('android.media.MediaRecorder.stop()', False)],
    #     [('android.media.MediaRecorder.start()', False), ('android.hardware.Camera.lock()', True), ('android.media.MediaRecorder.stop()', False)],
    #     [('android.media.MediaRecorder.start()', False), ('android.hardware.Camera.lock()', True), ('android.media.MediaRecorder.stop()', False), ('android.hardware.Camera.lock()', False)]
    # ]

    # Lru Cache
    # event_list = ['android.util.LruCache.<init>(I)', 'android.util.LruCache.evictAll()', 'android.app.Activity.onDestroy()']
    # sequences_with_flag = [
    #     [('android.util.LruCache.<init>(I)', False), ('android.app.Activity.onDestroy()', True)],
    #     [('android.util.LruCache.<init>(I)', False), ('android.util.LruCache.evictAll()', False), ('android.app.Activity.onDestroy()', False)],
    # ]

    # WakeLock
    # event_list = ['android.os.PowerManager$WakeLock.acquire()', 'android.os.PowerManager$WakeLock.release()', 'android.app.Activity.onPause()']
    # sequences_with_flag = [
    #     [('android.os.PowerManager$WakeLock.acquire()', False), ('android.app.Activity.onPause()', True)],
    #     [('android.os.PowerManager$WakeLock.acquire()', False), ('android.os.PowerManager$WakeLock.release()', False), ('android.app.Activity.onPause()', False)]
    # ]

    # WifiMulticastLock
    # event_list = ['android.net.wifi.WifiManager$MulticastLock.acquire()', 'android.net.wifi.WifiManager$MulticastLock.release()', 'android.app.Activity.onPause()']
    # sequences_with_flag = [
    #     [('android.net.wifi.WifiManager$MulticastLock.acquire()', False), ('android.app.Activity.onPause()', True)],
    #     [('android.net.wifi.WifiManager$MulticastLock.acquire()', False), ('android.net.wifi.WifiManager$MulticastLock.release()', False), ('android.app.Activity.onPause()', False)],
    #     [('android.app.Activity.onPause()', False)],
    # ]

    # Thread
    # event_list = ['java.lang.Thread.<init>()', 'java.lang.Thread.interrupt()', 'android.app.Service.onDestroy()']
    # sequences_with_flag = [
    #     [('java.lang.Thread.()', False), ('android.app.Service.onPause()', True)],
    #     # [('java.lang.Thread.()', False), ('java.lang.Thread.interrupt()', False), ('android.app.Service.onDestroy()', False)]
    # ]

    # Managed Query
    # event_list = [
    #     'android.app.Activity.managedQuery(Landroid/net/Uri;[Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;Ljava/lang/String;)',
    #     'android.content.ContentResolver.query(Landroid/net/Uri;[Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;Ljava/lang/String;)',
    # ]
    # sequences_with_flag = [
    #     [('android.app.Activity.managedQuery(Landroid/net/Uri;[Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;Ljava/lang/String;)', True)]
    # ]

    # Get Drawable
    # event_list = [
    #     'android.content.res.Resources.getDrawable(I)',
    #     'android.support.v7.widget.AppCompatDrawableManager.getDrawable(I)',
    # ]
    # sequences_with_flag = [
    #     [('android.content.res.Resources.getDrawable(I)', True)]
    # ]

    # List of method FQDN tab delimited (method name is tab separated from package and args).
    # Eg: android.hardware.Camera\topen\t(I), android.app.Activity.\tonPause\t()
    api_methods = format_events(event_list)
    print('> API Methods:', api_methods)
    add_android_method(G, api_methods)
    print()

    # Ricerca eventi
    print('> Searching events')
    if 'MUTATIONS_PATH' in env:
        print('Testing enforcer with mutations')
        test_enforcer(env, enforcer_package, sequences_with_flag, api_methods)
    else:
        run(event_list, sequences_with_flag, api_methods)

if __name__ == "__main__":
    main()
