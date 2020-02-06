load 'plots/style.gnu'
set datafile separator ","

set lmargin 10

set size 0.6, 0.6
set multiplot
set grid
set xdata time
set timefmt "%Y-%m-%d"
set xrange["2017-10-22":"2019-10-31"]
set key top  left 
set format x "%m/%y"
set yrange [0:]

set xtics 3600 * 24 * 30 * 3

set size 0.6, 0.35
set origin 0, 0

set xlabel ""
set ylabel "{/Helvetica-Bold % of domains with }{/Courier-Bold TLSA }{/Helvetica-Bold records}" offset 0, 5

#set arrow from "2018-11-23", 0 to "2018-11-23",0.8 lw 3 lt 0 nohead

set arrow from "2018-04-20", 0.25 to "2018-05-10", 0.25
set label "{active24.cz}" at "2017-11-01", 0.25

plot\
"data/tlsa-counts.csv" u 1:(100*($3/$2)) w st linestyle 1 lw 3 title "{/Courier-Bold .com}",\
"data/tlsa-counts.csv" u 1:(100*($8/$7)) w st linestyle 2 lw 3 title "{/Courier-Bold .net}",\
"data/tlsa-counts.csv" u 1:(100*($13/$12)) w st linestyle 3 lw 3 title "{/Courier-Bold .org}",\


set xtics()
unset label
set origin 0, 0.32
set size 0.6, 0.29
set xlabel ""
set ylabel ""
set format x ""
#set arrow from "2018-11-23", 0 to "2018-11-23",40 lw 3 lt 0 nohead
set arrow from "2018-10-23", 17.5 to "2018-11-20", 17.5
set label "{one.com}" at "2018-06-11", 17.5

set arrow from "2019-08-23", 32.5 to "2019-09-20", 32.5
set label "{loopia.se}" at "2019-04-11", 32.5

#set label "{/Courier One.com }{/Helvetica-Bold published a }\n{/Courier-Bold TLSA }{/Helvetica-Bold record}" at "2018-04-11", 20

plot "data/tlsa-counts.csv" u 1:(100*($18/$17)) w st linestyle 4 lw 3 title "{/Courier-Bold .nl}",\
    "data/tlsa-counts.csv" u 1:(100*($23/$22)) w st linestyle 5 lw 3 title "{/Courier-Bold .se}"


