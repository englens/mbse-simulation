# A token that passes information between exectuion events. 
# Can be updated to hold information as needed
# Ex of use: Fork makes a pair of sibilings that are each needed for the Join to complete
class ExecToken:
    """Holds run-specific enviroment/state information."""
    next_id = 0
    def __init__(self, creation_time, run_id, fork_infos=[], node_history=[]):
        # stores ids for fork/joins ""above"" the current level
        # A ""stack"" -- should be pushed and popped from
        self.id = ExecToken.next_id
        self.run_id = run_id
        ExecToken.next_id+=1
        self.fork_infos = fork_infos
        self.creation_time = creation_time
        self.node_history = node_history
        
    def spawn_children_for_fork(self, num_children):
        """Creates a list of child tokens, with same exec info as parent but parent added to stack"""
        # Add an entry to the fork stack, detailing info from the current point
        new_fork_stack = self.fork_infos[:]
        new_fork_info = ForkInfo(self.id, num_children, self.node_history)
        new_fork_stack.append(new_fork_info)
        # New exec tokens have 0 visited forks, to be added to the parent count by join
        return [ExecToken(self.creation_time, self.run_id, new_fork_stack, []) for _ in range(num_children)]
        # The new nodes will have no history -- we combine their fresh histories with the parent in the join
        
    # The run id is also importiant, but we can get that from self
    def log_node_history(self, node, time_elapsed):
        """Adds a new node to the list of all nodes this node has visited"""
        new_hist = NodeHistory(node.name, node.env.now, time_elapsed, node)
        self.node_history.append(new_hist)
        
class NodeHistory:
    def __init__(self, name, time_entered, time_elapsed, node):
        self.name = name
        self.time_entered = time_entered
        self.time_elapsed = time_elapsed
        self.node = node
        
        
class ForkInfo:
    """Holds the nessesary info to repair fork exectuion tokens at the corresponding join"""
    def __init__(self, parent_id, num_children, parent_node_history):
        self.parent_id = parent_id
        self.num_children = num_children
        self.parent_node_history = parent_node_history