create_clock -name i_wb_clk -period 0.5200 [get_ports i_wb_clk]
create_clock -name i_xclk_clk -period 0.4900 [get_ports i_xclk_clk]
set_clock_groups -asynchronous -group {i_wb_clk} -group {i_xclk_clk}
