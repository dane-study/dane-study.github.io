load 'plots/style.gnu'

set datafile separator ","

set grid
set xdata time
set timefmt "%Y%m%d %H"

set ylabel "{/Helvetica-Bold % of }{/Courier-Bold TLSA }{/Helvetica-Bold records}\n{/Helvetica-Bold that fails validation}" #offset 0, 8
set xlabel "{/Helvetica-Bold Date}"
set xrange["20190711 01":"20191101 01"]
set xtics 3600 * 24 * 14
set format x "%m/%d"
#set ytics 0.2
set yrange[0:20]
set key center right
#set label "{/Helvetica-Bold DNSSEC}" at "20190713 01", 0.1

#time, totalDn, noData, bogus, wrongChain, usage2, usage3, undefined, selector, matchingType, notmatch-tlsa-certificate
#TLSA Errors: Wrong usage,  selector, undefined
plot \
"data/check-incorrect-stat-virginia.txt" u 1:(100*$4/($2-$3)) w  st linestyle 1 lw 3  title "DNSSEC",\
"data/check-incorrect-stat-virginia.txt" u 1:(100*($5+$6+$7+$8+$9+$10+$11)/($2-$3)) w  st linestyle 2 lw 3  title "Certificate"
