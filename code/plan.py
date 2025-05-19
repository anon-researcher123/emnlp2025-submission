import logging
from time_utils import DatetimeNL
from memory import Memory

class Plan:
    def __init__(self, name, history, description, memory, auto_thought, situation, behavior, relationship, llm):
        self.name = name
        self.history = history
        self.description = description
        self.memory = memory
        self.llm = llm
        self.suggested_changes = []
        self.thought = auto_thought
        self.situation = situation
        self.behavior = behavior
        self.relationship = relationship

    @staticmethod
    def check_updated_plan_format(plan):
        prev_t = None
        curr_time = DatetimeNL.accelerated_time()

        if plan is None:
                return False

        plan_items = plan.split('\n')

        if len(plan_items) < 2:
            return False 
        
        for idx, plan_item in enumerate(plan_items, start=1):
            plan_colon_split = plan_item.split(":")
            
            if len(plan_colon_split) > 2 and plan_colon_split[0].isdigit():
                minute_and_rest = plan_colon_split[1].strip()
                if len(minute_and_rest.split(" ")) >= 2:
                    minute = minute_and_rest.split(" ")[0]
                    ampm = minute_and_rest.split(" ")[1]

                    if minute.isdigit() and ampm in ["am", "pm"]:
                        ts = plan_colon_split[0].zfill(2) + ":" + minute + " " + ampm
                        t = DatetimeNL.convert_time_string(ts)

                        if t is None:
                            return False  
                        
                        if idx == 1 and t >= curr_time:
                            return False

                        if prev_t is not None:
                            time_diff = (t - prev_t).total_seconds() / 60
                            if time_diff == 15:
                                pass
                            else:
                                return False
                        else:
                            pass

                        prev_t = t
                        continue

            return False

        return True 
    
    @staticmethod
    def check_plan_format(plan):
        if plan is None:
            return False

        plan_items = plan.split('\n')

        if len(plan_items) < 2:
            return False 

        for plan_item in plan_items:
            plan_colon_split = plan_item.split(":")
            if len(plan_colon_split) > 2 and plan_colon_split[0].isdigit() and len(plan_colon_split[1].split(" ")) == 2 and plan_colon_split[1].split(" ")[0].isdigit() and plan_colon_split[1].split(" ")[1] in ["am", "pm"]:
                pass
            else:
                return False
            
        
        plan_item = plan_items[-1]
        if plan_item.split(":")[1].split(" ")[1] == "am":
            print("End to early")
            return False
        return True
    

    @staticmethod
    def postprocess_initial_plan(plan):
        plan = plan.strip()

        # remove empty lines
        plan_list = plan.split('\n')
        plan = '\n'.join([plan_item for plan_item in plan_list if len(plan_item.strip())])

        plan_list = plan.split('\n')
        new_plan_list = []
        for plan_item in plan_list:
            if len(plan_item.split("-")) > 1 and len(plan_item.split(":")) > 3:
                new_plan_list.append(plan_item.split("-", 1)[1].strip())
            else:
                new_plan_list.append(plan_item)

        plan = '\n'.join(new_plan_list)

        plan_list = plan.split('\n')
        new_plan_list = []
        for plan_item in plan_list:
            if len(plan_item.split(":")[0]) < 2:
                new_plan_list.append("0"+plan_item)
            else:
                new_plan_list.append(plan_item)
        plan = '\n'.join(new_plan_list)

        plan = '\n'.join([plan_item for plan_item in plan.split('\n') if len(plan_item.split(":")[0]) == 2])

        plan_list = plan.split('\n')
        new_plan_list = []
        for plan_item in plan_list:
            if len(plan_item) > 11:
                new_plan_list.append(plan_item[:11].lower() + plan_item[11:])
            else:
                new_plan_list.append(plan_item)

        plan = '\n'.join(new_plan_list)
        return plan
    
    def initial_plan(self, curr_time, condition=None, max_attempts=10):
        """
        This creates a daily plan using a person's name, age, traits, and a self description and the latest plan
        """
        date = DatetimeNL.get_date_nl(curr_time)
        condition_formatted = f'\nCondition: {condition}\n' if condition is not None else ''
        prompt = f"""
                Please plan a day for {self.name}. Generated plan must starts at 00:15am and ends by 11:45 pm.
                You must consider {self.name}'s Description carefully to create his plan.
                Plan during the night must be related to sleep. You can decide rather to sleep or struggle to get sleep
                You must decide when how long {self.name} to be sleeping by considering it's Description.
                Remeber, you don't have any psychological information to improve current situation unless it is provided in Description which means you should not meditate or perform relaxing activity.
                Stay with your Background, Description, Behavior and consider Situation and Thought about situation to plan activities considering it.

                Format:
                hh:mm am/pm: <activity>

                Name: {self.name}
                Background: {self.history}
                Description: {self.description}{condition_formatted}
                Situation: {self.situation}
                Thought about situation: {self.thought}
                Behavior: {self.behavior}

                On {date},

                Return only a plan.
            """
        resulting_plan = None
        
        attempts = 0
        while not self.check_plan_format(resulting_plan) and attempts < max_attempts:
            resulting_plan = self.llm.get_llm_response(prompt)
            resulting_plan = self.postprocess_initial_plan(resulting_plan)

            attempts += 1
            print(f"planning day attempt number {attempts} / {max_attempts}")

        if attempts == max_attempts:
            raise ValueError("Initial Plan generation failed")

        self.memory.add_to_memory("day_plan", resulting_plan, timestamp=curr_time)
        return resulting_plan

    def recursively_decompose_plan(self, plan, curr_time, time_interval="1 hour", max_attempts=10):

        prompt = f"""
            Please decompose the plan into items at intervals of {time_interval}. Generated plan must starts at 00:15am and ends by 11:45 pm.
            You must consider {self.name}'s Description carefully to create his plan.
            Format: hh:mm am/pm: <activity>

            Plan: 
            6:00 am: woke up and completed the morning routine
            7:00 am: finished breakfast
            8:00 am: opened up The Willows Market and Pharmacy
            8:30 am: greeted the regular customers and helped them with their medication needs
            12:00 pm: had lunch
            1:00 pm: continued working and assisting customers
            7:00 pm: closed up the shop and went home 
            8:00 pm: have dinner with his family
            9:00 pm: watched a movie with his son, Eddy
            10:00 pm: get ready for bed and slept

            Plan in intervals of 1 hour: 
            6:00 am: woke up and completed the morning routine 
            7:00 am: finished breakfast 
            8:00 am: opened up The Willows Market and Pharmacy 
            9:00 am: greeted the regular customers 
            10:00 am: helped regular customers with their medication needs 
            11:00 am: greeted more customers 
            12:00 pm: had lunch 
            1:00 pm: restocked medication 
            2:00 pm: checked computers on medications he should order
            3:00 pm: checked shelves to see whether popular medications are still in stock
            4:00 pm: helped with prescription of customers
            5:00 pm: helped with prescription of customers
            6:00 pm: helped customers with questions about side effects of medication
            7:00 pm: closed shop and went home
            8:00 pm: had dinner with family
            9:00 pm: watched a movie with his son, Eddy
            10:00 pm: got ready for bed and slept

            Remeber, you don't have any psychological information to improve current situation unless it is provided in Description which means you should not meditate or perform relaxing activity.
            Stay with your Background, Description, Behavior and consider Situation and Thought about situation to plan activities considering it.
            Name: {self.name}
            Background: {self.history}
            Description: {self.description}
            Situation: {self.situation}
            Thought about situation: {self.thought}
            Behavior: {self.behavior}
            Relationships, Score: {self.relationship}

            Plan: 
            {plan}
            Plan in intervals of {time_interval}:
            
            Each activity in plan should be specific as possible.
            You must not include interactions with people who are not listed in the Relationships.  
            That means, if there is no one in the Relationship list, you cannot include activities such as 'phone call with a friend' or 'discussing with colleagues'.
            
            The 'Score' reflects the emotional closeness or tension:  
            - A score between **-10 to 0** means a negative or strained relationship. Avoid any activities involving this person.  
            - A score between **1 to 10** means a positive relationship. You **may** include low-effort interactions with that person (e.g., short conversation, sitting near them), but only if such behavior is natural within the context of the Description.

            Do not add new people to the plan.  
            Do not suggest overly idealized self-help actions. If the person attempts therapeutic activities (e.g., breathing, journaling), it should reflect realistic effort and potential failure or frustration. The plan should feel natural and grounded in the character's described mental state.
            You don't have any psychological information to improve the current situation unless it is provided in the Description, which means you should **not** meditate or perform relaxing activity.


            Return only plan.
            """
        
        resulting_plan = None
        attempts = 0
        while not self.check_plan_format(resulting_plan) and attempts < max_attempts:
            resulting_plan = self.llm.get_llm_response(prompt) 
            resulting_plan = resulting_plan.split('\n')
            resulting_plan = '\n'.join([plan_item for plan_item in resulting_plan if plan_item.strip()])

            attempts += 1
            print(f"planning {time_interval} attempt number {attempts} / {max_attempts}")

        if attempts == max_attempts:
            raise ValueError(f"Plan {time_interval} generation failed")

        if time_interval == "15_minute":
            self.memory.add_to_memory(f"{time_interval}_plan", resulting_plan, curr_time )
        return resulting_plan

    def get_plan_after_curr_time(self, curr_time, plan_type='15_minute'):
        if plan_type == '15_minute':
            retrieved_memories = self.memory.short_term_memory.retrieve_plan("15_minute_plan")
            plan = retrieved_memories[-1]["description"] if retrieved_memories else ""
        
        time_nl = DatetimeNL.get_time_nl(curr_time)
        plan_items = plan.split('\n')
        for i, plan_item in enumerate(plan_items):
            if plan_item.strip().startswith(time_nl):
                return '\n'.join(plan_items[i:])

        date = DatetimeNL.get_date_nl(curr_time)

        last_i_before_curr_time = None
        for i, plan_item in enumerate(plan_items):
            entry_time_nl = ":".join(plan_item.split(":")[:2])
            if DatetimeNL.convert_nl_datetime_to_datetime(date, entry_time_nl) <= curr_time:
                last_i_before_curr_time = i
            else:
                break
            
        if last_i_before_curr_time is not None:
            return '\n'.join(plan_items[last_i_before_curr_time:])
        
        return ''
        
    def change_plans_helper(self, suggested_change, existing_plan):
        prompt = f"""
            Please use the suggested change ({suggested_change}) to edit activities in the original plan.  
            Format: hh:mm am/pm: <activity within 10 words>

            Name: {self.name}  
            Background: {self.history}  
            Description: {self.description}  
            Relationships, Score: {self.relationship}

            original plan:  
            {existing_plan}

            Stay with your Description and Background.  

            You must not include interactions with people who are not listed in the Relationships.  
            That means, if there is no one in the Relationship list, you cannot include activities such as 'phone call with a friend' or 'discussing with colleagues'.

            The 'score' reflects the emotional closeness or tension:  
            - A score between **-10 to 0** means a negative or strained relationship. Avoid any activities involving this person.  
            - A score between **1 to 10** means a positive relationship. You **may** include low-effort interactions with that person (e.g., short conversation, sitting near them), but only if such behavior is natural within the context of the Description.

            Do not add new people to the plan.  
            Do not suggest overly idealized self-help actions. If the person attempts therapeutic activities (e.g., breathing, journaling), it should reflect realistic effort and potential failure or frustration. The plan should feel natural and grounded in the character's described mental state.
            You don't have any psychological information to improve the current situation unless it is provided in the Description, which means you should **not** meditate or perform relaxing activity.

            Only include solitary and familiar actions unless a positively scored relationship allows otherwise.  
            The final activity in the plan should be scheduled for **11:45 PM**.

            updated plan:
            """
    
        llm_response = self.llm.get_llm_response(prompt)
        plan = self.postprocess_change_plans_helper(llm_response)
        return plan
    
    def postprocess_change_plans_helper(self, plan):
        plan = plan.split('\n')
        plan = '\n'.join([plan_item for plan_item in plan if plan_item.strip()])
        return plan
    
    def change_plans(self, suggested_change, curr_time, max_attempts=10):
        existing_plan = self.get_plan_after_curr_time(curr_time)
        time_nl = DatetimeNL.get_time_nl(curr_time)
        plan = None
        attempts = 0
        while not self.check_updated_plan_format(plan) and attempts < max_attempts:
            plan = self.change_plans_helper(suggested_change, existing_plan)

            attempts += 1
            logging.info(f"replanning at {time_nl} attempt number {attempts} / {max_attempts}")
            if not self.check_plan_format(plan):
                logging.info("Failed Plan")
            logging.info(plan)

        if attempts == max_attempts:
            logging.info("Existing plan")
            logging.info(existing_plan)
            return None
        return plan

    
    def plan_update(self):
        curr_time = DatetimeNL.accelerated_time()
        planned_activities = self.get_plan_after_curr_time(curr_time)
        formatted_date_time = DatetimeNL.get_formatted_date_time(curr_time)
        prompt = f"""
        {formatted_date_time}  
        Original plan: {planned_activities}  
        Description: {self.description}  
        Background: {self.history}  
        Relationships, Score: {self.relationship}

        Should {self.name} change their original plan? Please respond with either yes or no.  
        If yes, please also then suggest a specific change in 1 sentence.

        Remember, {self.name} does not have any psychological information to improve the current situation unless it is provided in the Description.  
        This means {self.name} should not meditate, journal, or perform emotionally soothing or therapeutic activities unless explicitly described.

        Additionally, do not suggest activities that involve any person who is not listed in the Relationships.  
        Only interactions with people in the Relationships list are allowed.
        Do not suggest overly idealized self-help actions. If the person attempts therapeutic activities (e.g., breathing, journaling), it should reflect realistic effort and potential failure or frustration. The plan should feel natural and grounded in the character's described mental state.


        Score indicates the nature of the relationship:  
        - A score between **-10 and 0** means the relationship is negative or strained. Avoid any activities involving that person.  
        - A score between **1 and 10** means a positive relationship. You may suggest light interaction with that person, but only if it fits naturally with the Description.

        If the Relationships list is empty, the plan must consist solely of solitary activities.  
        Do not invent new people or support systems.

        Stay on your Background and Description.
        """
        reaction_raw = self.llm.get_llm_response(prompt)
        suggested_change = self.parse_reaction_response(reaction_raw)
        self.suggested_changes.append((suggested_change, curr_time))

        if suggested_change is not None:
            updated_plan = self.change_plans(suggested_change, curr_time)
            if updated_plan is not None:
                self.memory.add_to_memory("15_minute_plan", updated_plan, timestamp=curr_time)
                return updated_plan
    
    def parse_reaction_response(self, response):
        """
        The first sentence should either contain Yes or No (and maybe some additional words). If yes, the second sentence onwards tells of the actual reaction
        """
        response_parts = response.split(".")
        if "yes" in response_parts[0].lower() and len(response_parts) > 1:
            full_response = '.'.join(response_parts[1:])
            return full_response
        return None
    
    @staticmethod
    def remove_formatting_before_time(one_string):
            for i, char in enumerate(one_string):
                if char.isdigit():
                    return one_string[i:]
            return ''

    def get_agent_action(self):
            retrieved_memories = self.memory.short_term_memory.retrieve_plan("15_minute_plan")
            plan = retrieved_memories[-1]["description"] if retrieved_memories else ""
            plan = plan.lower()

            curr_time = DatetimeNL.accelerated_time()
            time_nl = DatetimeNL.get_time_nl(curr_time)
            plan_items = plan.split('\n')

            plan_items = [Plan.remove_formatting_before_time(plan_item) for plan_item in plan_items if Plan.remove_formatting_before_time(plan_item)]
            date = DatetimeNL.accelerated_time()
            
            last_activity = None
            for plan_item in plan_items:
                entry_time_nl = ":".join(plan_item.split(":")[:2])
                if DatetimeNL.convert_nl_datetime_to_datetime(date, entry_time_nl) <= curr_time:
                    last_activity = ':'.join(plan_item.split(":")[2:])
            if last_activity is not None:
                return last_activity
            return "N/A"