import random
import typing
from enum import Enum

import simpy

# the min value of R in actual processing time model
R_RANDOM_MIN = 0.1
# the max value of R in actual processing time model
R_RANDOM_MAX = 0.7


class Priority(Enum):
    LOW = 1
    MIDDLE = 2
    HIGH = 3
    DEFAULT = -1


class Process:
    """
    Process Class
    """

    def __init__(self, name: str, arrival_time: int, service_time: int, priority: Priority = Priority.DEFAULT):
        self.name = name
        self.arrival_time = arrival_time
        self.service_time = service_time
        self.priority = priority


EXAMPLE_LOW_PRIORITY_PROCESS: typing.List[Process] = [Process("low-priority-process1", 1, 10, Priority.LOW),
                                Process("low-priority-process2", 4, 15, Priority.LOW),
                                Process("low-priority-process3", 6, 20, Priority.LOW),
                                Process("low-priority-process4", 3, 5, Priority.LOW),
                                Process("low-priority-process5", 9, 10, Priority.LOW)]

EXAMPLE_MIDDLE_PRIORITY_PROCESS: typing.List[Process] = [Process("middle-priority-process1", 2, 12, Priority.MIDDLE),
                                Process("middle-priority-process2", 5, 8, Priority.MIDDLE),
                                Process("middle-priority-process3", 7, 18, Priority.MIDDLE),
                                Process("middle-priority-process4", 9, 10, Priority.MIDDLE),
                                Process("middle-priority-process5", 6, 22, Priority.MIDDLE),
                                Process("middle-priority-process5", 10, 15, Priority.MIDDLE)]

EXAMPLE_HIGH_PRIORITY_PROCESS: typing.List[Process] = [Process("high-priority-process1", 3, 9, Priority.HIGH),
                                Process("high-priority-process2", 8, 11, Priority.HIGH),
                                Process("high-priority-process3", 1, 10, Priority.HIGH),
                                Process("high-priority-process4", 7, 14, Priority.HIGH),
                                Process("high-priority-process5", 5, 7, Priority.HIGH),
                                Process("middle-priority-process5", 11, 12, Priority.MIDDLE)]


def fcfs(env, processes):
    for process in processes:
        yield env.timeout(process.arrival_time)
        print(f"Time {env.now}: Process {process.name} starts")
        yield env.timeout(process.service_time)
        print(f"Time {env.now}: Process {process.name} finishes")


def priority(env, processes):
    sorted_processes = sorted(processes, key=lambda x: x.priority)
    for process in sorted_processes:
        yield env.timeout(process.arrival_time)
        print(f"Time {env.now}: Process {process.name} with priority {process.priority} starts")
        yield env.timeout(process.service_time)
        print(f"Time {env.now}: Process {process.name} finishes")


def _generate_random_r() -> float:
    """
    generate the R random of the model of Actual Processing time of tasks
    k = Ti,k*(1+R)
    :return: the random value of R beterrn 0.1% == 0.001, 0.7% == 0.007
    """
    return random.uniform(0.001, 0.007)


# TODO: adopt SIMD to speed up
def _compute_actual_processing_time(expected_time: float, r: float = None) -> float:
    """
    compute the actual executing time based on expected time
    :param expected_time: expected processing time
    :param r: a random variable, if None, then generate a random number from 0.1% to 0.7%%
    :return: the actual processing time
    """
    if r is None:
        r = _generate_random_r()
    r /= 100
    return expected_time * (1 + r)


# def _process_input() -> typing.Tuple(int, int, int):


if __name__ == '__main__':
    # random.seed(42)
    env = simpy.Environment()
    env.process()
    env.timeout()

# Define processes
processes_fcfs = [
    Process("P1", arrival_time=0, service_time=3),
    Process("P2", arrival_time=1, service_time=2),
    Process("P3", arrival_time=2, service_time=1)
]

processes_priority = [
    Process("P1", arrival_time=0, service_time=3, priority=3),
    Process("P2", arrival_time=1, service_time=2, priority=2),
    Process("P3", arrival_time=2, service_time=1, priority=1)
]

# Run FCFS
print("First-Come, First-Served (FCFS):")
env.process(fcfs(env, processes_fcfs))
env.run()

# Run Priority scheduling
print("\nPriority Scheduling:")
env.process(priority(env, processes_priority))
env.run()
