import xml.etree.ElementTree as ET
from invalid_model_error import InvalidModelError
from pprint import pprint
SIM_PROFILE_PREFIX = '{http://www.magicdraw.com/schemas/SimProfile.xmi}'
SIM_ACTION = f'{SIM_PROFILE_PREFIX}SimAction'
SIM_ACTOR_STEREO = f'{SIM_PROFILE_PREFIX}SimActor'
ENVIROMENT_ATTRIBS = ['Cold_Temperature', 'Wind', 'Heat_Temperature',
'Humidity', 'Noise_Decibels', 'Noise_Distance', 'Whole_Body_Vibration_Frequency',
'Whole_Body_Vibration_Magnitude', 'Sleepess_Hours', 'MOPP_Gear', 'Level_A_Gear',
'Weight_Load']
PERF_ATTRIBS = ['Visual_Recognition_Taxon', 'Information_Taxon', 'Fine_Motor_Discrete_Taxon',
'Fine_Motor_Continuous_Taxon', 'Gross_Motor_Light_Taxon', 'Gross_Motor_Heavy_Taxon', 'Oral_Taxon',
'Reading_and_Writing_Taxon', 'Numerical_Analysis_Taxon']

# Shorthands, mainly for brevity
XMI_ID = '{http://www.omg.org/spec/XMI/20131001}id'
XMI_TYPE = '{http://www.omg.org/spec/XMI/20131001}type'
XMI_IDREF = '{http://www.omg.org/spec/XMI/20131001}idref'
SYSML_PROBABILITY = '{http://www.omg.org/spec/SysML/20150709/SysML}Probability'


def get_activities(root, ActivityDiagramName):
    """Returns the main activity and a list of all other activities
       Activities, for our purposes, may be diagrams or objects that actions represent"""
    print('-------- Actvities Found: --------')
    activities = root.findall(f".//packagedElement[@{XMI_TYPE}='uml:Activity']")
    # Activities turn into a "owned_behavior" when place inside another activity
    activities += root.findall(f".//ownedBehavior[@{XMI_TYPE}='uml:Activity']")
    for act in activities:
        print('   ', act.attrib['name'])
    
    main_activity = [a for a in activities if a.attrib['name'] == ActivityDiagramName]
    if len(main_activity) == 0:
        raise InvalidModelError('err: No diagram with supplied name found')
    if len(main_activity) > 1:
        raise InvalidModelError('err: Multiple diagrams with supplied name found.')
    main_activity = main_activity[0]
    
    # getting the name of the Main (entry) activity diagram
    print('------------------------------')
    print('Main Activity Found: ', main_activity.attrib['name'])   # should be same as ActivityDiagramName

    # Setting up other activities and Abstractions of them
    all_activities = {}
    for a in activities:
        all_activities[a.attrib[XMI_ID]] = a
    
    return main_activity, all_activities
    

def get_actors(root):
    """Searches for actor block stereotypes, and scans for info from them
       This creates the exclusive list of allocatable actors"""
    print(' -------- Reading Actor Blocks --------')
    canidate_stereotypes = root.findall(f".//{SIM_ACTOR_STEREO}")
    # Ensure we have only one block -- TODO: Can we do this per-model?
    if len(canidate_stereotypes) == 0:
        raise InvalidModelError("No Actor Blocks Found!")
    actor_infos = {}
    for actor_stereo in canidate_stereotypes:
        # Find Block name by cross-referencing the id
        base_id = actor_stereo.attrib['base_Class']
        print('BASEID:', base_id)
        canidate_blocks = root.findall(f".//packagedElement[@{XMI_ID}='{base_id}']")
        if len(canidate_blocks) == 0:
            raise InvalidModelError("No Enable Block found for given stereotype!")
        if len(canidate_blocks) > 1:
            raise InvalidModelError("More than one Enable Block for given stereotype, not sure which one to use. (This is a weird error)")
        actor_block = canidate_blocks[0]
        try:
            actor_name = actor_block.attrib['name']
        except AttributeError:
            raise AttributeError('No name set in actor block! Please give a unique name')
        print('ACTOR NAME:', actor_name)
        # Set up dict for the attributes
        actor_dict = {}
        actor_dict['env'] = {}
        actor_dict['name'] = actor_name
        actor_dict['id'] = base_id
        for attrib in ENVIROMENT_ATTRIBS:
            try:
                val = actor_stereo.attrib[attrib]
            except KeyError:
                val = 'N/A'
            actor_dict['env'][attrib] = val
        for attrib in ENVIROMENT_ATTRIBS:
            print(f"{attrib} Environment Value == {actor_dict['env'][attrib]}")
        actor_infos[actor_dict['id']] = actor_dict
    return actor_infos
    
    
def get_actor_allocations(root, actor_infos, all_activities):
    """With our list of actors, scan for allocations using them
       Uses allocations to setup activities"""
    activity_allocations = {} # keyed by activity id
    print('-------- Actor Allocations Found: --------')
    abstractions = root.findall(f".//packagedElement[@{XMI_TYPE}='uml:Abstraction']")
    for actor_id in actor_infos:
        # index 0 is client, 1 is supplier
        # list of activity ids
        associated_clients = [a.find('client').attrib[XMI_IDREF] for a in abstractions if a.find('supplier').attrib[XMI_IDREF]==actor_id]
        for activ_id in all_activities:
            if activ_id in associated_clients:
                activity_allocations[activ_id] = actor_id
                print(all_activities[activ_id].attrib['name'], 'allocated to: ', actor_infos[actor_id]['name'])
    return activity_allocations


def get_nodes(activity, all_activities, activity_allocations):
    """Returns a list of nodes in the main activity
       Extracts only information from the node xml itself
       Also Grabs signal information while we're at it"""
    # Node dict is dict of dicts
    # each keyed by ID
    node_xmls = activity.findall('node')
    node_info_dict = {}
    accept_signal_connections = []  # reciver_id, event_id pairs
    send_signal_connections = []  # sender_id, signal_id pairs
    print('-------- Nodes found: --------')
    for n in node_xmls:
        node_info = {}
        node_info['type'] = n.attrib[XMI_TYPE]
        try:
            behavior_id = n.attrib['behavior']
            actor_id = activity_allocations[behavior_id]
        except KeyError:
            if node_info['type'] == 'uml:CallBehaviorAction':
                # Actions need an actor in the current sim model.
                # TODO: Consider letting base (or only non-sim) actions have no actor
                try:
                    # If the base action is allocated, use that.
                    actor_id = activity_allocations[activity.attrib[XMI_ID]]
                    behavior_id = None  # No behavior in this case; ignore it for naming
                except KeyError:
                    # Otherwise, error.
                    raise InvalidModelError(f'{node_info["type"]} Not Allocated. All Performance Actions must be Allocated to an Actor, or be in an Activity that itself is allocated.')
            # else, its not a perf action so behavior/actor is not relevant
            behavior_id = None
            actor_id = None
        # Give The node a name, using a priority based on whats availible:
        #     First try the actual nodes name
        #     Then the activity it represents, if it exists
        #     Finally default to the node type
        try:
            node_info['name'] = n.attrib['name']
        except KeyError:
            if behavior_id is not None:
                node_info['name'] = all_activities[behavior_id].attrib['name']
            else:
                node_info['name'] = n.attrib[XMI_TYPE]
        node_info['id'] = n.attrib[XMI_ID]
        # Special Cases for Signal stuff
        if node_info['type'] == 'uml:AcceptEventAction':
            trigger = n.find('trigger')
            event_id = trigger.attrib['event']
            accept_signal_connections.append({'reciver_id': node_info['id'], 'event_id': event_id})
        if node_info['type'] == 'uml:SendSignalAction':
            try:
                signal_id = n.attrib['signal']
            except KeyError:
                raise InvalidModelError(f"Signal Sender {node_info['name']} has no registered signal.")
            send_signal_connections.append({'sender_id': node_info['id'], 'signal_id': signal_id})
        node_info['actor_id'] = actor_id
        if actor_id is None:
            print(f"{node_info['name']}, Allocated to actor {node_info['actor_id']}")
        else:
            print(f"{node_info['name']}, Not allocated to an actor")
        node_info['time_type'] = None  # to be set later
        node_info_dict[node_info['id']] = node_info
    return node_info_dict, accept_signal_connections, send_signal_connections
    
    
def apply_node_stereotypes(root, node_info_dict):
    """Adds performance and other info from stereotypes to the node info dict"""
    print('-------- Applying Node Stereotypes --------')
    canidate_stereotypes = root.findall(f".//{SIM_ACTION}")
    # Assemble lookup based on 'base_CallBehaviorAction', the id of the applied object
    stereo_lookup_dict = {}
    for c in canidate_stereotypes:
        stereo_lookup_dict[c.attrib['base_CallBehaviorAction']] = c

    # For each node in nodedict, look for stereotype with its id
    for n_id in node_info_dict:
        try:
            stereo = stereo_lookup_dict[n_id]
        except KeyError:
            # if none exists, its not a performance node    
            print(node_info_dict[n_id]['name'], 'not a performance action; Skipping')
            # TODO: Handle raw actions that aernt perf? (error)
            node_info_dict[n_id]['PSF_Enable'] = False
            continue
            
        # Loop thru every perf data, add to node's dict if specified (lots of try blocks)
        n_name = node_info_dict[n_id]['name']
        print(f'{n_name}:')
        try:
            node_info_dict[n_id]['TTC'] = stereo.attrib['Static_Time_To_Complete']
        except KeyError:
            node_info_dict[n_id]['TTC'] = None
        print(f'    TTC == {node_info_dict[n_id]["TTC"]}')
        try:
            node_info_dict[n_id]['PerformanceEnable'] = stereo.attrib['PSF_Enable']
        except KeyError:
            node_info_dict[n_id]['PerformanceEnable'] = None
        print(f'    PerformanceEnable == {node_info_dict[n_id]["PerformanceEnable"]}')
        node_info_dict[n_id]['perf'] = {}
        for attrib in PERF_ATTRIBS:
            try:
                node_info_dict[n_id]['perf'][attrib] = int(stereo.attrib[attrib])
                print(f'    {attrib} == {node_info_dict[n_id]["perf"][attrib]}')
            except KeyError:
                print(f'    ', attrib, 'undefined, setting to 0')
                node_info_dict[n_id]['perf'][attrib] = 0
            except ValueError as e:
                raise InvalidModelError(f'{n_name}:', attrib, 'not an Int')
    return node_info_dict
    
        
def apply_time_stereotype(root, node_info_dict, time_name, time_params):
    """Applies the stereotype of given timing type"""
    stereo_name = f'{SIM_PROFILE_PREFIX}{time_name}'
    print(f'-------- Applying {time_name} Stereotypes --------')
    canidate_stereotypes = root.findall(f".//{stereo_name}")
    # Assemble lookup based on 'base_CallBehaviorAction', the id of the applied object
    stereo_lookup_dict = {}
    for c in canidate_stereotypes:
        stereo_lookup_dict[c.attrib['base_CallBehaviorAction']] = c
        
    # For each node in nodedict, look for stereotype with its id
    for n_id in node_info_dict:
        try:
            stereo = stereo_lookup_dict[n_id]
        except KeyError:
            continue
        print(node_info_dict[n_id]['name'])
        node_info_dict[n_id]['time_type'] = time_name
        for p in time_params:
            try:
                node_info_dict[n_id][p] = int(stereo.attrib[p])
                print('   ', f'{p}:', node_info_dict[n_id][p])
            except KeyError:
                raise InvalidModelError(f'{time_name} has invalid/unset arg {p}.')
    return node_info_dict
    
    
def apply_all_time_stereotypes(root, node_info_dict):
    """Applies the time stereotypes for all time types"""
    name = 'Uniform_Completion_Time'
    time_args = ['Min', 'Max']
    node_info_dict = apply_time_stereotype(root, node_info_dict, name, time_args)
    name = 'Static_Completion_Time'
    time_args = ['Time']
    node_info_dict = apply_time_stereotype(root, node_info_dict, name, time_args)
    name = 'Normal_Completion_Time'
    time_args = ['Mean', 'Standard_Deviation']
    node_info_dict = apply_time_stereotype(root, node_info_dict, name, time_args)
    return node_info_dict
    
    
def get_edge_probabilities(root, activity):
    """Extracts a list of probabtilites to be later coupled with edges"""
    print('-------- Edge Probabilites Found: --------')
    edge_xmls = activity.findall('edge')
    edge_probabilites = {}
    probability_xmls = root.findall(f".//{SYSML_PROBABILITY}")
    for p in probability_xmls:
        try:
            prob = p.attrib['probability']
        except KeyError:
            print('Edge Probability found with no value supplied; skipping')
            continue
        e_id = p.attrib['base_ActivityEdge']
        edge_probabilites[e_id] = prob
        print('Probability', prob, 'found for edge', e_id)
    return edge_probabilites
    
   
def get_edges(activity, edge_probabilites):
    """Return a list of edges with info from the base xml
    edict: id, name, probability, source_id, target_id, type"""
    edge_xmls = activity.findall('edge')
    edge_info_list = []
    print('-------- Edges found: --------')
    for e in edge_xmls:
        new_edge = {}
        new_edge['source_id'] = e.attrib['source']
        new_edge['target_id'] = e.attrib['target']
        try:
            new_edge['name'] = e.attrib['name']
        except KeyError:
            new_edge['name'] = e.attrib[XMI_TYPE] 
        new_edge['id'] = e.attrib[XMI_ID]
        try:
            new_edge['probability'] = float(edge_probabilites[new_edge['id']])
        except ValueError as e:
            print(new_edge['name'], 'has probability value un-convertable to float')
        except KeyError:
            new_edge['probability'] = None
        new_edge['type'] = 'basic'
        print('Edge found: from', new_edge['source_id'], 'to', new_edge['target_id'])
        edge_info_list.append(new_edge)
    return edge_info_list
    
    
def get_signals(root):
    """grab list of signals (with name info mainly)"""
    print('-------- Signals Found: --------')
    signal_xmls = root.findall(f".//packagedElement[@{XMI_TYPE}='uml:Signal']")
    nested_signal_xmls = root.findall(f".//nestedClassifier[@{XMI_TYPE}='uml:Signal']")
    signal_xmls += nested_signal_xmls
    signals = {}
    for s in signal_xmls:
        id = s.attrib[XMI_ID]
        try:
            name = s.attrib['name']
        except KeyError:
            name = s.attrib[XMI_ID]
        signals[id] = {'id':id, 'name':name}
    return signals
    
    
def get_signal_events(root, signals):
    """Grab list of signal events (not all them are nessesarily used)"""
    signal_events = {} # keyed by id
    print('-------- Signal Events Found: --------')
    signal_event_xmls = root.findall(f".//packagedElement[@{XMI_TYPE}='uml:SignalEvent']")
    for s in signal_event_xmls:
        id = s.attrib[XMI_ID]
        signal_id = s.attrib['signal']
        signal_name = signals[signal_id]['name']
        signal_events[id] = {'id':id, 'signal_id':signal_id, 'signal_name':signal_name}
        print(f"id:{id}, signal_id:{signal_id}")
    return signal_events


def assemble_signal_edges(accept_signal_connections, send_signal_connections, signal_events):
    """Connects signals and recivers to form signal edges"""
    signal_edge_info_list = []
    print('-------- Signal Edges: --------')
    for a in accept_signal_connections:
        e_id = a['event_id']
        s_id = signal_events[e_id]['signal_id']
        signal_name = signal_events[e_id]['signal_name']
        for s in send_signal_connections:
            if s['signal_id'] == s_id:
                new_edge = {'id': e_id,
                            'name': signal_name,
                            'probability': None,
                            'source_id' : s['sender_id'],
                            'target_id' : a['reciver_id'],
                            'type': 'signal'}
                print('SignalEdge found: ', f'"{new_edge["name"]}", from', new_edge['source_id'], 'to', new_edge['target_id'])
                signal_edge_info_list.append(new_edge)
    return signal_edge_info_list
    
    
def load_model_data(xmlfile, ActivityDiagramName):
    """Extracts all relevant data from the model and organizes it into several containers"""
    tree = ET.parse(xmlfile)
    root = tree.getroot()
    activity, all_activities = get_activities(root, ActivityDiagramName)
    # Actors
    actor_infos = get_actors(root)
    activity_allocations = get_actor_allocations(root, actor_infos, all_activities)
    # Nodes
    node_info_dict, accept_signal_connections, send_signal_connections = get_nodes(activity, all_activities, activity_allocations)
    node_info_dict = apply_node_stereotypes(root, node_info_dict)
    node_info_dict = apply_all_time_stereotypes(root, node_info_dict)
    # Edges
    edge_probabilites = get_edge_probabilities(root, activity)
    edge_info_list = get_edges(activity, edge_probabilites)
    
    signals = get_signals(root)
    signal_events = get_signal_events(root, signals)
    signal_edge_info_list = assemble_signal_edges(accept_signal_connections, send_signal_connections, signal_events)
    # combine edge lists
    edge_info_list = edge_info_list + signal_edge_info_list
    return node_info_dict, edge_info_list, actor_infos