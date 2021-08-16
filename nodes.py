import exec_token
from invalid_model_error import InvalidModelError
import random


class Node(object):
    """Generic Node with no special functions. Expected to be overrided as needed"""
    def __init__(self, env, logger, name, id):
        self.env = env
        self.logger = logger
        self.name = name
        self.id = id
        self.out_edges = []
        self.is_action = False
        
    def add_connection(self, new_edge):
        """Adds a new outgoing edge. This is done post-construction to 
           allow for various graph building orders"""
        if new_edge in self.out_edges:
            raise Exception('Tried to add edge when already in connections!')
        self.out_edges.append(new_edge)
    
    def run(self, token):
        """Handles logic of the exection of a Node"""
        token.log_node_history(self, 0)
        # This is a hacky solution that forces this to be a generator function:
        # TODO: Find a way to declare a generator without any yields
        yield self.env.timeout(0)        
        self.logger.log_sim_event(token.run_id, f"Activating {type(self).__name__} {self.name}")
        self.call_edges(token)
    
    def call_edges(self, token):
        """Handles logic in the calling of edges. May be overrided to implement choosing logic"""
        # self.logger.log_sim_event(token.run_id, f'{self.name} calling edges')
        if self.out_edges == [] or self.out_edges is None:
            raise InvalidModelError(f"Node {self.name} attemped to call edges with no outgoing edges present.")
        for edge in self.out_edges:
            edge.call_next_node(token)
    
    def finish_run(self, token, fail):
        self.logger.log_sim_event(token.run_id, f"Execution completed with token {token.id}")
        self.logger.record_final_stats(token, self.env.now, fail)
        
    def __str__(self):
        return f'Node(name={self.name}, id={self.id})'
      
      
class TimeAndFailNode(Node):
    """Specific kind of node that has takes an amount of time to finish,
       and has a chance of failing. Both are displayed in output"""
    
    def run(self, token):
        """Overrided version that also handles fails and timeouts"""
        node_enter_time = self.env.now
        yield self.env.timeout(0)
        self.logger.log_sim_event(token.run_id, f"Activating Node {self.name}")
        # Calculate action time, action success
        succeeds = self.calc_success()
        action_time = self.calc_time()
        yield self.env.timeout(action_time)
        if succeeds:
            self.logger.log_sim_event(token.run_id, f'Action {self.name} finishes')
        else:
            self.logger.log_sim_event(token.run_id, f'Action {self.name} finishes; FAIL')
        token.log_node_history(self, self.env.now-node_enter_time)
        self.call_edges(token)
    
    def add_fail_edge(self, fail_edge):
        """Gives a SINGLE edge that will be traveled if the action fails.
           If unset the run will prematurley finish instead"""
        if self.fail_edge is not None:
            raise InvalidModelError(f"Node {self.name} has more than one registered failure edge.")
        self.fail_edge = fail_edge
        
    def calc_success(self):
        """Uses env and performance varables to see if action succeeds or not"""
        return True # Base nodes always succeed
    
    def calc_time(self):
        """Calculate action time using performance and other variables"""
        # TODO: maybe make this a constant (defined at runtime)
        return 1 # units undefined like IMPRINT
        
    
class InitialNode(Node):
    def __init__(self, env, logger, name, id):
        super().__init__(env, logger, name, id)
      
      
# TODO: Probably need to give this one special consideration
class ForkNode(Node):
    def __init__(self, env, logger, name, id):
        super().__init__(env, logger, name, id)
        
    def call_edges(self, token):
        num_children = len(self.out_edges)
        if self.out_edges is None:
            raise Exception("Call edges was called without outgoing edges!")
        new_tokens = token.spawn_children_for_fork(num_children)
        for edge, new_token in zip(self.out_edges, new_tokens):
            edge.call_next_node(new_token)
         
         
# To handle joins, incoming edges are 'stored' by adding +1 to their count
# Whenever this is called by an edge and all edges are now >1, one count is consumed from each
# And the next edge is only then called
# This forces the sim to only progress when all paths converge
# But allows for extreme differences in path speed
# big TODO: Do we need to track proper pairs? may need communication with preceding fork node
class JoinNode(Node):
    def __init__(self, env, logger, name, id):
        super().__init__(env, logger, name, id)
        self.waiting_tokens = []
    
    def all_incoming_edges_ready(self):
        for edge in incoming_edges:
            if edge == 0:
                return False
        return True
    
    def run(self, token):
        """Override: same as base but without node history logging (save that for edge caller)"""
        yield self.env.timeout(0)        
        self.logger.log_sim_event(token.run_id, f"Activating {type(self).__name__} {self.name}")
        self.call_edges(token)
    
    def call_edges(self, token):
        if token.fork_infos == []:
            raise InvalidModelError("Join node with no previous fork")
        fork_info = token.fork_infos[-1]
        matches = []
        for other in self.waiting_tokens:
            if fork_info.parent_id == other.fork_infos[-1].parent_id:
                matches.append(other)
        # Go foward with the join nodes
        required_matches = fork_info.num_children-1
        if len(matches) == required_matches:
            # -1 to not count join for every path, but +1 because we need to count it once
            combined_history = fork_info.parent_node_history + token.node_history
            for m in matches:
                self.waiting_tokens.remove(m)
                combined_history += m.node_history  # subtract one so we dont count this join for every incoming
            token.fork_infos.pop()
            new_token = exec_token.ExecToken(token.creation_time, token.run_id, token.fork_infos, combined_history)
            new_token.log_node_history(self, 0)
            self.logger.log_sim_event(token.run_id, f"JoinNode {self.name} Recieved ExecToken {token.id}; all incoming edges ready.")
            super().call_edges(new_token)
        # First node in pair; wait for 2nd
        elif len(matches) < required_matches:
            self.waiting_tokens.append(token)
            self.logger.log_sim_event(token.run_id, f'JoinNode {self.name} Recieved ExecToken {token.id}; not enough matching pairs yet.')
        else:  # somehow we overshot
            raise Exception("Somehow exceeded the number of incoming joins")
            
# Only difference with final is that is also handles the sim ending
class FinalNode(Node):
    def __init__(self, env, logger, name, id):
        super().__init__(env, logger, name, id)
        
    def run(self, token):
        token.log_node_history(self, 0)
        yield self.env.timeout(0)
        self.finish_run(token, fail=False)
        # TODO: Log to env? need x amount to complete?
    # TODO: some override for run() that does cleanup?
    
class DecisionNode(Node):
    def __init__(self, env, logger, name, id):
        super().__init__(env, logger, name, id)
        
    # Returns edge to be followed
    def choose_path(self):
        weights = [e.probability for e in self.out_edges]
        # Check for None values.
        sum_nones = weights.count(None)
        if sum_nones == len(self.out_edges):
            # If all none, then choose with no weighting
            return random.choice(self.out_edges)
        elif sum_nones > 0:
            # If some but not all None, error
            raise InvalidModelError("Must have all probabilites defined, or none")
        else:
            # If none None, chose based on probability
            return random.choices(self.out_edges, weights=weights, k=1)[0]
            
    def call_edges(self, token):
        if self.out_edges is None:
            raise Exception(f"Node {self.name} attemped to call edges with no outgoing edges present.")
        edge_to_follow = self.choose_path()
        self.logger.log_sim_event(token.run_id, f'DecisionNode {self.name} chose path: edge {edge_to_follow.name}')
        edge_to_follow.call_next_node(token)
        
        
class PerformanceActivity(TimeAndFailNode):
    """Node that has access to and is influenced by performance/enviromental data"""
    BASE_TTC = 1
    def __init__(self, env, logger, name, id, performance_info, actor):
        super().__init__(env, logger, name, id)
        self.actor = actor
        self.performance_info = performance_info
        self.is_action = True
    def add_connection(self, new_edge):
        super().add_connection(new_edge)
        if len(self.out_edges) > 1:
            raise InvalidModelError("Actions can only have one outgoing edge")
            # TODO: is this true?
        
    # Uses env and performance varables to see if action succeeds or not
    def calc_success(self):
        return True # TODO
        # This uses actor + performance stuff
        
    # Calculate action time using performance and other variables
    def calc_time(self):
        return PerformanceActivity.BASE_TTC # units undefined like IMPRINT
        # TODO
        # This uses actor + performance stuff


class UniformTimeNode(PerformanceActivity):
    """Action that uses a uniform range for timing"""
    def __init__(self, env, logger, name, id, performance_info, actor, time_min, time_max):
        super().__init__(env, logger, name, id, performance_info, actor)
        if time_max < time_min:
            raise InvalidModelError(f"Max time of Uniform Node {name} is larger than its min time!")
        self.time_min = time_min
        self.time_max = time_max

    def calc_time(self):
        return random.randint(self.time_min, self.time_max)


class StaticTimeNode(PerformanceActivity):
    """Action that uses a static time variable"""
    def __init__(self, env, logger, name, id, performance_info, actor, time_static):
        super().__init__(env, logger, name, id, performance_info, actor)
        self.time_static = time_static
    
    def calc_time(self):
        return self.time_static
        
class NormalTimeNode(PerformanceActivity):
    """Action That uses a normal distribusion for timing"""
    def __init__(self, env, logger, name, id, performance_info, actor, time_mean, time_stdev):
        super().__init__(env, logger, name, id, performance_info, actor)
        self.time_mean = time_mean
        self.time_stdev = time_stdev
        
    def calc_time(self):
        return max(0, round(random.normalvariate(self.time_mean, self.time_stdev)))
        
        
# Sinals are managed by imagining the acceptors are physcially linked to the senders
# Thus, senders outgoing edges all connect to paired acceptors
# This is managed by the graph builder
class SendSignalNode(Node):
    """Sends a signal that may be captured by all signal acceptor nodes. In reality, this acts much like a fork."""
    def __init__(self, env, logger, name, id):
        super().__init__(env, logger, name, id)
        
        
class AcceptSignalNode(Node):
    """Accepts signals coming from SendSignalNodes.
       Functionally a normal edge, only with different logging to make clear this is a signal."""
    def __init__(self, env, logger, name, id):
        super().__init__(env, logger, name, id)