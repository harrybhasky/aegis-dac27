create_clock -name clk_dst_i -period 0.1000 [get_ports clk_dst_i]
create_clock -name clk_src_i -period 0.1300 [get_ports clk_src_i]
set_clock_groups -asynchronous -group {clk_src_i} -group {clk_dst_i}
