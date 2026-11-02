create_clock -name clk_i -period 0.1000 [get_ports clk_i]
set_input_delay 0 -clock clk_i [delete_from_list [all_inputs] [get_ports clk_i]]
set_output_delay 0 -clock clk_i [all_outputs]
