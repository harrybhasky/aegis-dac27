create_clock -name clk_in -period 0.5600 [get_ports clk_in]
create_clock -name clk_out -period 0.5900 [get_ports clk_out]
set_clock_groups -asynchronous -group {clk_in} -group {clk_out}
