create_clock -name i_rclk -period 0.4600 [get_ports i_rclk]
create_clock -name i_wclk -period 0.4000 [get_ports i_wclk]
set_clock_groups -asynchronous -group {i_wclk} -group {i_rclk}
