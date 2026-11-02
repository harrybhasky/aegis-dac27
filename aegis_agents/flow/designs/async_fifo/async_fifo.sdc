create_clock -name rclk -period 0.4800 [get_ports rclk]
create_clock -name wclk -period 0.3700 [get_ports wclk]
set_clock_groups -asynchronous -group {wclk} -group {rclk}
