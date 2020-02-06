#   date, non-rpki, rpki-invalid, rpki-valid
load 'plots/style.gnu'
set datafile separator "\t"


set tmargin 1
set lmargin 12

set grid 
set size 0.6, 0.75
set multiplot

set xdata time
set timefmt "%Y%m%d"
set key top right
set format x "%Y%m%d"
set xrange ["20110101": "20190201"]
set xtics ("2011" "20110101", "2012" "20120101", "2013" "20130101", "2014" "20140101", "2015" "20150101", "2016" "20160101", "2017" "20170101", "2018" "20180101", "2019" "20190101")
#set xtics 3600 * 24 * 365
#set yrange [0:11]

set size 0.6, 0.3
set origin 0, 0
set xlabel "{/Helvetica-Bold Date}"
set ylabel "{/Helvetica-Bold The number of BGP announcements}\n{/Helvetica-Bold having a wrong ASN}" offset 0, 10
set colorsequence default
set yrange [0:3000]
set ytics 500
# time, valid, hijacking, misconfiguration, sub-hijack, all-invalid-bgp-announcement
set label "{/Courier-Bold Routeviews }" at "20110301", 2750
plot "data/rpki-unique-prefix-classify-hijack-ipv4/routeviews.tsv" u 1:($2) w st linestyle 1 title "",\
     "data/rpki-unique-prefix-classify-hijack-ipv4/routeviews.tsv" u 1:(($3+$4+$5)) w st linestyle 2 title "",\
     "data/rpki-unique-prefix-classify-hijack-ipv4/routeviews.tsv" u 1:($6) w st linestyle 3 title "",\
"data/rpki-unique-prefix-classify-hijack-ipv4/routeviews.tsv" u 1:($7) w st linestyle 4 title "",\
#plot "data/rpki-unique-prefix-classify-hijack-ipv4/routeviews.tsv" u 1:($3/$6 * 100) w points pt 1 ps 0.5 lc rgb "#85bcff" title "",\
     #"data/rpki-unique-prefix-classify-hijack-ipv4/routeviews.tsv" u 1:($4/$6 * 100) w points pt 7 ps 0.5 lc rgb "#b5001a" title "",\
     #"data/rpki-unique-prefix-classify-hijack-ipv4/routeviews.tsv" u 1:($5/$6 * 100) w points pt 14 ps 0.5 lc rgb "#00b200" title "",\



set xtics ()
unset label
set size 0.6, 0.25
set origin 0, 0.27
set xlabel ""
set ylabel ""
set format x ""
set ytics 500
set yrange [0:3000] 
set label "{/Courier-Bold RIPE-RIS }" at "20110301", 2750
plot "data/rpki-unique-prefix-classify-hijack-ipv4/ripe-ris.tsv" u 1:($2) w st linestyle 1 title "",\
     "data/rpki-unique-prefix-classify-hijack-ipv4/ripe-ris.tsv" u 1:(($3+$4+$5)) w st linestyle 2 title "",\
     "data/rpki-unique-prefix-classify-hijack-ipv4/ripe-ris.tsv" u 1:($6) w st linestyle 3 title "",\
    "data/rpki-unique-prefix-classify-hijack-ipv4/ripe-ris.tsv" u 1:($7) w st linestyle 4 title "",\


unset label
set size 0.6, 0.25
set origin 0, 0.50
set xlabel ""
set ylabel ""
set key bottom left
set format x ""
unset yrange
set ytics 500
set yrange [0:3000]
set label "{/Courier-Bold Akamai}" at "20110301", 2750
plot    "data/rpki-unique-prefix-classify-hijack-ipv4/akamai-public-prefix.tsv" u 1:($2) w st linestyle 1 title "Same ISP",\
    "data/rpki-unique-prefix-classify-hijack-ipv4/akamai-public-prefix.tsv" u 1:(($3+$4+$5)) w st linestyle 2 title "P-C or C-P",\
    "data/rpki-unique-prefix-classify-hijack-ipv4/akamai-public-prefix.tsv" u 1:($6) w st linestyle 3 title "DDoS Protection",\
    "data/rpki-unique-prefix-classify-hijack-ipv4/akamai-public-prefix.tsv" u 1:($7) w st linestyle 4 title "Other",\


unset multiplot

