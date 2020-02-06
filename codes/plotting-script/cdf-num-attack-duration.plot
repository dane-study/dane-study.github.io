load 'plots/style.gnu'

set tmargin 1
set lmargin 4
set grid
set size 0.6, 0.75
set multiplot
set datafile separator "\t"

set size 0.6, 0.3
set origin 0, 0
set ylabel "{/Helvetica-Bold CDF}"
set xlabel "{/Helvetica-Bold # of Dates Observed }"
set yrange["0":"1"]
set xrange["1":"1000"]
set ytics 0.2
set label "{/Courier-Bold RouteViews}" at 11, 0.1
plot "data/rpki-unique-prefix-classify-hijack-duration-ipv4/cdf-routeviews-sameISP.txt"  u 1:2 w st linestyle 1 lw 5 title"", \
    "data/rpki-unique-prefix-classify-hijack-duration-ipv4/cdf-routeviews-customer.txt"  u 1:2 w st linestyle 2 lw 5 title"", \
    "data/rpki-unique-prefix-classify-hijack-duration-ipv4/cdf-routeviews-None.txt"  u 1:2 w st linestyle 4 lw 5 title"", \



set xtics ()
unset label
set size 0.6, 0.25
set origin 0, 0.27
set xlabel ""
set ylabel ""
set format x ""
set label "{/Courier-Bold RIPE-RIS}" at 11, 0.1
plot "data/rpki-unique-prefix-classify-hijack-duration-ipv4/cdf-ripe-ris-sameISP.txt"  u 1:2 w st linestyle 1 lw 5 title"", \
    "data/rpki-unique-prefix-classify-hijack-duration-ipv4/cdf-ripe-ris-customer.txt"  u 1:2 w st linestyle 2 lw 5 title"", \
    "data/rpki-unique-prefix-classify-hijack-duration-ipv4/cdf-ripe-ris-None.txt"  u 1:2 w st linestyle 4 lw 5 title"", \

unset label
set size 0.6, 0.25
set origin 0, 0.50
set xlabel ""
set ylabel ""
set key bottom right
set format x ""
set label "{/Courier-Bold Akamai}" at 11, 0.1
plot "data/rpki-unique-prefix-classify-hijack-duration-ipv4/cdf-akamai-public-prefix-sameISP.txt"  u 1:2 w st linestyle 1 lw 5 title"Same ISP", \
    "data/rpki-unique-prefix-classify-hijack-duration-ipv4/cdf-akamai-public-prefix-customer.txt"  u 1:2 w st linestyle 2 lw 5 title"P-C or C-P", \
    "data/rpki-unique-prefix-classify-hijack-duration-ipv4/cdf-akamai-public-prefix-None.txt"  u 1:2 w st linestyle 4 lw 5 title "Other", \

unset multiplot

