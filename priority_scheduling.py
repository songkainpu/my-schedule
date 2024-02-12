import queue
import random
import threading
import typing
from enum import Enum

import simpy
from overrides import overrides

# the min value of R in actual processing time model
R_RANDOM_MIN = 0.1
# the max value of R in actual processing time model
R_RANDOM_MAX = 0.7


# TODO: 查一下gpt  python 的优先级队列怎么用


class Priority(Enum):
    LOW = 1 << 31
    MIDDLE = 1 << 16
    HIGH = 1
    DEFAULT = 1 << 31


class MachineResource(object):
    """
    the computing resources in a machine
    """

    def __init__(self, env: simpy.Environment, num_machine: int):
        self.env = env
        self.resource = simpy.Resource(env, num_machine)
    # def processTask(self):


# singleton
machine_resource: typing.Union[None, MachineResource] = None
machine_generate_lock: threading.Lock = threading.Lock()


def _generate_machine_resource(env: simpy.Environment, num_machine: int = 1) -> bool:
    global machine_resource
    if machine_resource is not None:
        return False
    with machine_generate_lock:
        machine_resource = MachineResource(env=env, num_machine=num_machine)
        return True
    return False


class Process:
    """
    Process Class
    """

    def __init__(self, name: str, arrival_time: int, service_time: int, priority: Priority = Priority.DEFAULT):
        self.name = name
        self.arrival_time = arrival_time
        self.service_time = service_time
        self.priority = priority

    def get_sort_key(self) -> str:
        if not self.priority or not self.arrival_time:
            raise ValueError(f"Invalid priority, and arrive_time: Process{Process}")
        return f"{format(self.priority.value, '032b')}-{format(self.arrival_time, '032b')}"


class PriorityBlockingQueue(queue.PriorityQueue):
    """
    A PriorityBlockingQueue is an extension of the PriorityQueue class
    that allows blocking operations for both putting and getting elements.
    """

    @overrides
    def __init__(self):
        """
        Initializes the PriorityBlockingQueue with a Condition variable.
        """
        super().__init__()
        self.condition = threading.Condition()

    @overrides
    def put(self, item: typing.Tuple[typing.Any, typing.Any], block=True, timeout=None):
        """
        Adds an item to the queue with the given priority.
        This method overrides the put method of the base class.
        :param item must be a tuple where the first element is sorted key, and the second is data
        """
        with self.condition:
            super().put((priority, item))
            self.condition.notify()

    @overrides
    def get(self, block=True, timeout=None):
        """
        Retrieves and removes the highest priority item from the queue.
        If the queue is empty, this method blocks until an item becomes available.
        This method overrides the get method of the base class.
        """
        with self.condition:
            while self.empty():
                self.condition.wait()
            _, item = super().get()
            return item if not isinstance(item, tuple) else item[1]


process_schedule_blocked_queue: PriorityBlockingQueue[Process] = PriorityBlockingQueue()
lock = threading.Lock()


def _convert_list_to_priority_blocking_queue(data: typing.Iterable[Process]) -> PriorityBlockingQueue[Process]:
    pq: PriorityBlockingQueue[Process] = PriorityBlockingQueue()
    for process in data:
        pq.put(item=(process.get_sort_key(), process))
    return pq


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


def _load_hierarchical_process_list(is_default: bool = True, level: int = 3, process_number: int = 1000) \
        -> typing.List[typing.List[Process]]:
    """
    load hierarchical process list
    :param is_default: is to return the default examoles <a href="https://canvas.nus.edu.sg/courses/53202/files/folder/2_CA_Assignments?preview=3407585" />
    :param level:  the total level of priority for process types
    :param process_number: the number of tasks in each type
    :return:
    """
    if is_default:
        return sorted([sorted(EXAMPLE_LOW_PRIORITY_PROCESS, key=lambda x: x.arrival_time),
                       sorted(EXAMPLE_MIDDLE_PRIORITY_PROCESS, key=lambda x: x.arrival_time),
                       sorted(EXAMPLE_HIGH_PRIORITY_PROCESS, key=lambda x: x.arrival_time)],
                      key=lambda ps: ps[0].priority.value)
    # TODO: implement the random generate
    return sorted([sorted(EXAMPLE_LOW_PRIORITY_PROCESS, key=lambda x: x.arrival_time),
                   sorted(EXAMPLE_MIDDLE_PRIORITY_PROCESS, key=lambda x: x.arrival_time),
                   sorted(EXAMPLE_HIGH_PRIORITY_PROCESS, key=lambda x: x.arrival_time)],
                  key=lambda ps: ps[0].priority.value)


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


def __check_is_remaining_process(hierarchical_processes: typing.List[typing.List[Process]]) -> bool:
    """
    check is there a proces in hierarchical_processes
    :param hierarchical_processes:
    :return: {@code True} there is at least a process
    {@code False} Otherwise
    """
    if not hierarchical_processes or len(hierarchical_processes) == 0:
        return False
    for process_list in hierarchical_processes:
        if process_list is not None and len(process_list) > 0:
            return True
    return False


def ___execute_process_mock(process: Process) -> typing.Generator:
    actual_process_time = _compute_actual_processing_time(expected_time=process.service_time)
    print(f"actual_process_time {actual_process_time}: Process {process.name} with priority {process.priority.value}")
    yield machine_resource.env.timeout(delay=actual_process_time)


def __allocate_process_task(process: Process) -> typing.Generator:
    with machine_resource.resource.request() as request:
        yield request
        print(f"Time {machine_resource.env.now}: Process {process.name} with priority {process.priority.value} starts")
        yield machine_resource.env.process(___execute_process_mock(process=process))
        print(f"Time {machine_resource.env.now}: Process {process.name} with priority {process.priority.value} starts")


def __generate_random_r() -> float:
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
        r = __generate_random_r()
    r /= 100
    return expected_time * (1 + r)


# def _process_input() -> typing.Tuple(int, int, int):


def pop_process(hierarchical_processes: typing.List[typing.List[Process]]):
    print(f"enter into pop process func")
    # record the time when submit previous process
    pre_arrive_time: int = 0
    while __check_is_remaining_process(hierarchical_processes):
        # pop the miniOne
        process_list_with_recent_process = hierarchical_processes[0]
        for process_list in hierarchical_processes:
            if (process_list is not None
                    and len(process_list) > 0
                    and process_list[0].arrival_time < process_list_with_recent_process[0].arrival_time):
                process_list_with_recent_process = process_list
        most_recent_process = process_list_with_recent_process.pop(0)
        print(f"most_recent_process:{most_recent_process.__dict__}")
        # use pysim to add the process into system
        yield machine_resource.env.timeout(most_recent_process.arrival_time - pre_arrive_time)
        pre_arrive_time = most_recent_process.arrival_time
        # TODO: implement a function to process
        submit_process: typing.Union[None, Process] = None
        with lock:
            process_schedule_blocked_queue.put(item=(most_recent_process.get_sort_key(), most_recent_process))
            # send a message to process task fetch the head
            # with machine_resource.resource.request():
            submit_process = process_schedule_blocked_queue.get()
        if submit_process is not None:
            machine_resource.env.process(__allocate_process_task(process=submit_process))


def main():
    random.seed(42)
    env: simpy.Environment = simpy.Environment()
    machine_number = int(input("please input the number of available machine: ").strip())
    _generate_machine_resource(env=env, num_machine=machine_number)
    processes_list: typing.List[typing.List[Process]] = _load_hierarchical_process_list()
    machine_resource.env.process(pop_process(hierarchical_processes=processes_list))
    machine_resource.env.run(until=90)


main()

# # Define processes
# processes_fcfs = [
#     Process("P1", arrival_time=0, service_time=3),
#     Process("P2", arrival_time=1, service_time=2),
#     Process("P3", arrival_time=2, service_time=1)
# ]
#
# processes_priority = [
#     Process("P1", arrival_time=0, service_time=3, priority=3),
#     Process("P2", arrival_time=1, service_time=2, priority=2),
#     Process("P3", arrival_time=2, service_time=1, priority=1)
# ]
#
# # Run FCFS
# print("First-Come, First-Served (FCFS):")
# env.process(fcfs(env, processes_fcfs))
# env.run()
#
# # Run Priority scheduling
# print("\nPriority Scheduling:")
# env.process(priority(env, processes_priority))
# env.run()
