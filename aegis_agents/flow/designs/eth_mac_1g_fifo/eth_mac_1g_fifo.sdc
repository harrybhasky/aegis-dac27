create_clock -name logic_clk -period 0.9900 [get_ports logic_clk]
create_clock -name rx_clk -period 0.5600 [get_ports rx_clk]
create_clock -name tx_clk -period 1.0300 [get_ports tx_clk]
set_clock_groups -asynchronous -group {rx_clk} -group {tx_clk} -group {logic_clk}
