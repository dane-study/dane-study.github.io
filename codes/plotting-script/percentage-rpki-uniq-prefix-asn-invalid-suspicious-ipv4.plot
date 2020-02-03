#   date, non-rpki, rpki-invalid, rpki-valid
load 'plots/style.gnu'
set datafile separator "\t"

set grid 
set xdata time
set timefmt "%Y%m%d"
set key top left
set format x "%Y%m%d"
set xrange ["20110101": "20190201"]
set xtics ("2011" "20110101", "2012" "20120101", "2013" "20130101", "2014" "20140101", "2015" "20150101", "2016" "20160101", "2017" "20170101", "2018" "20180101", "2019" "20190101")
#set xtics 3600 * 24 * 365
set yrange [0:30]

set xlabel "{/Helvetica-Bold Date}"
set ylabel "{/Helvetica-Bold % of unknown}\n{/Helvetica-Bold of unauthorized Advs.}"
set colorsequence default

plot "data/rpki-unique-prefix-classify-hijack-ipv4/akamai-public-prefix-all.tsv" u 1:(($5 + $7)/$8 * 100) w st linestyle 1 title "{/Courier-Bold Akamai}",\
     "data/rpki-unique-prefix-classify-hijack-ipv4/ripe-ris-all.tsv" u 1:(($5 + $7)/$8 * 100) w st linestyle 2 title "{/Courier-Bold RIPE-RIS}",\
     "data/rpki-unique-prefix-classify-hijack-ipv4/routeviews-all.tsv" u 1:(($5 + $7)/$8 * 100) w st linestyle 3 title "{/Courier-Bold RouteViews}"



