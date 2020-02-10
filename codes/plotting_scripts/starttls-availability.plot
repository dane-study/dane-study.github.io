load 'plots/style.gnu'

set datafile separator ","
#set output '../figures/starttls-availability.eps'

set lmargin 10
set size 0.6, 0.54  # 06 and 0.4
set multiplot

set grid
set xdata time
set timefmt "%Y%m%d %H"

set size 0.6, 0.32
set origin 0, 0
set ylabel "{/Helvetica-Bold % of SMTP servers that fail }\n{/Helvetica-Bold to establish a TLS connection}" offset 0, 4
set xlabel "{/Helvetica-Bold Date}"
set format x ""
set xrange["20190711 01":"20191101 01"]
set xtics 3600 * 24 * 7 * 2
set format x "%m/%d"
set key top left maxrows 3
set yrange [0:1.2]
set ytics 0.3

set label "{/Helvetica-Bold TLS Handshake Errors}" at "20190713 01", 0.15
plot "data/starttls_error_stat_output_virginia.txt" u 1:(100 * ($9)/($2 - $8 - $13 - $7)) w st linestyle 1 lw 3  title "Virginia",\
"data/starttls_error_stat_output_oregon.txt" u 1:(100 * ($9)/($2 - $8 - $13 - $7)) w st linestyle 2 lw 3  title "Oregon",\
"data/starttls_error_stat_output_paris.txt" u 1:(100 * ($9)/($2 - $8 - $13 - $7)) w st linestyle 3 lw 3  title "Paris",\
"data/starttls_error_stat_output_saopaulo.txt" u 1:(100 * ($9)/($2 - $8 - $13 - $7)) w st linestyle 4 lw 3  title "Sao-Paulo",\
"data/starttls_error_stat_output_sydney.txt" u 1:(100 * ($9)/($2 - $8 - $13 - $7)) w st linestyle 5 lw 3  title "Sydney",\

set yrange [0:1]
set ytics 0.2
set size 0.6, 0.25
set origin 0, 0.3
set xtics()
unset label
set xlabel ""
set ylabel ""
set format x ""
set label "{/Helvetica-Bold Unimplemented STARTTLS}" at "20190713 01", 0.9
plot "data/starttls_error_stat_output_virginia.txt" u 1:(100 * ($6)/($2 - $8 - $13 - $7)) w st linestyle 1 lw 3  title "",\
"data/starttls_error_stat_output_oregon.txt" u 1:(100 * ($6)/($2 - $8 - $13 - $7)) w st linestyle 2 lw 3  title "",\
"data/starttls_error_stat_output_paris.txt" u 1:(100 * ($6)/($2 - $8 - $13 - $7)) w st linestyle 3 lw 3  title "",\
"data/starttls_error_stat_output_saopaulo.txt" u 1:(100 * ($6)/($2 - $8 - $13 - $7)) w st linestyle 4 lw 3  title "",\
"data/starttls_error_stat_output_sydney.txt" u 1:(100 * ($6)/($2 - $8 - $13 - $7)) w st linestyle 5 lw 3  title "",\

