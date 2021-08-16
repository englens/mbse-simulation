import time
import json
import simpy

from logger import Logger
from builder import create_sim_graph
from sim import start_sim
from xml_loader import load_model_data

CONFIG_FILE = 'config.json'
time_for_names = int(time.time())

def load_config(config_file):
    with open(config_file) as f:
        data = json.load(f)
    xmlfile = data['model_file']
    act_name = data['main_activity_name']
    time_between_runs = data['time_between_runs']
    num_runs = data['number_of_runs']
    return xmlfile, act_name, time_between_runs, num_runs
    
def main():
    env = simpy.Environment()
    xmlfile, activity_diagram_name, time_between_runs, num_runs = load_config(CONFIG_FILE)
    log_file = f'Results/Log_{activity_diagram_name}_{time_for_names}.txt'
    results_file = f'Results/Results_{activity_diagram_name}_{time_for_names}.xlsx'
    logger = Logger(env, Logger.LOG_BOTH, results_file, out_file=log_file)
    node_info_dict, edge_info_list, actor_infos = load_model_data(xmlfile, activity_diagram_name)
    node_dict, edge_list, start_node, actor_dict = create_sim_graph(env, logger, node_info_dict, edge_info_list, actor_infos)
    start_sim(env, logger, start_node, num_runs, time_between_runs)
    
if __name__ == "__main__":
    main()