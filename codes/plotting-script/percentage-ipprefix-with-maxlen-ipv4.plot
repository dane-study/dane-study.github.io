#   date, non-rpki, rpki-invalid, rpki-valid
load 'plots/style.gnu'
set datafile separator "\t"

set size 0.6, 0.3
set grid 
set xdata time
set timefmt "%Y%m%d"
#set key outside right
#set key top left
set format x "%Y%m%d"
set xrange ["20110101": "20190201"]
set xtics ("2011" "20110101", "2012" "20120101", "2013" "20130101", "2014" "20140101", "2015" "20150101", "2016" "20160101", "2017" "20170101", "2018" "20180101", "2019" "20190101")
#set xtics 3600 * 24 * 365
set yrange [0:100]

set xlabel "{/Helvetica-Bold Date}"
set ylabel "{/Helvetica-Bold \% of }{/Courier-Bold VRP }{/Helvetica-Bold prefixes}\n{/Helvetica-Bold w/o }{/Courier-Bold MaxLen}"
set colorsequence default

plot "data/roa-prefix-with-maxlength/roa-prefix-with-maxlength.tsv" u 1:($2/($2+$3)*100) w st linestyle 1 lw 5 title ""
