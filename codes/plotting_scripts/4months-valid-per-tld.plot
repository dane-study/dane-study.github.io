load 'plots/style.gnu'
set datafile separator ","

set size 0.6, 0.4
set grid
set xdata time
set timefmt "%Y%m%d %H"
set xrange["20190711 01":"20191101 01"]
set key top  left 
set format x "%m/%d"
set yrange [0:3]

set xtics 3600 * 24 * 7 * 2
set xlabel ""
set ylabel "{/Helvetica-Bold % of domains unable to}\n{/Helvetica-Bold support DANE correctly}"

plot\
"data/valid-dn-stat-virginia.txt" u 1:(100*($4/$2)) w st linestyle 1 lw 3 title "{/Courier-Bold .com}",\
"data/valid-dn-stat-virginia.txt" u 1:(100*($7/$5)) w st linestyle 2 lw 3 title "{/Courier-Bold .org}",\
"data/valid-dn-stat-virginia.txt" u 1:(100*($10/$8)) w st linestyle 3 lw 3 title "{/Courier-Bold .net}",\
"data/valid-dn-stat-virginia.txt" u 1:(100*($13/$11)) w st linestyle 4 lw 3 title "{/Courier-Bold .nl}",\
"data/valid-dn-stat-virginia.txt" u 1:(100*($16/$14)) w st linestyle 5 lw 3 title "{/Courier-Bold .se}"
