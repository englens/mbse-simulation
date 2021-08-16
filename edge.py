class Edge(object):
    """Basic edge that calls the next node when activated"""
    def __init__(self, env, logger, name, id, probability=None, next_node=None):
        self.env = env
        self.logger = logger
        self.name = name
        self.id = id
        self.probability = probability
        self.next_node = next_node
        
    # This is so we can create the objects then connect them at a latter time
    def set_next_node(self, next_node):
        self.next_node = next_node
        
    def call_next_node(self, token):
        if self.next_node is None:
            raise Exception(f"Edge {self.name}'s next node called without one being set.")
        self.logger.log_sim_event(token.run_id, f"Edge {self.name} followed, calling next node {self.next_node.name}.")
        self.env.process(self.next_node.run(token))
        
    def __str__(self):
        return f'Edge(name={self.name}, id={self.id})'
        
    
class SignalEdge(Edge):
    """A virtual edge not represented by the sysml graph, but represents control flow from a signal sender to reciver"""
    # The only difference is how its logged
    def call_next_node(self, token):
        if self.next_node is None:
            raise Exception(f"Edge {self.name}'s next node called without one being set.")
        self.logger.log_sim_event(token.run_id, f"SignalEdge {self.name} followed, Calling Acceptor {self.next_node.name}. TOKEN={token.id}")
        self.env.process(self.next_node.run(token))