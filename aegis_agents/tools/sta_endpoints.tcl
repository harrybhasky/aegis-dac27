# AEGIS: dump the worst setup path to every endpoint below the closure margin,
# as an OpenSTA "full" text report that tools/aegis_select.py parses.
#
# Source this after the design is loaded (read_liberty, read_verilog,
# link_design, read_sdc). Environment variables:
#   AEGIS_MARGIN   closure margin in ns (default 0.1)
#   AEGIS_STA_RPT  output file (default sta_endpoints.rpt)
#
# Option names for path counts changed across OpenSTA versions, so both
# spellings are tried. Check the result once against your version: each path
# block must contain "Startpoint:", "Endpoint: ... clocked by <clk>", two
# "clock <name> (rise|fall edge)" lines (launch, then capture), and a
# "slack" line.

set margin 0.1
if {[info exists ::env(AEGIS_MARGIN)]} { set margin $::env(AEGIS_MARGIN) }
set out sta_endpoints.rpt
if {[info exists ::env(AEGIS_STA_RPT)]} { set out $::env(AEGIS_STA_RPT) }

if {[catch {
    report_checks -path_delay max -format full -slack_max $margin \
        -group_path_count 100000 -endpoint_path_count 1 > $out
} err]} {
    puts "newer option names not accepted ($err); trying older names"
    report_checks -path_delay max -format full -slack_max $margin \
        -group_count 100000 -endpoint_count 1 > $out
}
puts "AEGIS: wrote $out (margin $margin ns)"
