create_clock -name M_APB_PCLK -period 0.2400 [get_ports M_APB_PCLK]
create_clock -name S_APB_PCLK -period 0.1900 [get_ports S_APB_PCLK]
set_clock_groups -asynchronous -group {S_APB_PCLK} -group {M_APB_PCLK}
