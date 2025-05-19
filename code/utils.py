from datetime import datetime
from time_utils import DatetimeNL
from agent import Agent
import json
import time

def load_json_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def create_agent(filename):
    
    data = load_json_file(filename)
    name = data["name"]
    agent_type = data["agent_type"]
    intermediate_belief = data["intermediate_belief"]
    intermediate_belief_depression = data["intermediate_belief_depression"]
    history = data["history"]
    behavior = data["behavior"]
    description = data["description"]
    situation = data["situation"]
    auto_thought = data["auto_thought"]

    agent = Agent(filename, name, agent_type, intermediate_belief, intermediate_belief_depression, history, behavior, description, auto_thought, situation)
    return agent

def save_agent_json(filename,agent):
    agent_data = {
        "name": agent.name,
        "agent_type": agent.agent_type,
        "description" : agent.description,
        "intermediate_belief": agent.intermediate_belief,
        "intermediate_belief_depression": agent.intermediate_belief_depression,
        "history": agent.history,
        "behavior": agent.behavior,
        "situation": agent.situation,
        "auto_thought": agent.auto_thought,
        "short-term-memory": agent.memory.short_term_memory.whole_memories,
        "long-term-memory": agent.memory.long_term_memory.memory_entries
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(agent_data, f, default=datetime_converter, ensure_ascii=False, indent=4)

    print(f"Agent saved! ShortTerm: {len(agent.memory.short_term_memory.whole_memories)}, LongTerm: {len(agent.memory.long_term_memory.memory_entries)}")

def datetime_converter(o):
        if isinstance(o, datetime):
            return o.strftime("%Y-%m-%d %H:%M:%S")
        raise TypeError(f"Type {type(o)} not serializable")