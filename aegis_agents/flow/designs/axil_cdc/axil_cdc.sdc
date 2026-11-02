create_clock -name m_clk -period 0.2800 [get_ports m_clk]
create_clock -name s_clk -period 0.2900 [get_ports s_clk]
set_clock_groups -asynchronous -group {s_clk} -group {m_clk}
