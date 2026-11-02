create_clock -name clk_in -period 0.1000 [get_ports clk_in]
set_input_delay 0 -clock clk_in [delete_from_list [all_inputs] [get_ports clk_in]]
set_output_delay 0 -clock clk_in [all_outputs]
