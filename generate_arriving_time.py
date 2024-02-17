import typing

import numpy
from data_model import Process, TaskType

def _generate_arrival_times(num_tasks: int, average_rate: int = 10) -> typing.Iterable[typing.Union[int, float]]:
    numpy.random.seed(42)

    arrival_times = numpy.random.poisson(average_rate, num_tasks)

    print(arrival_times)
    return arrival_times


def generate_process_list(num_tasks: int,
                          rate_map=None) -> typing.List[Process]:
    if rate_map is None:
        rate_map = {TaskType.LOW.name: 1, TaskType.MIDDLE.name: 1, TaskType.HIGH.name: 1}
    arrive_time_list: typing.Iterable[typing.Union[int, float]] = _generate_arrival_times(num_tasks=num_tasks)
    process_list: typing.List[Process] = []
    cur_type = TaskType.LOW
    cur_count = rate_map.get(cur_type.name)
    total_count = 0
    for arrive_time in arrive_time_list:
        while cur_count == 0:
            cur_type = _get_next_type(cur_type=cur_type)
            cur_count = rate_map.get(cur_type.name)
        process_list.append(Process(name=f"priority-{cur_type.name}-{total_count}",
                                    arrival_time=arrive_time,
                                    service_time=1,
                                    priority=cur_type))
        total_count += 1
        cur_count -= 1
        # process_list.append(Process(name=))
    for p in process_list:
        print(f"process:{p.__dict__}")
    return process_list


def _get_next_type(cur_type: TaskType):
    if TaskType.LOW == cur_type:
        return TaskType.MIDDLE
    if TaskType.MIDDLE == cur_type:
        return TaskType.HIGH
    else:
        return TaskType.LOW
