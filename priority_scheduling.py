import queue
import random
import sys
import threading
import time
import traceback
import typing
from datetime import datetime

import gevent
import pytz
import simpy
from overrides import overrides

from data_model import ScheduleInfo, TaskType, Process
from generate_arriving_time import generate_process_list
from initi_mysql import session

shanghai_tz = pytz.timezone('Asia/Shanghai')
# the min value of R in actual processing time model
R_RANDOM_MIN = .001
# the max value of R in actual processing time model
R_RANDOM_MAX = .007
# TODO: search EN of 自旋
SELF_ROTATE_TIME = .001
round_uuid = datetime.now(shanghai_tz).strftime('%Y-%m-%d %H:%M:%S')
print(f"round_uuid:{round_uuid}")



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

    # to solve the problem than when using tuple as element and the first priority items are the same,
    # then the queue will compare the second element(Process), which do not support compare

    @overrides
    def put(self, item: typing.Tuple[typing.Any, typing.Any], block=True, timeout=None):
        """
        Adds an item to the queue with the given priority.
        This method overrides the put method of the base class.
        :param item must be a tuple where the first element is sorted key, and the second is data
        """
        with self.condition:
            # print(f"item：{item}")
            # q.put(Task('Medium priority task', 3), priority=partial(lambda task: task.priority))
            super().put(item, block=block, timeout=timeout)
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
            _, item = super().get(block=block, timeout=timeout)
            return item if not isinstance(item, tuple) else item[1]




def _check_is_validate_process(process: Process, machine_no: int) -> bool:
    return True


def execute_process_mock(process: Process) -> typing.Generator:
    if process.stage >= len(process.priority.process_time_list):
        return
    cur_stage = process.stage
    next_stage = cur_stage + 1
    process.stage = next_stage
    origin_process_time = process.get_origin_cur_process_time()
    if origin_process_time is None:
        return
    actual_process_time = _compute_actual_processing_time(expected_time=origin_process_time)
    if origin_process_time is None:
        return
    cur_time = machine_resource.env.now
    waiting_time = cur_time - process.arrival_time
    process.arrival_time = cur_time + actual_process_time
    print(f"waiting_time:{waiting_time}, execute_time:{actual_process_time}, process:{process}")
    schedule_info: ScheduleInfo = ScheduleInfo(round_id=round_uuid,
                                               priority=process.priority.name,
                                               waiting_time=waiting_time,
                                               actual_execute_time=actual_process_time,
                                               origin_execute_time=origin_process_time)
    __save_schedule_info(schedule_info=schedule_info)
    with lock:
        print(f"runnable_process.stage:{process.stage}")
        if process.stage < len(process.priority.process_time_list):
            process_schedule_blocked_queue.put(
                item=(process.get_arrive_time_priority_sort_key(), process))
    # print(f"actual_process_time {actual_process_time}: Process {process.name} with priority {process.priority}")
    yield machine_resource.env.timeout(delay=actual_process_time)


def __save_schedule_info(schedule_info: ScheduleInfo):
    try:
        session.add(schedule_info)
        session.commit()
    except Exception as e:
        print(f"e:{e}")
        traceback.print_exception(e)
        session.rollback()


class Machine(object):
    """
    the machine object which is the unit to execute sub-task
    """
    priority_blocking_queue: PriorityBlockingQueue[Process] = PriorityBlockingQueue()
    mutex: threading.Lock = threading.Lock()

    def __init__(self, resource: simpy.Resource, machine_no: int):
        self.resource: simpy.Resource = resource
        self.machine_no: int = machine_no

    def add_runnable_process(self, process: Process) -> typing.Generator:
        if not _check_is_validate_process(process=process, machine_no=self.machine_no):
            return
        runnable_process: typing.Union[None, Process] = None
        with self.mutex:
            self.priority_blocking_queue.put(item=(process.get_sort_key(), process))
            runnable_process = self.priority_blocking_queue.get()
        if runnable_process is not None:
            # after executing update time
            if not _check_is_validate_process(process=runnable_process, machine_no=self.machine_no):
                return
            with self.resource.request() as request:
                yield request
                yield from execute_process_mock(process=runnable_process)


class MachineResource(object):
    """
    the computing resources in a machine
    """
    resource_map_lock = threading.Lock()

    def __init__(self, env: simpy.Environment, num_machine: int):
        self.env: simpy.Environment = env
        self.resource_map: typing.Dict[int, Machine] = {}
        min_machine_no, max_machine_no = TaskType.get_min_and_max_machine_no()
        for i in range(min_machine_no, max_machine_no + 1):
            self.resource_map[i] = Machine(resource=simpy.Resource(env, 2), machine_no=i)

    def get_machine(self, machine_no: typing.Union[int, str]) -> Machine:
        """

        :param machine_no:
        :return: corresponding machine resource according to machine no
        """
        if not self.resource_map.get(machine_no):
            with self.resource_map_lock:
                if not self.resource_map.get(machine_no):
                    self.resource_map[machine_no] = Machine(resource=simpy.Resource(self.env, 1),
                                                            machine_no=machine_no)
        return self.resource_map.get(machine_no)


def _generate_machine_resource(env: simpy.Environment, num_machine: int = 1) -> bool:
    global machine_resource
    if machine_resource is not None:
        return False
    with machine_generate_lock:
        machine_resource = MachineResource(env=env, num_machine=num_machine)
        return True
    return False


process_schedule_blocked_queue: typing.Optional[PriorityBlockingQueue[Process]] = None
lock = threading.Lock()
# singleton
machine_resource: typing.Union[None, MachineResource] = None
machine_generate_lock: threading.Lock = threading.Lock()

processing_task_dict: typing.Dict[str, typing.Dict[str, Process]] = {
    TaskType.LOW.name: {},
    TaskType.MIDDLE.name: {},
    TaskType.HIGH.name: {}
}
processing_task_mutex: threading.Lock = threading.Lock()


def _convert_list_to_priority_blocking_queue(data: typing.Iterable[Process]) -> PriorityBlockingQueue[Process]:
    pq: PriorityBlockingQueue[Process] = PriorityBlockingQueue()
    for process in data:
        pq.put(item=(process.get_sort_key(), process))
    return pq


def _convert_list_to_priority_blocking_queue_sorted_by_arr_time(data: typing.Iterable[Process]) -> \
        PriorityBlockingQueue[Process]:
    pq: PriorityBlockingQueue[Process] = PriorityBlockingQueue()
    for process in data:
        pq.put(item=(process.get_arrive_time_priority_sort_key(), process))
    return pq


EXAMPLE_LOW_PRIORITY_PROCESS: typing.List[Process] = [Process("low-priority-process1", 1, 10, TaskType.LOW)]
# EXAMPLE_LOW_PRIORITY_PROCESS: typing.List[Process] = [Process("low-priority-process1", 1, 10, TaskType.LOW),
#                                                       Process("low-priority-process2", 4, 15, TaskType.LOW),
#                                                       Process("low-priority-process3", 6, 20, TaskType.LOW),
#                                                       Process("low-priority-process4", 3, 5, TaskType.LOW),
#                                                       Process("low-priority-process5", 9, 10, TaskType.LOW)]
EXAMPLE_MIDDLE_PRIORITY_PROCESS: typing.List[Process] = [Process("middle-priority-process1", 2, 12, TaskType.MIDDLE)]
# EXAMPLE_MIDDLE_PRIORITY_PROCESS: typing.List[Process] = [Process("middle-priority-process1", 2, 12, TaskType.MIDDLE),
#                                                          Process("middle-priority-process2", 5, 8, TaskType.MIDDLE),
#                                                          Process("middle-priority-process3", 7, 18, TaskType.MIDDLE),
#                                                          Process("middle-priority-process4", 9, 10, TaskType.MIDDLE),
#                                                          Process("middle-priority-process5", 6, 22, TaskType.MIDDLE),
#                                                          Process("middle-priority-process5", 10, 15, TaskType.MIDDLE)]
EXAMPLE_HIGH_PRIORITY_PROCESS: typing.List[Process] = [Process("high-priority-process1", 3, 9, TaskType.HIGH)]


# EXAMPLE_HIGH_PRIORITY_PROCESS: typing.List[Process] = [Process("high-priority-process1", 3, 9, TaskType.HIGH),
#                                                        Process("high-priority-process2", 8, 11, TaskType.HIGH),
#                                                        Process("high-priority-process3", 1, 10, TaskType.HIGH),
#                                                        Process("high-priority-process4", 7, 14, TaskType.HIGH),
#                                                        Process("high-priority-process5", 5, 7, TaskType.HIGH),
#                                                        Process("middle-priority-process5", 11, 12, TaskType.MIDDLE)]


def _load_hierarchical_process_list(is_default: bool = True, level: int = 3, process_number: int = 1000) \
        -> PriorityBlockingQueue[Process]:
    """
    load hierarchical process list
    :param is_default: is to return the default examoles <a href="https://canvas.nus.edu.sg/courses/53202/files/folder/2_CA_Assignments?preview=3407585" />
    :param level:  the total level of priority for process types
    :param process_number: the number of tasks in each type
    :return:
    """
    if is_default:
        return _convert_list_to_priority_blocking_queue_sorted_by_arr_time(data=EXAMPLE_LOW_PRIORITY_PROCESS
                                                                                + EXAMPLE_MIDDLE_PRIORITY_PROCESS
                                                                                + EXAMPLE_HIGH_PRIORITY_PROCESS)

    return _convert_list_to_priority_blocking_queue_sorted_by_arr_time(data=generate_process_list(num_tasks=process_number))


def __check_is_remaining_process(hierarchical_processes: PriorityBlockingQueue[Process]) -> bool:
    """
    check is there a proces in hierarchical_processes
    :param hierarchical_processes:
    :return: {@code True} there is at least a process
    {@code False} Otherwise
    """
    if hierarchical_processes and hierarchical_processes.qsize() != 0:
        return True
    count = 0
    while True:
        print(f"waiting new tasks to distribute, hierarchical_processes:{hierarchical_processes.qsize()}")
        time.sleep(1)
        count += 1
        if hierarchical_processes and hierarchical_processes.qsize() != 0:
            return True
    # read without lock
    # # TODO: make sure add to the dict then delete from hierarchical_processes
    # for key, value in processing_task_dict:
    #     if value is not None and len(value) > 0:
    #         return True
    # return False


def __allocate_process_task(process: Process):
    # cur_machine_no = process.stage
    with process.stage_op_lock:
        if process.stage >= len(process.priority.machine_sequence):
            return
        cur_machine_no = process.priority.machine_sequence[process.stage]
        if not _check_is_validate_process(process=process, machine_no=cur_machine_no):
            return
        else:
            try:
                cur_machine: Machine = machine_resource.get_machine(machine_no=cur_machine_no)
                machine_resource.env.process(cur_machine.add_runnable_process(process=process))
            except Exception as e:
                traceback.print_exception(e)
                raise e


def __generate_random_r() -> float:
    """
    generate the R random of the model of Actual Processing time of tasks
    k = Ti,k*(1+R)
    :return: the random value of R beterrn 0.1% == 0.001, 0.7% == 0.007
    """
    return random.uniform(R_RANDOM_MIN, R_RANDOM_MAX)


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

def pop_process(hierarchical_processes: PriorityBlockingQueue[Process]):
    print(f"enter into pop process func")
    # record the time when submit previous process
    pre_arrive_time: int = machine_resource.env.now
    while __check_is_remaining_process(hierarchical_processes):
        now_time = machine_resource.env.now
        # pop the miniOne
        most_recent_process: typing.Union[None, Process] = None
        try:
            most_recent_process = hierarchical_processes.get(timeout=1)
        except Exception as e:
            traceback.print_exception(e)
        if most_recent_process is None:
            time.sleep(SELF_ROTATE_TIME)
            continue
        # use pysim to add the process into system
        yield machine_resource.env.timeout(max(most_recent_process.arrival_time - machine_resource.env.now, 0))
        pre_arrive_time = most_recent_process.arrival_time
        if most_recent_process is not None:
            gevent.spawn(_submit_process_into_machine, **{
                "submit_process": most_recent_process
            }).run()


def _submit_process_into_machine(submit_process: Process):
    print(f"submit_process:{submit_process.__dict__}")
    if submit_process is not None:
        is_success = False
        count = 0
        while not is_success and count < 10:
            try:
                __allocate_process_task(process=submit_process)
                is_success = True
                count += 1
            except Exception as e:
                traceback.print_exception(e)
                is_success = False
        if count == 10:
            print(f"task submit error process:{submit_process}")


def main():
    random.seed(42)
    env: simpy.Environment = simpy.Environment()
    machine_number = int(input("please input the number of available machine: ").strip())
    process_number = int(input("please input process_number: ").strip())

    _generate_machine_resource(env=env, num_machine=machine_number)
    processes_list: PriorityBlockingQueue[Process] = _load_hierarchical_process_list(is_default=False, process_number=process_number)
    global process_schedule_blocked_queue
    process_schedule_blocked_queue = processes_list
    machine_resource.env.process(pop_process(hierarchical_processes=process_schedule_blocked_queue))
    machine_resource.env.run(until=sys.maxsize)


main()
