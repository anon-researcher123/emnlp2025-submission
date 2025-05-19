from persona import Persona
from plan import Plan
from llm import OpenAILLM  
import time
from datetime import datetime, timedelta
from memory import Memory

class Agent:
    def __init__(self, file_name: str, name: str, agent_type: str, intermediate_belief: str, intermediate_belief_depression: str, history:str, behavior:str, description: list, auto_thought:str, situation:str, model="gpt-4o"):
        self.name = name
        self.agent_type = agent_type
        self.intermediate_belief = intermediate_belief
        self.intermediate_belief_depression = intermediate_belief_depression
        self.history = history
        self.behavior = behavior
        self.model = model
        self.auto_thought = auto_thought
        self.situation = situation
        self.llm = OpenAILLM(llm_model_name=self.model, embedding_model_name="text-embedding-ada-002")
        self.description = description
        self.state = "idle"

        self.relationships = {}
        self.relationship_summary = {}

        self.persona = Persona(
            name=self.name,
            agent_type=self.agent_type,
            intermediate_belief=self.intermediate_belief,
            intermediate_belief_depression=self.intermediate_belief_depression,
            history=self.history,
            behavior=self.behavior,
            memory=None,
            llm=self.llm,
            description = self.description
        )

        self.memory = Memory(
            memory_path = file_name,
            persona=self.persona
        )
        self.memory.short_term_memory.long_term_memory.set_reflection_callback(self.handle_reflection)

        self.persona.memory = self.memory

        self.plan = Plan(
            name=self.name,
            history=self.history,
            description=self.description,
            memory=self.memory,
            auto_thought=self.auto_thought,
            situation=self.situation,
            behavior=self.behavior,
            relationship=self.relationships,
            llm=self.llm
        )

        self.memory.short_term_memory.description = self.description
        self.memory.memory_retrieval.short_memory.description = self.description

    def handle_reflection(self, reflection_entry):
        self.update_persona_description()


    def update_persona_description(self):
        reflection = self.memory.short_term_memory.long_term_memory.get_current_reflection()
        self.description = self.persona.get_persona_after_reflection(reflection)

        self.plan.description = self.description
        self.memory.short_term_memory.description = self.description
        self.memory.memory_retrieval.short_memory.description = self.description
        self.persona.description = self.description

    def update_relationship(self, other_agent_name, interaction_text):       
        prompt = f"""
        Below is a conversation interaction between {self.name} and {other_agent_name}:

        "{interaction_text}"

        Evaluate the quality of this interaction. If the conversation was engaging, useful, or enjoyable, 
        assign a positive score between 0 and 10. If it was unhelpful, boring, or unpleasant, 
        assign a negative score between -10 and 0.
        
        Return only the numeric score.
        """

        score_response = self.llm.get_llm_response(prompt).strip()

        try:
            score = float(score_response)
            if score < -10:
                score = -10
            elif score > 10:
                score = 10
        except ValueError:
            print(f"Error parsing LLM response for relationship score: {score_response}")
            score = 0 

        if other_agent_name not in self.relationships:
            self.relationships[other_agent_name] = 0
            self.plan.relationship[other_agent_name] = 0

        self.relationships[other_agent_name] += score
        self.plan.relationship[other_agent_name] += score
        self.relationship_summary[other_agent_name] = interaction_text

        
    def retrieve_memories(self, query):
        return self.memory.retrieve_memories(query)


    def get_relationship_summary(self, other_agent_name, curr_time=None):
        relationship_query = f"Relationship between {self.name} and {other_agent_name}"
        memory_statements = self.retrieve_memories(relationship_query)

        relationship_score = self.relationships.get(other_agent_name, 0)

        if not memory_statements:
            return f"{self.name} has no recorded memories of interactions with {other_agent_name}. Sentiment Score: {relationship_score}"

        joined_memory_statements = '\n- '.join(memory_statements)
        prompt = f"""How would you describe the relationship between {self.name} and {other_agent_name} based on the following statements?
        \n- {joined_memory_statements}"""

        relationship_summary = self.llm.get_llm_response(prompt)
        return f"{relationship_summary}\nSentiment Score: {relationship_score}"