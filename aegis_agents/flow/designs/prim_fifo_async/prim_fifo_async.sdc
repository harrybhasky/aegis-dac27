create_clock -name clk_rd_i -period 0.3500 [get_ports clk_rd_i]
create_clock -name clk_wr_i -period 0.3200 [get_ports clk_wr_i]
set_clock_groups -asynchronous -group {clk_wr_i} -group {clk_rd_i}
