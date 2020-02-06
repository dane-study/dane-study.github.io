load 'plots/style.gnu'
set datafile separator "\t"

set tmargin 3
set lmargin 11.5

set grid 
set size 0.6, 0.9 # 1, 0.4 
set multiplot

set grid 
set xdata time
set timefmt "%Y%m%d"
#set key outside right
set key top left
set format x "%Y%m%d"
set xrange ["20110101": "20190401"]
set xtics ("2011" "20110101", "2012" "20120101", "2013" "20130101", "2014" "20140101", "2015" "20150101", "2016" "20160101", "2017" "20170101", "2018" "20180101", "2019" "20190101")
#set xtics 3600 * 24 * 365
#set yrange [0:11]


set tmargin 0
set size 0.6, 0.33
set origin 0, 0
set xlabel "{/Helvetica-Bold Date}"
set colorsequence default
set ytics 10
set ylabel "{/Helvetica-Bold % of IPv4s}\n{/Helvetica-Bold authorized by VRP}\n\n"

plot "data/roas-covering-IPcnt-ipv4/roas-covering-IPcnt-ipv4.tsv" u 1:($2/($3 == 0 ? 0: $3) * 100) w st linestyle 1  lw 5 title "",\
     "data/roas-covering-IPcnt-ipv4/roas-covering-IPcnt-ipv4.tsv" u 1:($4/($5 == 0 ? 0: $5) * 100) w st linestyle 2  lw 5 title "",\
     "data/roas-covering-IPcnt-ipv4/roas-covering-IPcnt-ipv4.tsv" u 1:($6/($7 == 0 ? 0: $7) * 100) w st linestyle 3  lw 5 title "",\
     "data/roas-covering-IPcnt-ipv4/roas-covering-IPcnt-ipv4.tsv" u 1:($8/($9 == 0 ? 0: $9) * 100) w st linestyle 4  lw 5 title "",\
     "data/roas-covering-IPcnt-ipv4/roas-covering-IPcnt-ipv4.tsv" u 1:($10/($11 == 0 ? 0: $11) * 100) w st linestyle 5  lw 5 title "",\


set xtics()
unset label
set tmargin 0
set size 0.6, 0.27
set origin 0, 0.33
set xlabel ""
set ylabel ""
set format x ""
set ylabel "{/Helvetica-Bold % of ASes }\n{/Helvetica-Bold authorized by VRP}\n\n"
set colorsequence default
set ytics 5

plot "data/roas-covering-AScnt-ipv4/roas-covering-AScnt-ipv4.tsv" u 1:($2/($3 == 0 ? 0: $3) * 100) w st linestyle 1  lw 5 title "",\
     "data/roas-covering-AScnt-ipv4/roas-covering-AScnt-ipv4.tsv" u 1:($4/($5 == 0 ? 0: $5) * 100) w st linestyle 2  lw 5 title "",\
     "data/roas-covering-AScnt-ipv4/roas-covering-AScnt-ipv4.tsv" u 1:($6/($7 == 0 ? 0: $7) * 100) w st linestyle 3  lw 5 title "",\
     "data/roas-covering-AScnt-ipv4/roas-covering-AScnt-ipv4.tsv" u 1:($8/($9 == 0 ? 0: $9) * 100) w st linestyle 4  lw 5 title "",\
     "data/roas-covering-AScnt-ipv4/roas-covering-AScnt-ipv4.tsv" u 1:($10/($11 == 0 ? 0: $11) * 100) w st linestyle 5  lw 5 title "",\

unset label
set size 0.6, 0.27
set origin 0, 0.60
set xlabel ""
set ylabel ""
set key top left
set ytics 10000
set format x ""
set ylabel "{/Helvetica-Bold \# of VRP}\n{/Helvetica-Bold IP Prefixes (IPv4)}"
set colorsequence default

plot "data/vrp-growth/vrp-growth.tsv" u 1:($2+$3+$4+$5+$6+$7) w st linestyle 1  lw 5 title "APNIC",\
     "data/vrp-growth/vrp-growth.tsv" u 1:8 w st linestyle 2  lw 5 title "LACNIC",\
     "data/vrp-growth/vrp-growth.tsv" u 1:9 w st linestyle 3  lw 5 title "RIPENCC",\
     "data/vrp-growth/vrp-growth.tsv" u 1:10 w st linestyle 4  lw 5 title "ARIN",\
     "data/vrp-growth/vrp-growth.tsv" u 1:11 w st linestyle 5  lw 5 title "AFRINIC",\
