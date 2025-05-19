import json
import os

class LongTermMemory:
    def __init__(self, memory_path):
        self.memory_path = memory_path
        self.reflection_callback = None
        self.current_reflection = None

        self.load_existing_data()

        with open(memory_path, 'r', encoding='utf-8') as file:
            memory_data = json.load(file)
            self.memory_entries = memory_data.get("long-term-memory", [])

            if isinstance(self.memory_entries, dict):
                self.memory_entries = list(self.memory_entries.values())

    def load_existing_data(self):
        try:
            if os.path.exists(self.memory_path):
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    self.memory_entries = existing_data.get("long-term-memory", [])
            else:
                self.memory_entries = []

        except (FileNotFoundError, json.JSONDecodeError):
            self.memory_entries = []
            print("No existing Long-Term Memory found. Initializing empty storage.")

    def add_reflection(self, reflection_entry):
        self.memory_entries.append(reflection_entry)
        print(f"Reflection added! Current LongTermMemory count: {len(self.memory_entries)}")
        
        self.current_reflection = reflection_entry
        if self.reflection_callback:
            self.reflection_callback(reflection_entry)
    
    def get_current_reflection(self):
        return self.current_reflection["description"]

    def set_reflection_callback(self, callback):
        self.reflection_callback = callback


    def get_max_longterm_node_id(self):
        if not self.memory_entries: 
            return 0

        try:
            max_id = max(int(entry["node_id"].split("-")[0]) for entry in self.memory_entries)
            return max_id
        except Exception as e:
            print(f"Error getting max node_id from Long-Term Memory: {e}")
            return 0 


