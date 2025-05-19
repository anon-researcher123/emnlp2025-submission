from llm import OpenAILLM
import json
from datetime import datetime
from long_term_memory import LongTermMemory
import numpy as np
import os
import re

class ShortTermMemory:
    def __init__(self, memory_path, reflection_threshold=150, persona=None, model="gpt-4o-mini"):
        self.chat_memories = []
        self.recent_memories = []
        self.current_poignancy = reflection_threshold
        self.current_emotion_score = reflection_threshold
        self.reflection_threshold = reflection_threshold
        self.chat_message_id = 0
        self.general_memory_id = 1
        self.persona = persona
        self.model = model
        self.long_term_memory = LongTermMemory(memory_path)
        self.llm = OpenAILLM(llm_model_name=self.model, embedding_model_name="text-embedding-ada-002")
        self.memory_path = memory_path
        self.description = None
        self.name = self.persona.name

        with open(memory_path, 'r', encoding='utf-8') as file:
            memory = json.load(file)
            self.whole_memories = memory["short-term-memory"]
            if isinstance(self.whole_memories, dict):
                self.whole_memories = list(self.whole_memories.values())

        if self.whole_memories:
            max_existing_node_id = max(
                int(m["node_id"].split("-")[0]) for m in self.whole_memories if "node_id" in m
            )
            self.general_memory_id = max_existing_node_id + 1 

    def generate_node_id(self, memory_type):
        """
        Generates a unique node_id.
        - For "chat", use the same prefix (chat_set_id) and increase message_id.
        - For others (event, thought, etc.), use next available integer.
        """
        all_node_ids = []

        # shortterm
        all_node_ids += [int(m["node_id"].split("-")[0]) for m in self.whole_memories if "node_id" in m]

        # longterm
        all_node_ids += [int(m["node_id"].split("-")[0]) for m in self.long_term_memory.memory_entries if "node_id" in m]

        max_existing_node_id = max(all_node_ids, default=0)

        if memory_type == "chat":
            if self.chat_message_id == 0:
                self.chat_set_id = max_existing_node_id + 1
            node_id = f"{self.chat_set_id}-{self.chat_message_id}"
            self.chat_message_id += 1
        else:
            next_id = max_existing_node_id + 1
            node_id = f"{next_id}-0"
            self.general_memory_id = next_id + 1 

        print(f"generate_node_id(): generated node_id={node_id}")
        return node_id

    def reset_chat_set(self):
        self.chat_message_id = 0
        self.chat_set_id = None

    def format_persona(self):
        return self.description

    def generate_embedding(self, description):
        try:
            embedding = self.llm.get_embeddings(description)
            # print(f"Embedding generated.")
            return embedding
        except Exception as e:
            # print(f"Error generating embedding: {e}")
            return None

    def calculate_poignancy(self, description):
        persona_text = self.format_persona()
        prompt = f"""
        You will be given the information of speaker and recent memory of speaker.
        Your task is to evaluate the following memory description in terms of its importance to the speaker's psychological growth or self-understanding.

        Speaker information: 
        {persona_text}

        Recent_Memory:
        {description}

        Evaluation Criteria (1.0~10.0):
        - 1 represents a memory with little to no impact on personal development (e.g., routine tasks, factual statements, minor observations)
        - 5 represents a moment of moderate emotional awareness or insight, but without strong transformative value
        - 10 represents a rare and highly impactful memory that significantly alters the speaker’s thinking, emotions, or behavior

        Evaluation Steps:
        1. Read carefully about speaker information and recent memory
        2. Evaluate recent memory's importance from the speaker's perspective considering their emotional state and struggles
        3. Penalize if memory is routine tasks or lacks emotional depth
        4. Assign extra points if the memory opens up possibilities for self-reflection or action, especially in ways that may foster Ethan's growth or emotional insight
        5. Give extra points if the speaker is challenged gently and encouraged to explore personal desires and small actionable steps without fear of disruption
        6. Assess how the recent memory contributes to Ethan's understanding, and how it encourages self-exploration without feeling overwhelming
        7. Assign an importance score from 1 to 10, where 1 is the lowest and 10 is the highest based on the Evaluation Criteria.

        Provide Only Score, Nothing Else
"""

        response = self.get_llm_response(prompt)
        try:
            poignancy = float(response.strip())
            return poignancy
        except ValueError:
            return 5.0

    def emotion_analyze(self, description, max_attempts=100):
        persona_text = self.format_persona()
        valid_emotions = {"joy", "sadness", "anger", "fear", "anticipation", "surprise", "trust", "disgust"}
        
        prompt = f"""
        {persona_text}
        Analyze the following memory and provide the primary emotion and its intensity.
        1. The primary emotion must strictly be one of the following: ["joy", "sadness", "anger", "fear", "anticipation", "surprise", "trust", "disgust"].
        2. The intensity of the emotion should be a number between 1 and 10.

        Please respond in JSON format like this:
        {{
            "emotion": "joy",
            "emotion_score": 8
        }}
        Memory: "{description}"
        """

        attempts = 0
        while attempts < max_attempts:
            response = self.get_llm_response(prompt).strip()
            try:
                clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", response.strip())
                result = json.loads(clean)
                emotion = result.get("emotion", "").strip().lower()
                emotion_score = float(result.get("emotion_score", 5.0))

                if emotion in valid_emotions:
                    return emotion, emotion_score

            except (json.JSONDecodeError, ValueError, TypeError):
                pass  

            attempts += 1

        print(f"⚠ short_term Warning: {max_attempts} attempts reached for description: {description!r} → setting default emotion to 'sadness'")
        return "sadness", 5.0

    def get_llm_response(self, prompt):
        try:
            return self.llm.get_llm_response(prompt)
        except Exception as e:
            return ""

    def check_reflection_trigger(self, poignancy, emotion_score):
        self.current_poignancy -= poignancy
        self.current_emotion_score -= emotion_score

        if self.current_poignancy <= 0 or self.current_emotion_score <= 0:
            print("\n=== Reflection Triggered ===")
            reflection_result = self.generate_reflection()

            if reflection_result:
                print("Reflection completed. Resetting poignancy/emotion scores.")

                self.current_poignancy = self.reflection_threshold
                self.current_emotion_score = self.reflection_threshold

    def add_to_memory(self, memory_type, description, timestamp):
        node_id = self.generate_node_id(memory_type)

        if memory_type in ["day_plan", "15_minute_plan"]:
            memory_entry = {
                "node_id": node_id,
                "timestamp": timestamp,
                "description": description,
                "memory_type": memory_type,
                "poignancy": None,
                "emotion": None,
                "emotion_intensity": None,
                "embedding": None
            }
        elif memory_type == "thought" and description.strip().lower().startswith("summary"):
            pattern = r"Summary\s*\(from\s+([^)]+)\):\s*(.*)"
            match = re.match(pattern, description, re.IGNORECASE)
            if match:
                speaker = match.group(1).strip()
                summary_text = match.group(2).strip()
            else:
                speaker = ""
                summary_text = description.split(":", 1)[1].strip() if ":" in description else description

            embedding = self.generate_embedding(description)
            poignancy = self.calculate_poignancy(description)
            if self.persona and speaker == self.persona.name:
                emotion, emotion_intensity = self.emotion_analyze(summary_text)
            else:
                emotion, emotion_intensity = self.emotion_analyze_as_listener(summary_text, speaker)
            memory_entry = {
                "node_id": node_id,
                "timestamp": timestamp,
                "description": description,
                "memory_type": memory_type,
                "embedding": embedding,
                "poignancy": poignancy,
                "emotion": emotion,
                "emotion_intensity": emotion_intensity
            }
        else:
            embedding = self.generate_embedding(description)
            poignancy = self.calculate_poignancy(description)

            if memory_type == "chat":
                speaker, content = self.extract_speaker_and_content(description)
                if self.persona and speaker == self.persona.name:
                    emotion, emotion_intensity = self.emotion_analyze(content)
                else:
                    emotion, emotion_intensity = self.emotion_analyze_as_listener(content, speaker)
            else:
                emotion, emotion_intensity = self.emotion_analyze(description)

            memory_entry = {
                "node_id": node_id,
                "timestamp": timestamp,
                "description": description,
                "memory_type": memory_type,
                "embedding": embedding,
                "poignancy": poignancy,
                "emotion": emotion,
                "emotion_intensity": emotion_intensity
            }

        self.recent_memories.append(memory_entry)
        self.whole_memories.append(memory_entry)

        if memory_type in ["event", "chat"]:
            self.check_reflection_trigger(memory_entry["poignancy"], memory_entry["emotion_intensity"])

    def extract_speaker_and_content(self, description):
        try:
            speaker, content = description.split(":", 1)
            return speaker.strip(), content.strip()
        except ValueError:
            return "unknown", description
        
    def emotion_analyze_as_listener(self, description, speaker, max_attempts=100):
        persona_text = self.format_persona()
        valid_emotions = {"joy", "sadness", "anger", "fear", "anticipation", "surprise", "trust", "disgust"}

        prompt = f"""
        Persona Information:
        {persona_text}

        Situation:
        You are having a conversation with {speaker}. 
        Below is what {speaker} said to you. Analyze **your** emotional reaction to this statement as a listener.
        
        Task:
        1. Provide the **primary emotion** you feel. It must strictly be one of the following: ["joy", "sadness", "anger", "fear", "anticipation", "surprise", "trust", "disgust"].
        2. Provide the **intensity** of that emotion, as a number between 1 and 10.

        Please respond in JSON format like this:
        {{
            "emotion": "sadness",
            "emotion_score": 7
        }}

        Statement from {speaker}: "{description}"
        """

        attempts = 0
        while attempts < max_attempts:
            response = self.get_llm_response(prompt).strip()

            try:
                result = json.loads(response)
                emotion = result.get("emotion", "").strip().lower()
                emotion_score = float(result.get("emotion_score", 5.0))

                if emotion in valid_emotions:
                    return emotion, emotion_score
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

            attempts += 1

        print(f"short_term Warning (listener): {max_attempts} attempts reached for statement from {speaker!r}: {description!r} → setting default emotion to 'sadness'")
        return "sadness", 5.0

    def generate_reflection(self):
        recent_memory = list(self.recent_memories)
        questions = self.generate_questions(recent_memory)
        reflections = []

        all_node_ids = []

        # shortterm
        all_node_ids += [int(m["node_id"].split("-")[0]) for m in self.whole_memories if "node_id" in m]

        # longterm
        all_node_ids += [int(m["node_id"].split("-")[0]) for m in self.long_term_memory.memory_entries if "node_id" in m]

        current_reflection_id = max(all_node_ids, default=0) + 1

        latest_timestamp = max(
            [m["timestamp"] for m in recent_memory], default=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        for question in questions:
            relevant_shortterms = self.find_relevant_shortterms(question, recent_memory)
            reflection_text = self.generate_reflection_text(question, relevant_shortterms)

            poignancy = self.calculate_poignancy(reflection_text)
            emotion, emotion_score = self.emotion_analyze(reflection_text)
            embedding = self.generate_embedding(reflection_text)

            next_node_id = f"{current_reflection_id}-0"
            current_reflection_id += 1

            reflection_entry = {
                "node_id": next_node_id,
                "timestamp": latest_timestamp,
                "description": reflection_text,
                "memory_type": "thought",
                "embedding": embedding,
                "poignancy": poignancy,
                "emotion": emotion,
                "emotion_intensity": emotion_score
            }

            self.long_term_memory.add_reflection(reflection_entry)

            reflections.append(reflection_text)

        self.general_memory_id = current_reflection_id

        self.recent_memories.clear()

        return reflections

    def generate_questions(self, memory):
        memory_text = "\n".join(
            [f"Timestamp: {m['timestamp']}, Description: {m['description']}" for m in memory]
        )
        persona_text = self.format_persona()

        prompt = f"""
        Persona Information:
        {persona_text}

        Statements:
        {memory_text}

        Based on the above statements, what are the 3 most important high-level questions we can ask 
        to understand the behavior or motivations behind these observations?

        Provide the questions in a numbered list, without explanations.
        """
        try:
            response = self.get_llm_response(prompt)
            questions = [q.strip() for q in response.strip().split("\n") if q.strip()]
            print(f"Generated Questions: {questions}")
            return questions[:3]
        except Exception as e:
            print(f"Error generating questions: {e}")
            return []

    def find_relevant_shortterms(self, question, memory):
        question_embedding = self.generate_embedding(question)
        similarities = []

        for m in memory:
            if "embedding" in m and m["embedding"] is not None:
                memory_embedding = np.array(m["embedding"])
                question_embedding = np.array(question_embedding)
                similarity = np.dot(question_embedding, memory_embedding) / (
                    np.linalg.norm(question_embedding) * np.linalg.norm(memory_embedding)
                )
                similarities.append((similarity, m))

        similarities.sort(reverse=True, key=lambda x: x[0])
        relevant_memories = [item[1] for item in similarities[:5]]
        print(f"Found {len(relevant_memories)} relevant short-term memories.")
        return relevant_memories

    def generate_reflection_text(self, question, relevant_memories):
        memory_text = "\n".join(
            [f"Timestamp: {m['timestamp']}, Description: {m['description']}" for m in relevant_memories]
        )
        persona_text = self.format_persona()

        prompt = f"""

        Relevant Observations:
        {memory_text}

        Question:
        {question}

        Imagine you are in the situation described above.
        Reflect on your thoughts and feelings in response to the question,
        allowing your reflection to be shaped naturally by your current emotional state and past experiences.

        Write in a personal, conversational tone—like you're journaling or speaking to someone you trust.
        Avoid specific time references, and focus on expressing your internal thoughts as they are,
        whether they feel clear, conflicted, or unresolved.

        Avoid interpreting the situation in an overly positive or optimistic way unless specific adivces or helps are found in Relevant Observations to improve your cognition.
        If there are specific advices and helps from others found in Relevant Observations, try to reflect those advice in your response.
        Advice from others are stated in "Name: narrative" format and "{self.name}: narrative" is what you mentioned which is not a advice.
        stay true to your current emotional perspective.
        Remeber you should not answer questions too postively or optimistically if there were not related advice in Relevant Observation.

        Keep your response to 2–3 sentences.
        """
        try:
            response = self.get_llm_response(prompt)
            reflection = response.strip()
            print(f"Generated Reflection: {reflection}")
            return reflection
        except Exception as e:
            print(f"Error generating reflection text: {e}")
            return "Reflection generation failed."


    def retrieve_plan(self, memory_type):
        filtered_data = [entry for entry in self.whole_memories if entry.get('memory_type') == memory_type]
        return filtered_data
