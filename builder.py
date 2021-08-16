import nodes
import edge
from invalid_model_error import InvalidModelError
class Actor:
    """Represents an actor as defined in sysml. Holds enviromental information."""
    def __init__(self, id, name, perf_env):
        self.id = id
        self.name = name
        self.perv_env = perf_env

def create_node_object(node_info, env, logger, actor=None):
    """Handles creating the correct node based on the type"""
    n_name = node_info['name']
    n_id = node_info['id']
    n_type = node_info['type']
    if n_type == 'uml:CallBehaviorAction':
        if node_info['time_type'] == 'Uniform_Completion_Time':
            print(f'Making UniformTimeNode from {n_name}')
            return nodes.UniformTimeNode(env, logger, n_name, n_id, node_info['perf'], actor, node_info['Min'], node_info['Max'])
        elif node_info['time_type'] == 'Static_Completion_Time':
            print(f'Making StaticTimeNode from {n_name}')
            return nodes.StaticTimeNode(env, logger, n_name, n_id, node_info['perf'], actor, node_info['Time'])
        elif node_info['time_type'] == 'Normal_Completion_Time':
            print(f'Making NormalTimeNode from {n_name}')
            return nodes.NormalTimeNode(env, logger, n_name, n_id, node_info['perf'], actor, node_info['Mean'], node_info['Standard_Deviation'])
        else:
            print(f'Making PerformanceActivity from {n_name}')
            return nodes.PerformanceActivity(env, logger, n_name, n_id, node_info['perf'], actor)
    elif n_type == 'uml:InitialNode':
        print(f'Making InitialNode from {n_name}')
        return nodes.InitialNode(env, logger, n_name, n_id)
    elif n_type == 'uml:ForkNode':
        print(f'Making ForkNode from {n_name}')
        return nodes.ForkNode(env, logger, n_name, n_id)
    elif n_type == 'uml:JoinNode':
        print(f'Making JoinNode from {n_name}')
        return nodes.JoinNode(env, logger, n_name, n_id)
    elif n_type == 'uml:ActivityFinalNode':
        print(f'Making FinalNode from {n_name}')
        return nodes.FinalNode(env, logger, n_name, n_id)
    elif n_type == 'uml:DecisionNode':
        print(f'Making DecisionNode from {n_name}')
        return nodes.DecisionNode(env, logger, n_name, n_id)
    elif n_type == 'uml:AcceptEventAction':
        print(f'Making AcceptSignalNode from {n_name}')
        return nodes.AcceptSignalNode(env, logger, n_name, n_id)
    elif n_type == 'uml:SendSignalAction':
        print(f'Making SendSignalNode from {n_name}')
        return nodes.SendSignalNode(env, logger, n_name, n_id)
    else:
        raise Exception(f'Unknown node type ({n_type}) Encountered.')
    

def create_sim_graph(env, logger, node_info_dict, edge_info_list, actor_infos):
    """Takes in information from the xml loader, and assembles nodes and edges and connects them"""
    # Create nodes with no connections for now
    print('----- Setting up SimGraph... -----')
    node_dict = {}
    actor_dict = {}
    for actor_id in actor_infos:
        actor_dict[actor_id] = Actor(actor_id, actor_infos[actor_id]['name'], actor_infos[actor_id]['env'])
    start_node = None
    for n_id in node_info_dict:
        # Find actor
        if node_info_dict[n_id]['actor_id'] is None:
            this_node_actor = None
        else:
            this_node_actor = actor_dict[node_info_dict[n_id]['actor_id']]
        node_dict[n_id] = create_node_object(node_info_dict[n_id], env, logger, this_node_actor)
        if node_info_dict[n_id]['type'] == 'uml:InitialNode':
            if start_node is None:
                start_node = node_dict[n_id]
            else:
                raise InvalidModelError("Only one InitalNode may be present; multiple found.")
    # Create edge objects, connecting their outgoing nodes and
    # Connecting incoming nodes to them
    edge_list = []
    for e in edge_info_list:
        if e['type'] == 'basic':
            new_edge = edge.Edge(env, logger, e['name'], e['id'], e['probability'])
        elif e['type'] == 'signal':
            new_edge = edge.SignalEdge(env, logger, e['name'], e['id'], e['probability'])
        else:
            raise InvalidModelError(f"Unknown edge type {e['type']}")
        source_id = e['source_id']
        target_id = e['target_id']
        new_edge.set_next_node(node_dict[target_id])
        node_dict[source_id].add_connection(new_edge)
        edge_list.append(new_edge)
        print(f'Added {type(new_edge).__name__}: {e["name"]}')
        if e['probability'] != None:
            print('    Probability:', e['probability'])
    return node_dict, edge_list, start_node, actor_dict