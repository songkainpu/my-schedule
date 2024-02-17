import threading
import typing
from enum import Enum

from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ScheduleInfo(Base):
    __tablename__ = 'schedule_info'
    id = Column(Integer, primary_key=True)
    round_id = Column(String(256))
    priority = Column(String(128))
    waiting_time = Column(Float)
    actual_execute_time = Column(Float)
    origin_execute_time = Column(Float)


class TaskType(Enum):
    LOW = (1 << 31, [1, 4, 6, 3, 9], [10, 15, 20, 5, 10])
    MIDDLE = (1 << 16, [2, 5, 7, 9, 6, 10], [12, 8, 18, 10, 22, 15])
    HIGH = (1, [3, 8, 1, 7, 5, 11], [9, 11, 10, 14, 7, 12])
    DEFAULT = LOW

    def __init__(self, priority: int, machine_sequence: typing.List[int], process_time_list: typing.List[int]):
        """
        TaskType Enum
        :param priority:
        :param machine_sequence:
        :param process_time_list:
        """
        self.priority = priority
        self.machine_sequence = machine_sequence
        self.process_time_list = process_time_list

    @staticmethod
    def get_min_and_max_machine_no() -> typing.Tuple[int, int]:
        """

        :return: first element is min value, the last is max value
        """
        return (min(min(TaskType.LOW.machine_sequence),
                    min(TaskType.MIDDLE.machine_sequence),
                    min(TaskType.HIGH.machine_sequence)),
                max(max(TaskType.LOW.machine_sequence),
                    max(TaskType.MIDDLE.machine_sequence),
                    max(TaskType.HIGH.machine_sequence)))

class Process:
    """
    Process Class
    """

    def __init__(self, name: str,
                 arrival_time: typing.Union[int, float],
                 service_time:  typing.Union[int, float],
                 priority: TaskType = TaskType.DEFAULT):
        self.name = name
        self.arrival_time = arrival_time
        self.service_time = service_time
        self.priority = priority
        self.stage = 0
        self.stage_op_lock = threading.Lock()

    def __lt__(self, other):
        return True

    def __eq__(self, other):
        return False

    def get_sort_key(self) -> str:
        if not self.priority or not self.arrival_time:
            raise ValueError(f"Invalid priority, and arrive_time: Process{Process}")
        return f"{format(self.priority.value[0], '032b')}-{format(int(self.arrival_time), '032b')}"

    def get_arrive_time_priority_sort_key(self) -> str:
        if not self.priority or not self.arrival_time:
            raise ValueError(f"Invalid priority, and arrive_time: Process{Process}")
        return f"{format(int(self.arrival_time), '032b')}-{format(self.priority.value[0], '032b')}"

    def get_origin_cur_process_time(self) -> typing.Union[None, int, float]:
        if self.stage >= len(self.priority.process_time_list):
            return None
        return self.priority.process_time_list[self.stage]
