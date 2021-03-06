load 'plots/style.gnu'

set grid
set datafile separator "\t"
set size 0.6, 0.35

set ylabel "{/Helvetica-Bold CDF}"
set xlabel "{/Helvetica-Bold # of Victim ASes}"
set yrange["0":"1"]
set xrange["1":"10"]
set ytics 0.1
set key bottom right
plot "data/rpki-unique-prefix-hijack-ipv4-None-pairs/akamai-public-prefix-attacker-cnt-byAS.txt"  u 1:($2) w st linestyle 1 lw 5 title "{/Courier-Bold Akamai}",\
     "data/rpki-unique-prefix-hijack-ipv4-None-pairs/ripe-ris-attacker-cnt-byAS.txt"  u 1:($2) w st linestyle 2 lw 5 title "{/Courier-Bold RIPE-RIS}",\
     "data/rpki-unique-prefix-hijack-ipv4-None-pairs/routeviews-attacker-cnt-byAS.txt"  u 1:($2) w st linestyle 3 lw 5 title "{/Courier-Bold RouteViews}",\
