from short_term_memory import ShortTermMemory
from long_term_memory import LongTermMemory
from memory_retrieval import MemoryRetrieval

class Memory:
    def __init__(self, memory_path, persona=None):
        self.short_term_memory = ShortTermMemory(memory_path, persona=persona)
        self.long_term_memory = self.short_term_memory.long_term_memory
        self.memory_retrieval = MemoryRetrieval(memory_path, persona=persona)


    def add_to_memory(self, memory_type, description, timestamp):
        self.short_term_memory.add_to_memory(memory_type, description, timestamp)

    def retrieve_memories(self, query, top_n=5):
        return self.memory_retrieval.retrieve_top_memories(query)["top_10_retrieved"][:top_n]
    
    def retrieve_longterm_memories(self, query, top_n=5):
        return self.memory_retrieval.retrieve_top_memories(query)["long_term_retrieved"][:top_n]

    def calculate_importance(self, description):
        return self.short_term_memory.calculate_poignancy(description)

    def trigger_reflection(self, poignancy, emotion_score):
        self.short_term_memory.check_reflection_trigger(poignancy, emotion_score)

    def add_reflection(self, reflection_entry):
        self.long_term_memory.add_reflection(reflection_entry)

    def reset_chat_set(self):
        self.short_term_memory.reset_chat_set()


