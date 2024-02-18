# one available resources for each machine
# round_ uuid:round_uuid:2024-02-18 12:46:39 process_number:1000
select * from embedded_system.schedule_info where round_id='2024-02-18 12:46:39';

select count(id) as total_count, avg(waiting_time) as average_waiting_time from embedded_system.schedule_info where round_id='2024-02-18 04:39:43';
select count(id) as total_count, avg(waiting_time) as average_waiting_time,
       avg(waiting_time/origin_execute_time) as avg_wait_time_to_origin_exec_percentage,
       avg(waiting_time/actual_execute_time) as avg_wait_time_to_actual_exec_percentage,
       priority,
       machine_no
from embedded_system.schedule_info
where round_id='2024-02-18 04:39:43' group by priority, machine_no;

# two available resource for each machine
# round_uuid 2024-02-18 04:11:14 process_number:1000

