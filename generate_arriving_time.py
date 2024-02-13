import random


def generate_arrival_times(num_tasks, arrival_rate):
    arrival_times = []
    time = 0
    for _ in range(num_tasks):
        # 生成指数分布的随机数，代表到达时间间隔
        interval = random.expovariate(arrival_rate)
        time += interval
        arrival_times.append(time)
    return arrival_times


# 定义任务数量和到达率
num_tasks = 1000
arrival_rate = 0.1  # 到达率，即单位时间内平均到达的任务数量

# 生成一批任务的到达时间
arrival_times = generate_arrival_times(num_tasks, arrival_rate)

# 打印任务到达时间
print(arrival_times)
for arr_time in arrival_times:

