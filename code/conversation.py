import random
import time
from datetime import timedelta
from location import Location
import time_utils  
from memory import Memory 
from time_utils import DatetimeNL


class Conversation:
    def __init__(self, agents):
        self.active_conversations = {}  
        self.agents = agents  
        self.location = Location.get_instance()  

    def conversation_trigger(self, agent):
        curr_time = DatetimeNL.accelerated_time()
        last_activity = agent.plan.get_agent_action()
        
        if agent.state != "idle":
            agent.memory.add_to_memory("event", last_activity, timestamp=curr_time)
            return f"{agent.name} is currently busy."

        visible_agents = self.location.get_visible_agents(agent)

        if not visible_agents:
            agent.memory.add_to_memory("event", last_activity, timestamp=curr_time)
            return f"{agent.name} is alone and does not initiate a conversation."

        candidates = []
        for other_agent_name in visible_agents:
            other_agent = self.get_agent_by_name(other_agent_name)
            if other_agent and other_agent.state == "idle":
                relationship_score = agent.relationships.get(other_agent_name, 0)
                probability = max(5, min(100, relationship_score + 50))
                if random.randint(1, 100) <= probability:
                    candidates.append(other_agent_name)

        if not candidates:
            agent.memory.add_to_memory("event", last_activity, timestamp=curr_time)
            return f"{agent.name} does not find a suitable conversation partner."

        other_agent_name = random.choice(candidates)
        other_agent = self.get_agent_by_name(other_agent_name)

        agent.state = "talking"
        other_agent.state = "talking"

        conversation_id = f"{agent.name}_{other_agent.name}_{int(time.time())}"
        self.active_conversations[conversation_id] = {
            "agents": (agent, other_agent),
            "turns": 0,
            "dialogue": []
        }

        return self.run_conversation(conversation_id)


    def run_conversation(self, conversation_id):
        conversation = self.active_conversations[conversation_id]
        agent1, agent2 = conversation["agents"]
        turn = 0
        start_time = time_utils.DatetimeNL.accelerated_time()

        while turn < 10:
            if time_utils.DatetimeNL.accelerated_time() - start_time >= timedelta(minutes=15):
                break

            timestamp = time_utils.DatetimeNL.accelerated_time()
            speaker, listener = (agent1, agent2) if turn % 2 == 0 else (agent2, agent1)
            
            try:
                relationship = speaker.relationship_summary[listener.name]
            except:
                relationship = f'{listener.name}'

            if turn == 0:
                topic = self.choose_topic(speaker, listener, relationship)
            else:
                topic = conversation["dialogue"]

            response = self.generate_response(speaker, listener, topic)
            description = f"{speaker.name}: {response}"  

            speaker.memory.add_to_memory(memory_type="chat", description=description, timestamp=timestamp)
            listener.memory.add_to_memory(memory_type="chat", description=description, timestamp=timestamp)

            conversation["dialogue"].append(description)
            turn += 1

            if turn > 5 and self.should_end_conversation(speaker, listener, turn):
                break

        conversation["turns"] = turn
        print('conversation history:', conversation["dialogue"])

        agent1.memory.reset_chat_set()
        agent2.memory.reset_chat_set()

        self.update_relationships_after_conversation(conversation["dialogue"], agent1, agent2)

        del self.active_conversations[conversation_id]
        agent1.state = "idle"
        agent2.state = "idle"
        return f"Conversation ended after {turn} turns."

    def update_relationships_after_conversation(self, dialogue_text, agent1, agent2):
        summary_agent1 = self.summarize_conversation(agent1, dialogue_text)
        summary_agent2 = self.summarize_conversation(agent2, dialogue_text)

        agent1.update_relationship(agent2.name, summary_agent1)
        agent2.update_relationship(agent1.name, summary_agent2)

        summary_with_relationship_1 = f"Summary (from {agent1.name}): {summary_agent1}"
        summary_with_relationship_2 = f"Summary (from {agent2.name}): {summary_agent2}"

        agent1.memory.long_term_memory.add_reflection({
            "node_id": agent1.memory.short_term_memory.generate_node_id("thought"),
            "timestamp": time_utils.DatetimeNL.accelerated_time(),
            "description": summary_with_relationship_1,
            "memory_type": "thought",
            "embedding": agent1.memory.short_term_memory.generate_embedding(summary_with_relationship_1),
            "poignancy": agent1.memory.short_term_memory.calculate_poignancy(summary_with_relationship_1),
            "emotion": agent1.memory.short_term_memory.emotion_analyze(summary_with_relationship_1)[0],
            "emotion_intensity": agent1.memory.short_term_memory.emotion_analyze(summary_with_relationship_1)[1]
        })

        agent2.memory.long_term_memory.add_reflection({
            "node_id": agent2.memory.short_term_memory.generate_node_id("thought"),
            "timestamp": time_utils.DatetimeNL.accelerated_time(),
            "description": summary_with_relationship_2,
            "memory_type": "thought",
            "embedding": agent2.memory.short_term_memory.generate_embedding(summary_with_relationship_2),
            "poignancy": agent2.memory.short_term_memory.calculate_poignancy(summary_with_relationship_2),
            "emotion": agent2.memory.short_term_memory.emotion_analyze(summary_with_relationship_2)[0],
            "emotion_intensity": agent2.memory.short_term_memory.emotion_analyze(summary_with_relationship_2)[1]
        })

    def summarize_conversation(self, agent, conversation_text):
        persona_info = agent.description 

        prompt = f"""
        {agent.name} just had a conversation.
        {agent.name}'s persona: {persona_info}

        Here's what was said:
        {conversation_text}

        Summarize this from {agent.name}'s perspective in a casual way.
        """
        return agent.llm.get_llm_response(prompt)

    def should_end_conversation(self, speaker, listener, turn):
        dialogue_history = self.active_conversations[f"{speaker.name}_{listener.name}_{turn}"]["dialogue"] \
            if f"{speaker.name}_{listener.name}_{turn}" in self.active_conversations else []

        prompt = f"""
        Below is the dialogue history between {speaker.name} and {listener.name} over {turn} turns:

        {dialogue_history}

        Analyze the flow of conversation. Is it becoming repetitive or stagnant? 
        Has there been any emotional or topic progression? 
        If the dialogue feels stuck, repetitive, or lacks depth, say "yes" to end. Otherwise, say "no".
        Should this conversation naturally come to an end? (yes/no)
        """
        response = speaker.llm.get_llm_response(prompt).strip().lower()
        return response == "yes"


    def choose_topic(self, speaker, listener, relationship_summary):
        persona_info = speaker.description 

        prompt = f"""
        {speaker.name} wants to start a conversation with {listener.name}.
        {speaker.name}'s persona: {persona_info}
        Relevant memories:
        {speaker.retrieve_memories(relationship_summary)}

        Suggest a topic they would naturally talk about.
        """
        return speaker.llm.get_llm_response(prompt)

    def generate_response(self, speaker, listener, topic):
        persona_info = speaker.description
        topic_str = "\n".join(topic)
        
        if speaker.agent_type == "patient":

            prompt = f"""
            {speaker.name} and {listener.name} are having a casual chat.
            Dialogue history: {topic}
            Last dialouge: {topic[-1]}
            {speaker.name}'s persona: {persona_info}
            Relevant memories:
            {speaker.retrieve_memories(topic_str)}

            Conversation Rules:
            - Always respond in line with your persona's psychological traits, emotional tendencies, and behavioral patterns.
            - Your personality, emotional reactions, and thought patterns should directly reflect the information in {speaker.name}'s persona.
            - If your persona includes traits like avoidance, low mood, anxiety, resistance, or rumination, show them in your response.
            - If your persona includes traits like hostility, fear, trauma, or dependency, reflect those in your interaction style.
            - You may respond dismissively, defensively, passively, emotionally, or with hesitation—whatever is congruent with your character.
            - Do not reveal too much too quickly unless your persona indicates impulsivity or oversharing.
            - Keep your language natural, conversational, and emotionally grounded in your experience.

            Behavioral Guidelines:
            - Avoid abstract or generic replies.
            - Responses should be 2–3 sentences long.
            - Reference specific emotions, events, or experiences from your memories or past statements when possible.
            - Express internal conflict, emotional friction, or tension when relevant.

            Based on this, what would {speaker.name} say?
            responce to Last dialouge: {topic[-1]}
            Avoid abstract or generic statements.
            Generate a natural response in a conversational tone.
            Only two to three sentences.
            """

        elif speaker.agent_type == "counselor":
            prompt = f"""
            {speaker.name} and {listener.name} are having a casual chat.
            Dialogue history: {topic}  
            Last dialouge: {topic[-1]}
            {speaker.name}'s persona: {persona_info}
            Relevant memories:
            {speaker.retrieve_memories(topic_str)}

            Conversation Style:
            - Keep the tone gentle, natural, and client-centered.
            - Ask one question at a time, preferably Socratic in style: clarify meanings, uncover assumptions, explore implications, and consider alternatives.
            - Avoid using therapy jargon, labels, or references to psychological theories or books.
            - Don’t initiate with personal knowledge (like “I read a book about CBT…”).
            - Focus on the speaker’s emotional experience, behavior patterns, or contradictions.
            - Responses should sound like a real, warm, emotionally intelligent person, not a textbook or therapist.
            - Avoid obvious “counseling language” like “How does that make you feel?” or “Tell me more about that.”
            - Instead, use language that reflects understanding and curiosity grounded in the conversation history.

            Counseling Phases:
            1. Early Stage: Build rapport and emotional safety. Use clarification and gentle questions to understand the client's experience more deeply.
            2. Middle Stage: Help the client notice thought patterns, internal conflicts, and consequences. Ask reflective questions that gently challenge assumptions.
            3. Late Stage: Encourage reflection on changes, new understanding, and possible actions without prescribing them.

            Instructions:
            - Keep replies short: 2–3 natural sentences.
            - Ground the response in what the listener just said or past memory.
            - Do not make abstract or generic statements.
            - Do not introduce counseling theories or techniques by name.
            - Don’t rush to problem-solving—stay with the client’s emotions and experiences.

            Based on this, what would {speaker.name} say?
            responce to Last dialouge: {topic[-1]}
            Generate a natural response in a conversational tone.
            Only two to three sentences.
            """


        else:
            prompt = f"""
            {speaker.name} and {listener.name} are having a casual chat.
            Dialogue history: {topic}  
            Last dialouge: {topic[-1]}
            {speaker.name}'s persona: {persona_info}
            Relevant memories:
            {speaker.retrieve_memories(topic_str)}

            Based on this, what would {speaker.name} say?
            responce to Last dialouge: {topic[-1]}
            Avoid abstract or generic statements.
            Use specific emotions, events, or examples from personal memory or prior interactions.
            Connect the response to a concrete detail from the relevant memories or the other agent's behavior.
            Generate a natural response in a conversational tone.
            Only two to three sentences.
            """
        return speaker.llm.get_llm_response(prompt)

    def get_agent_by_name(self, name):
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None
