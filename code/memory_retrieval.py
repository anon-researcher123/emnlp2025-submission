import json
import numpy as np
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity
from short_term_memory import ShortTermMemory
from long_term_memory import LongTermMemory
from llm import OpenAILLM
from time_utils import DatetimeNL

class MemoryRetrieval:
    def __init__(self, memory_path, persona=None):
        self.short_memory = ShortTermMemory(memory_path, persona=persona)
        self.long_memory = LongTermMemory(memory_path)
        self.short_term_data = self.short_memory.whole_memories
        self.long_term_data = self.long_memory.memory_entries
        self.llm = OpenAILLM(llm_model_name="gpt-4o-mini", embedding_model_name="text-embedding-ada-002")


    def retrieve_top_memories(self, query):
        timestamp = DatetimeNL.accelerated_time()
        query_embedding = self.generate_embedding(query)
        query_emotion, query_emotion_score = self.emotion_analyze(query)

        weights = {
            "recency": 0.10,
            "relevance": 0.25,
            "poignancy": 0.40,
            "emotion_score": 0.15,
            "emotion_relevance": 0.10
        }

        emotion_pairs = {
            "joy": "sadness",
            "sadness": "joy",
            "anger": "trust",
            "fear": "anticipation",
            "anticipation": "fear",
            "surprise": "disgust",
            "trust": "anger",
            "disgust": "surprise"
        }

        short_ranked = self.rank_memory(query_embedding, query_emotion, self.short_term_data, weights, emotion_pairs, memory_type="short")
        long_ranked = self.rank_memory(query_embedding, query_emotion, self.long_term_data, weights, emotion_pairs, memory_type="long")
        short_top_5 = [node[0] for node in short_ranked[:5]]
        long_top_5 = [node[0] for node in long_ranked[:5]]

        top_10_memories = short_top_5 + long_top_5

        return {
            "short_term_retrieved": short_top_5,
            "long_term_retrieved": long_top_5,
            "top_10_retrieved": top_10_memories
        }

    def _find_query_node_id(self, query):
        for memory in self.short_term_data:
            if memory["description"] == query and memory["memory_type"] == "query":
                return memory["node_id"]
        return None 

    def generate_embedding(self, text):
        return self.llm.get_embeddings(text)

    def calculate_recency(self, timestamp, reference_time):
        time_diff = (reference_time - datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")).total_seconds()
        time_diff_hours = abs(time_diff) / 3600
        max_time_diff = 168
        return max(0, 1 - (time_diff_hours / max_time_diff))

    def calculate_relevance(self, input_embedding, target_embedding):
        similarity = cosine_similarity([input_embedding], [target_embedding])[0][0]
        return similarity

    def calculate_emotion_relevance(self, node_emotion, input_emotion, emotion_pairs):
        if node_emotion == input_emotion:
            return 1.5
        elif emotion_pairs.get(input_emotion) == node_emotion:
            return 0.1
        else:
            return 0.5

    def rank_memory(self, query_embedding, query_emotion, memory_data, weights, emotion_pairs, memory_type="short"):
        reference_time = DatetimeNL.accelerated_time()
        print(reference_time)
        scored_nodes = []
        for node in memory_data:
            if not isinstance(node, dict):  
                print("Unexpected node format:", node)
                continue
            if memory_type == "short" and node["memory_type"] not in ["event", "chat"]:
                continue

            recency = self.calculate_recency(node['timestamp'], reference_time)
            relevance = self.calculate_relevance(query_embedding, node['embedding'])
            poignancy = node.get('poignancy', 1) / 10.0 if node.get('poignancy') is not None else 0.0
            emotion_score = node.get('emotion_intensity', 1) / 10.0 if node.get('emotion_intensity') is not None else 0.0
            emotion_relevance = self.calculate_emotion_relevance(node['emotion'], query_emotion, emotion_pairs) / 1.5 \
                if node.get('emotion') else 0.0

            total_score = (
                weights['recency'] * recency +
                weights['relevance'] * relevance +
                weights['poignancy'] * poignancy +
                weights['emotion_score'] * emotion_score +
                weights['emotion_relevance'] * emotion_relevance
            )
            
            scored_nodes.append((node, total_score, weights['recency'] * recency, weights['relevance'] * relevance,  weights['poignancy'] * poignancy,  weights['emotion_score'] * emotion_score, weights['emotion_relevance'] * emotion_relevance))
        
        scored_nodes.sort(key=lambda x: x[1], reverse=True)

        return scored_nodes

    def emotion_analyze(self, query, max_attempts=50):
        persona_text = self.short_memory.format_persona() if self.short_memory else "Persona information not available."
        valid_emotions = {"joy", "sadness", "anger", "fear", "anticipation", "surprise", "trust", "disgust"}

        prompt = f"""
        {persona_text}

        Analyze the following query and provide the primary emotion and its intensity.
        1. The primary emotion must strictly be one of the following: {list(valid_emotions)}.
        2. The intensity of the emotion should be a number between 1 and 10.

        Respond in JSON format only without explanation:
        {{
            "emotion": "joy",
            "emotion_score": 8
        }}

        Query: "{query}"
        """

        for attempt in range(max_attempts):
            response = self.llm.get_llm_response(prompt).strip()
            response_clean = (
                response.replace("```json", "")
                .replace("```", "")
                .strip()
            )

            try:
                result = json.loads(response_clean)
                emotion = result.get("emotion", "").strip().lower()
                emotion_score = float(result.get("emotion_score", 5.0))

                if emotion in valid_emotions:
                    return emotion, emotion_score

            except (json.JSONDecodeError, ValueError, TypeError) as e:
                print()

        print(f"⚠ Retrieval Warning: {max_attempts} attempts reached, setting default emotion to 'sadness'")
        return "sadness", 5.0


