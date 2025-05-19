import time
import os
from datetime import datetime, timedelta

SIMULATION_START = datetime.strptime("2025-02-11 00:15:00", "%Y-%m-%d %H:%M:%S")
ACTUAL_START = None

class DatetimeNL:

    @staticmethod
    def get_date_nl(curr_time):
        # e.g. Monday Jan 02 2023
        day_of_week = curr_time.strftime('%A')
        month_date_year = curr_time.strftime("%b %d %Y")
        date = f"{day_of_week} {month_date_year}"
        return date

    @staticmethod
    def get_time_nl(curr_time):
        #e.g. 12:00 am and 07:00 pm (note there is a leading zero for 7pm)
        time = curr_time.strftime('%I:%M %p').lower()
        return time

    @staticmethod
    def convert_nl_datetime_to_datetime(date, time):
        # missing 0 in front of time
        if not isinstance(date,str):
            date = date.strftime("%A %b %d %Y")

        if time.startswith("00"):
            time = "12" + time[2:]

        if len(time) != len("12:00 am"):
            time = "0" + time.upper()
        
        concatenated_date_time = date + ' ' + time
        curr_time = datetime.strptime(concatenated_date_time, "%A %b %d %Y %I:%M %p")
        return curr_time

    def subtract_15_min(curr_time):
        return curr_time - timedelta(minutes=15)
    
    def add_15_min(curr_time):
        return curr_time + timedelta(minutes=15)
        
    @staticmethod
    def get_formatted_date_time(curr_time):
        # e.g. "It is Monday Jan 02 2023 12:00 am"
        date_in_nl = DatetimeNL.get_date_nl(curr_time)
        time_in_nl = DatetimeNL.get_time_nl(curr_time)
        formatted_date_time = f"It is {date_in_nl} {time_in_nl}"
        return formatted_date_time
    
    @staticmethod
    def get_date_range(start_date, end_date):
        """
        Get date range between start_date (inclusive) and end_date (inclusive)
        
        start_date and end_date are str in the format YYYY-MM-DD
        """
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        date_range = []
        
        while start_date <= end_date:
            date_range.append(start_date.strftime('%Y-%m-%d'))
            start_date += timedelta(days=1)
        if not date_range:
            raise ValueError("end_date must be later or equal to start_date")
        return date_range

    @staticmethod
    def initialize_simulation_start():
        global ACTUAL_START
        ACTUAL_START = datetime.now().replace(microsecond=0)
        return ACTUAL_START

    @staticmethod
    def accelerated_time(n = 3) -> datetime:

        global ACTUAL_START
        if ACTUAL_START is None:
            DatetimeNL.initialize_simulation_start()
        actual_elapsed = datetime.now().replace(microsecond=0) - ACTUAL_START  
        accelerated_elapsed = actual_elapsed * n  
        new_datetime = SIMULATION_START + accelerated_elapsed
        return new_datetime

    @staticmethod
    def convert_time_string(time_str):
        curr_time = DatetimeNL.accelerated_time()
        hour_part = int(time_str.split(":")[0])
        
        if hour_part > 12:
            converted_hour = str(hour_part - 12).zfill(2)
            time_str = converted_hour + time_str[2:]
        
        if time_str.startswith("00"):
            time_str = "12" + time_str[2:]
        
        time_part = datetime.strptime(time_str, "%I:%M %p").time()

        dt = datetime.combine(curr_time.date(), time_part)
        return dt