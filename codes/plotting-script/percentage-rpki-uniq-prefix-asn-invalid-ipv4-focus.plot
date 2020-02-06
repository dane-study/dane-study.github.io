#   date, non-rpki, rpki-invalid, rpki-valid
load 'plots/style.gnu'
set datafile separator "\t"

set grid 
set xdata time
set timefmt "%Y%m%d"
set key top right
set format x "%b %Y"
set xrange ["20180201": "20190201"]
#set xtics ("2011" "20110101", "2012" "20120101", "2013" "20130101", "2014" "20140101", "2015" "20150101", "2016" "20160101", "2017" "20170101", "2018" "20180101", "2019" "20190101")
#set xtics ("2011" "20110101", "2012" "20120101", "2013" "20130101", "2014" "20140101", "2015" "20150101", "2016" "20160101", "2017" "20170101", "2018" "20180101", "2019" "20190101")
set xtics 3600 * 24 * 30 * 3
#set yrange [0:100]

set xlabel "{/Helvetica-Bold Date}"
set ylabel "{/Helvetica-Bold Percentage of unique}\n{/Helvetica-Bold RPKI-invalid adv.}"
set colorsequence default

plot "data/rpki-enabled-unique-prefix-asn-adv-ipv4/akamai-public-prefix.tsv" u 1:($3/($4 + $3) * 100) w st linestyle 1 title "{/Courier-Bold Akamai}",\
     "data/rpki-enabled-unique-prefix-asn-adv-ipv4/ripe-ris.tsv" u 1:($3/($3 + $4) * 100) w st linestyle 2 title "{/Courier-Bold RIPE-RIS}",\
     "data/rpki-enabled-unique-prefix-asn-adv-ipv4/routeviews.tsv" u 1:($3/($3 + $4) * 100) w st linestyle 3 title "{/Courier-Bold RouteViews}"


