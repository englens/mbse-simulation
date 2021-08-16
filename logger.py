import csv
import pandas as pd

class Logger:
    """Central logging system for console printing and/or file logging"""
    LOG_PRINT = 0
    LOG_FILE = 1
    LOG_BOTH = 2
    def __init__(self, env, log_mode, results_file, out_file=''):
        self.log_mode = log_mode
        self.env = env
        self.summary_stats = []
        self.run_details = {}
        self.results_file = results_file
        if log_mode == Logger.LOG_PRINT:
            self.log = self.log_print
        elif log_mode == Logger.LOG_FILE:
            self.log = self.log_file
            if out_file == '':
                raise Exception("No Log File given.")
            self.out_file = out_file
        elif log_mode == Logger.LOG_BOTH:
            self.log = self.log_both
            if out_file == '':
                raise Exception("No Log File given.")
            self.out_file = out_file
        
    def log_print(self, msg, log_time=True):
        """log to the console"""
        if log_time:
            print(f'[{self.env.now}]: {msg}')
        else:
            print(msg)
            
    def log_file(self, msg, log_time=True):
        """log to a file"""
        with open(self.out_file, 'a') as f:
            if log_time:
                f.write(f'[{self.env.now}]: {msg}\n')
            else:
                f.write(msg + '\n')
    
    def log_both(self, msg, log_time=True):
        """Log to both the console and a file"""
        self.log_file(msg, log_time)
        self.log_print(msg, log_time)
    
    def log_sim_event(self, run_id, msg):
        """Adds the run id to a log. This distinguishes runs in the log"""
        self.log(f'Run {run_id}: ' + msg)
        
    # Todo: more stats, full pass/fail support, better ordering (filter non-actions)
    # also todo: not getting correct numbers -- theres a bug somewhere with counting
    def record_final_stats(self, token, end_time, did_fail):
        """Records the list of stats to be recorded in the results file.
           This is called when each run finishes."""
        record_dict = {
            'run_id': token.run_id,
            'start_time': token.creation_time,
            'end_time': end_time,
            'total_time_elapsed': end_time-token.creation_time,
            'num_nodes_visited': len(token.node_history)
        }
        n_ids = self.get_visited_node_ids(token)
        this_run_details = []
        for nid in n_ids:
            this_run_details.append(self.count_node_statistics(token, nid))
        self.run_details[token.run_id] = this_run_details
        self.summary_stats.append(record_dict)
    
    def get_visited_node_ids(self, token):
        """Returns list of every node visited in this token's history"""
        ids = []
        for node in token.node_history:
            if node.node.id not in ids:
                ids.append(node.node.id)
        return ids
        
    def count_node_statistics(self, token, node_id):
        """count up the various statistics for a specific node"""
        count = 0
        total_time = 0
        for n in token.node_history:
            if n.node.id == node_id:
                n_name = n.name
                total_time += n.time_elapsed
                count += 1
        n_dict = {'node': n_name,
                  'Total Time': total_time, 
                  'Times Visited': count}
        return n_dict
        
    def log_final_stats(self):
        """Prints the stored run stats"""
        if len(self.summary_stats) == 0:
            return  # this should never happen but it would make the log look weird if it did
        self.log("Recording final run statistics", log_time=False)
        self.summary_stats.sort(key=lambda x: x['run_id'])
        with pd.ExcelWriter(self.results_file) as writer:
            df = pd.DataFrame(self.summary_stats)
            df.to_excel(writer, sheet_name='Summary', index=False)
            for run_id in sorted(self.run_details):
                df = pd.DataFrame(self.run_details[run_id])
                df.to_excel(writer, sheet_name=f'Run {run_id}', index=False)
                