create_clock -name a_clk_i -period 0.3100 [get_ports a_clk_i]
create_clock -name b_clk_i -period 0.3100 [get_ports b_clk_i]
set_clock_groups -asynchronous -group {a_clk_i} -group {b_clk_i}
