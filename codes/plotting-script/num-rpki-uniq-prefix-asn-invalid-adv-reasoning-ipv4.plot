#   date, non-rpki, rpki-invalid, rpki-valid
load 'plots/style.gnu'
set datafile separator "\t"

# 0.6 vs. 0.4 * 2
# 1.2 vs. 0.8
set tmargin 1
set lmargin 10

set grid 
#set size 1, 1.2 # 1, 0.4 
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
set ylabel "{/Helvetica-Bold # of Unique Invalid Advertisements}" offset 0, 10
set ytics 4000 
set yrange [0:12000]
set colorsequence default
#set label "(A)" at "20120801", 14000
#set arrow from "20120601",12000 to "20120201",7000

#set label "(B)" at "20170601", 9000
#set arrow from "20180101",9000 to "20180401",7000

#set label "(C)" at "20170601", 15000
#set arrow from "20180101",13000 to "20181001",12000

set label "{/Courier-Bold Routeviews }" at "20110301", 10000
plot    "data/rpki-enabled-unique-prefix-asn-invalid-adv-reasoning-ipv4/routeviews.tsv" u 1:($4) w st linestyle 1 title "",\
        "data/rpki-enabled-unique-prefix-asn-invalid-adv-reasoning-ipv4/routeviews.tsv" u 1:($5+$3) w st linestyle 2 title "",\


set xtics ()
unset arrow
unset label
set size 0.6, 0.25
set origin 0, 0.27
set xlabel ""
set ylabel ""
set format x ""
set yrange [0:6000]
set ytics 2000 
set label "{/Courier-Bold RIPE-RIS }" at "20110301",  5000
plot "data/rpki-enabled-unique-prefix-asn-invalid-adv-reasoning-ipv4/ripe-ris.tsv" u 1:($4) w st linestyle 1 title "",\
     "data/rpki-enabled-unique-prefix-asn-invalid-adv-reasoning-ipv4/ripe-ris.tsv" u 1:($5+$3) w st linestyle 2 title "",\



unset label
set size 0.6, 0.25
set origin 0, 0.50
set xlabel ""
set ylabel ""
set key bottom left
set format x ""
set ytics 2000 
#set title "{/Helvetica Akamai}" offset 0, -1
set label "{/Courier-Bold Akamai}" at "20110301", 5000
plot    "data/rpki-enabled-unique-prefix-asn-invalid-adv-reasoning-ipv4/akamai-public-prefix.tsv" u 1:($4) w st linestyle 1 title "Too Specific",\
        "data/rpki-enabled-unique-prefix-asn-invalid-adv-reasoning-ipv4/akamai-public-prefix.tsv" u 1:($5+$3) w st linestyle 2 title "Wrong ASNs"


unset multiplot

