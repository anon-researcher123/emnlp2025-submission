import yaml
import networkx as nx
import threading
from typing import List
from agent import Agent 

class Location:
    _instance = None  

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"): 
            return
        self._initialized = True
        
        self.world_file = '../data/world_client_friend.yaml'
        self.graph = nx.Graph()
        self.agent_locations = {}
        self.lock = threading.Lock()
        self.load_world()

    def load_world(self):
        with open(self.world_file, 'r', encoding='utf-8') as file:
            world_data = yaml.safe_load(file)
        
        for location in world_data.get("World", []):
            if isinstance(location, dict): 
                for place, sub_places in location.items():
                    self.graph.add_node(place, type="location")
                    self._add_sub_places(place, sub_places)
            elif isinstance(location, str):
                self.graph.add_node(location, type="location")

        for agent_entry in world_data.get("Agents", []):
            if isinstance(agent_entry, dict):  
                for agent_name, location in agent_entry.items():
                    self.graph.add_node(agent_name, type="agent")
                    self.graph.add_edge(agent_name, location)
                    self.agent_locations[agent_name] = location
    
    def _add_sub_places(self, parent, sub_places):
        if isinstance(sub_places, list):
            for item in sub_places:
                if isinstance(item, str):
                    self.graph.add_node(item, type="sub_location")
                    self.graph.add_edge(parent, item)
                elif isinstance(item, dict):
                    for sub_place, nested_places in item.items():
                        self.graph.add_node(sub_place, type="sub_location")
                        self.graph.add_edge(parent, sub_place)
                        self._add_sub_places(sub_place, nested_places)
    
    def get_agent_location(self, agent: Agent) -> str:
        return self.agent_locations.get(agent.name, None)
    
    def move_agent(self, agent: Agent, new_location: str):
        with self.lock:
            if agent.name in self.agent_locations:
                old_location = self.agent_locations[agent.name]
                self.graph.remove_edge(agent.name, old_location)
            
            self.graph.add_edge(agent.name, new_location)
            self.agent_locations[agent.name] = new_location
    
    def get_possible_locations(self) -> List[str]:
        possible_locations = []

        for node in self.graph.nodes:
            if self.graph.nodes[node].get("type") == "location":
                sub_places = [neighbor for neighbor in self.graph.neighbors(node)
                              if self.graph.nodes[neighbor].get("type") == "sub_location"]
                if sub_places:
                    possible_locations.extend(sub_places)
                else:
                    possible_locations.append(node)

        return possible_locations

    def get_agent_next_location(self, agent: Agent, max_attempts=5) -> List[str]:
        current_location = self.get_agent_location(agent)
        possible_locations = self.get_possible_locations()
        next_plan = agent.plan.get_agent_action() 
        print(f"{agent.name}: ", next_plan)
        
        if not possible_locations:
            return [current_location]
        
        attempts = 0
        chosen_location = current_location
        
        while attempts < max_attempts:
            prompt = f"""
            {agent.name} is currently in {current_location}.
            Their next plan is: {next_plan}.
            They can either stay in the same location or move to a new one.
            Based on this plan, select the most suitable location from the options below:
            {possible_locations}
            
            Just select in option
            """
            generated_location = str(agent.llm.get_llm_response(prompt)).strip()
            
            if generated_location in possible_locations:
                chosen_location = generated_location
                break
            attempts += 1

        self.move_agent(agent, chosen_location)
        return [chosen_location]

    def display_world(self):
        print("World Graph Nodes:")
        print(self.graph.nodes(data=True))
        print("\nWorld Graph Edges:")
        print(self.graph.edges())

    def get_visible_agents(self, agent: Agent) -> List[str]:
        agent_location = self.get_agent_location(agent)
        if not agent_location:
            return []
        
        return [other_agent for other_agent, loc in self.agent_locations.items() if loc == agent_location and other_agent != agent.name]
