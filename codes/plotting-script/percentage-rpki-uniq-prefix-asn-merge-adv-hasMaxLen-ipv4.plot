#   date, non-rpki, rpki-unique-prefix-asn-invalid, rpki-unique-prefix-asn-valid
load 'plots/style.gnu'
set datafile separator "\t"

set tmargin 0
set lmargin 10

set grid 
set size 0.6, 0.7 # 1, 0.4 
set multiplot


set grid 
set xdata time
set timefmt "%Y%m%d"
set format x "%Y%m%d"
set xrange ["20110101": "20190201"]
set xtics ("2011" "20110101", "2012" "20120101", "2013" "20130101", "2014" "20140101", "2015" "20150101", "2016" "20160101", "2017" "20170101", "2018" "20180101", "2019" "20190101")
#set xtics 3600 * 24 * 365
set yrange [0:100]
#
set size 0.6, 0.36
set origin 0, 0

set xlabel "{/Helvetica-Bold Date}"
set ylabel "{/Helvetica-Bold % of Too-specific Adv.}\n{/Helvetica-Bold w/o} {/Courier-Bold MaxLen}"
set key bottom center  
set colorsequence default

plot "data/rpki-unique-prefix-asn-misconf-adv-hasMaxLen-ipv4/akamai-public-prefix.tsv" u 1:($3/($2 + $3) * 100) w st linestyle 1 title "",\
     "data/rpki-unique-prefix-asn-misconf-adv-hasMaxLen-ipv4/ripe-ris.tsv" u 1:($3/($3+$2) * 100) w st linestyle 2 title "",\
     "data/rpki-unique-prefix-asn-misconf-adv-hasMaxLen-ipv4/routeviews.tsv" u 1:($3/($3+$2) * 100) w st linestyle 3 title "",\
    "data/rpki-unique-prefix-asn-misconf-adv-hasMaxLen-ipv4/akamai-public-prefix.tsv" u 1:($3/($2 + $3) * 100) w st linestyle 1 title "",\


unset label
set size 0.6, 0.33
set origin 0, 0.36
set xtics()
set key top left
set xlabel ""
set format x ""
set ylabel "{/Helvetica-Bold % of Valid Adv.}\n{/Helvetica-Bold w/o} {/Courier-Bold MaxLen}"
set xtics
plot "data/rpki-unique-prefix-asn-valid-adv-hasMaxLen-ipv4/akamai-public-prefix.tsv" u 1:($3/($2 + $3) * 100) w st linestyle 1 title "{/Courier-Bold Akamai}",\
    "data/rpki-unique-prefix-asn-valid-adv-hasMaxLen-ipv4/ripe-ris.tsv" u 1:($3/($3+$2) * 100) w st linestyle 2 title "{/Courier-Bold RIPE-RIS}",\
    "data/rpki-unique-prefix-asn-valid-adv-hasMaxLen-ipv4/routeviews.tsv" u 1:($3/($3+$2) * 100) w st linestyle 3 title "{/Courier-Bold RouteViews}",\
    "data/rpki-unique-prefix-asn-valid-adv-hasMaxLen-ipv4/akamai-public-prefix.tsv" u 1:($3/($2 + $3) * 100) w st linestyle 1 title "",\

