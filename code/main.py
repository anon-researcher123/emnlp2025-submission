import concurrent.futures
from datetime import datetime
from time_utils import DatetimeNL
from agent import Agent
from memory import Memory  
import json
import time
import utils
from datetime import timedelta

from location import Location

loc = Location.get_instance()

from conversation import Conversation

file_name1 = "./insomnia_agent/Ethan4.json"

file_name2 = "./insomnia_agent/Zane.json"  
game_time = DatetimeNL.accelerated_time()
print(game_time)
turns = 200
start_date = DatetimeNL.get_date_nl(game_time).split(" ")[2]

agent1 = utils.create_agent(file_name1)
agent2 = utils.create_agent(file_name2)
all_agents = []
all_agents.append(agent1)
all_agents.append(agent2)

def run_sim(agent, all_agents, curr_time, start_date):

    print("")
    print(f"Agent {agent.name} start: ", curr_time)

    if start_date != DatetimeNL.get_date_nl(curr_time).split(" ")[2]:
        print(start_date, DatetimeNL.get_date_nl(curr_time).split(" ")[2])
        print("next day")
        init_plan = agent.plan.initial_plan(curr_time, max_attempts=10)
        hourly_plan = agent.plan.recursively_decompose_plan(init_plan, curr_time, time_interval="1_hour", max_attempts=20)
        half_plan = agent.plan.recursively_decompose_plan(hourly_plan, curr_time, time_interval="30_minute", max_attempts=20)
        quarter_plan = agent.plan.recursively_decompose_plan(half_plan, curr_time, time_interval="15_minute", max_attempts=20)
        start_date = DatetimeNL.get_date_nl(curr_time).split(" ")[2]
        
    loc.get_agent_next_location(agent, max_attempts=5)
    time.sleep(15)
    conv = Conversation(all_agents)
    conv.conversation_trigger(agent)

    agent.plan.plan_update()

    end = DatetimeNL.accelerated_time()
    print(f"Agent {agent.name} end: ", end)

    elapsed_time = end - curr_time
    print(elapsed_time)

    time_turn = timedelta(hours=0, minutes=15, seconds=0)
    if elapsed_time <= time_turn:
        diff_sec = (time_turn - elapsed_time).total_seconds()
        print("waiting for 15_min", diff_sec/3)
        time.sleep(diff_sec/3)

    curr_time = DatetimeNL.accelerated_time()
    utils.save_agent_json(f"./output/{agent.name}_{curr_time.strftime('%Y-%m-%d_%H-%M-%S')}.json", agent)
    
    return curr_time, start_date

print("len ", len(all_agents))

if len(all_agents) == 1:
    for i in range(turns):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future1 = executor.submit(run_sim, all_agents[0], all_agents, game_time, start_date)
            game_time, start_date = future1.result()

        print("Time: ", game_time, ", Turns: ", i)
        if i == turns:
            break

else:
    for i in range(turns):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future1 = executor.submit(run_sim, all_agents[0], all_agents, game_time, start_date)
            future2 = executor.submit(run_sim, all_agents[1], all_agents, game_time, start_date)

            concurrent.futures.wait([future1, future2])

            game_time1, start_date1 = future1.result()
            game_time2, start_date2 = future2.result()
            game_time = max(game_time1, game_time2)
            start_date = max(start_date1, start_date2)

        print("Time: ", game_time, ", Turns: ", i)
        if i == turns:
            break
