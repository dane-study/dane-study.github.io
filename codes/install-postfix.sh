wget ftp://ftp.porcupine.org/mirrors/postfix-release/official/postfix-3.4.8.tar.gz

wget http://www.linuxfromscratch.org/patches/blfs/svn/postfix-3.4.8-glibc230_fix-1.patch

tar -xvzf postfix-3.4.8.tar.gz

cd postfix-3.4.8

groupadd -g 32 postfix &&
groupadd -g 33 postdrop &&
useradd -c "Postfix Daemon User" -d /var/spool/postfix -g postfix \
        -s /bin/false -u 32 postfix &&
chown -v postfix:postfix /var/mail

sed -i 's/.\x08//g' README_FILES/*

patch -Np1 -i ../postfix-3.4.8-glibc230_fix-1.patch

CCARGS='-DUSE_SASL_AUTH -DUSE_CYRUS_SASL -I/usr/include/sasl'
AUXLIBS='-lsasl2'

CCARGS='-DHAS_SQLITE'
AUXLIBS='-lsqlite3 -lpthread'

CCARGS='-DUSE_TLS -I/usr/include/openssl/'
AUXLIBS='-lssl -lcrypto'

make CCARGS="-DUSE_TLS -I/usr/include/openssl/                     \
             -DUSE_SASL_AUTH -DUSE_CYRUS_SASL -I/usr/include/sasl" \
     AUXLIBS="-lssl -lcrypto -lsasl2"                              \
     makefiles &&
make

sh postfix-install -non-interactive \
   daemon_directory=/usr/lib/postfix \
   manpage_directory=/usr/share/man \
   html_directory=/usr/share/doc/postfix-3.4.8/html \
   readme_directory=/usr/share/doc/postfix-3.4.8/readme