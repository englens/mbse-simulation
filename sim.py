import exec_token

def loop_create_runs_process(env, logger, start_node, num_runs, run_delay):
    """Creates new runs periodically, insead of all at once
       This may make for cleaner logs"""
    for run_id in range(num_runs):
        logger.log(f"Beginning run {run_id}.")
        yield env.process(start_node.run(exec_token.ExecToken(creation_time=env.now, run_id=run_id)))
        yield env.timeout(run_delay)
        
        
def create_many_runs(env, logger, start_node, num_runs):
    """Makes many runs at once. Will cause a messy output log."""
    loop_create_runs_process(env, logger, start_node, num_runs, run_delay=0)
    
    
def start_sim(env, logger, start_node, num_runs, time_between_runs):
    """Start up the sim with the start node"""
    logger.log('Beginning Sim', log_time=False)
    env.process(loop_create_runs_process(env, logger, start_node, num_runs, time_between_runs))
    env.run()
    logger.log_final_stats()