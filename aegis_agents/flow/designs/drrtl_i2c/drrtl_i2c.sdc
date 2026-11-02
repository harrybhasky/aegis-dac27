create_clock -name wb_clk_i -period 0.1000 [get_ports wb_clk_i]
set_input_delay 0 -clock wb_clk_i [delete_from_list [all_inputs] [get_ports wb_clk_i]]
set_output_delay 0 -clock wb_clk_i [all_outputs]
