import numpy as np
from memory import Memory 

class Persona:
    def __init__(self, name, agent_type, intermediate_belief, intermediate_belief_depression, history, behavior, memory, llm, description):
        self.name = name
        self.agent_type = agent_type
        self.intermediate_belief = intermediate_belief
        self.intermediate_belief_depression = intermediate_belief_depression
        self.history = history
        self.behavior = behavior
        self.memory = memory 
        self.llm = llm  
        self.description = description

    def get_agent_information(self, aspect="core characteristics"):
        i = -1
        while True:
            memory_type = self.memory.short_term_memory.whole_memories[i]["memory_type"]
            
            if memory_type == "event":
                current_memory = self.memory.short_term_memory.whole_memories[i]["description"]
                print("current_memory (event):", current_memory)
                break

            elif memory_type == "chat":
                current_memory = self.memory.long_term_memory.memory_entries[i]["description"]
                print("current_memory (chat):", current_memory)
                break

            else:
                print("Wrong memory format:", memory_type)
                i -= 1


        memory_query = f"{self.name}'s {aspect}"
        memory_statements_dict = self.memory.retrieve_memories(current_memory)
        memory_statements = [memory.get('description') for memory in memory_statements_dict]
        
        print("related memories: ", memory_statements)

        if not memory_statements:
            return f"No relevant memories found for {aspect}."
        
        joined_memory_statements = "\n- ".join(memory_statements)
        prompt = f"""How would one describe {memory_query} given the following statements?\n- {joined_memory_statements}"""
        return self.llm.get_llm_response(prompt)
    
    def get_persona(self):
        core_characteristics = self.get_agent_information(aspect="core characteristics")
        feelings = self.get_agent_information(aspect="feeling about his recent progress in life")

        description = f"""
        Name: {self.name}
        Background: {self.history}
        Characteristic: {core_characteristics}
        Recent feeling: {feelings}
        """

        return description
    
    def get_agent_information_after_reflection(self, reflection, aspect="core characteristics"):
        i = -1
        while True:
            memory_type = self.memory.short_term_memory.whole_memories[i]["memory_type"]
            
            if memory_type == "event":
                current_memory = self.memory.short_term_memory.whole_memories[i]["description"]
                break

            elif memory_type == "chat":
                current_memory = self.memory.long_term_memory.memory_entries[i]["description"]
                break

            else:
                i -= 1


        memory_query = f"{self.name}'s {aspect}"
        memory_statements_dict = self.memory.retrieve_longterm_memories(current_memory)
        memory_statements = [memory.get('description') for memory in memory_statements_dict]

        if not memory_statements:
            return f"No relevant memories found for {aspect}."
        
        joined_memory_statements = "\n- ".join(memory_statements)
        prompt = f"""How would one describe {memory_query} given the following statements?\n- Current Thought: {reflection} \n Past Memories: {joined_memory_statements} \n Previous_Persona: {self.description}"""
        return self.llm.get_llm_response(prompt)
    
    def get_persona_after_reflection(self, reflection):
        core_characteristics = self.get_agent_information_after_reflection(reflection, aspect="core characteristics")
        feelings = self.get_agent_information_after_reflection(reflection, aspect="feeling about his recent progress in life")

        description = f"""
        Name: {self.name}
        Background: {self.history}
        Characteristic: {core_characteristics}
        Recent feeling: {feelings}
        """

        return description    

    def get_other_information(self, question):
        i = -1
        while True:
            memory_type = self.memory.short_term_memory.whole_memories[i]["memory_type"]
            
            if memory_type == "event":
                current_memory = self.memory.short_term_memory.whole_memories[i]["description"]
                print("current_memory (event):", current_memory)
                break

            elif memory_type == "chat":
                current_memory = self.memory.long_term_memory.memory_entries[i]["description"]
                print("current_memory (chat):", current_memory)
                break

            else:
                print("Wrong memory format:", memory_type)
                i -= 1


        memory_statements_dict = self.memory.retrieve_memories(current_memory)
        memory_statements = [memory.get('description') for memory in memory_statements_dict]
        
        print("related memories: ", memory_statements)

        if not memory_statements:
            return f"No relevant memories found."
        
        joined_memory_statements = "\n- ".join(memory_statements)
        print(joined_memory_statements)
        prompt = f"""Answer the question considering provided character's personality and memories
                Personality: {self.description}
                Memories: {joined_memory_statements}
                Question: {question}
                Answer:"""
        return self.llm.get_llm_response(prompt)

    def test_persona(self):
        joined_memory_statements = """ Theodore: It sounds like you're acknowledging the weight of these feelings and considering a gentle start by taking a bit of time for self-reflection. How do you feel about making this space for yourself, even if it's a quiet, initial step?,
        brief session recognizing personal boundaries  
        supportive discussion with friend or therapist
        seek clarity, light self-assessment
        lunch, gentle reflection
        """
       
        prompt = f"""How would one describe core characteristic given the following statements?\n- {joined_memory_statements}"""
        return self.llm.get_llm_response(prompt)