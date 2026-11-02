# test constraints
set PW 0.55
create_clock -name clk_w -period $PW [get_ports clk_w]
create_clock -name clk_r -period 0.9 [get_ports clk_r]
create_clock -name clk_x -period 0.45  [get_ports clk_x]
create_generated_clock -name clk_div -source [get_ports clk_w] -divide_by 2 [get_pins u_div/div_q_reg/Q]
set_clock_groups -asynchronous -group {clk_w clk_div} -group {clk_r}
set_multicycle_path 2 -setup -from [get_cells fast_q_reg*] -to [get_cells slow_q_reg*]
set_clock_uncertainty 0.1 [all_clocks]
