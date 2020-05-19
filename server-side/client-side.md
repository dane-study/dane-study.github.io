+++
title = "Client-side Artifacts"
menu = "main"
weight = 2
date = "2018-05-16"
+++
# Q: How to reproduce Table 2 in the paper? --- In other words, how can we know if a mail server provider supports DANE (and correctly?)

<style>
table, th { text-align: center;
}
</style>


Our basic idea is to setup many different mail servers (SMTP servers), which have an unique domain name and its corresponding MX record. We configure each of them with a different combination of DNSSEC, STARTTLS, and DANE misconfigurations as well as one with correctly configured settings.
After that we send emails from a mail provider that we want to test to each of our mail servers to throughly understand what protocols the mail provider (correctly) support.

## Preliminary 

1.  You need to set up your own mail server with a DNS server; we used postfix and Bind9. For the reproducibility, we provide (1) how to install Bind9 and Postfix software as we did for our research and (2) how to generate each of the scenarios that are correctly and misconfigured using Bind9 so that you can test a mail provider by simply sending an email from the provider and checking the logs in your mail server.

2.  First, we need to install and configure the DNS server using Bind9; we provide a script, which automatically create Bind zone files. 

3.  Second, we need to install and configure SMTP server using postfix MTA (Mail Transfer Agent). We used the Server Name Indication (SNI) extension to serve multiple certificates on the same (physical) machine. It allows a sending mail client to specify which domain it is trying to contact so that our mail server presents the certificate matched to the domain name in the MX record.

4.  Once you send an email from the mail service provider, you can use our script to infer their policy.

5.  For your reference, we have provided our subdomains (see below), each of which is configured differently. You can easily test each of the subdomains on this [website](https://dane.sys4.de/).

## Summary of source codes

Here, we provide following source codes. The instruction and usage of the source codes are explainedbelow.

{{< bootstrap-table "table table-dark table-striped table-bordered" >}}
| filename | Download  | Misc.
| --- | --- | --- |
| `configuration-bind-postfix.tar.gz` | [link](/codes/configuration-bind-postfix.tar.gz)| It contains Bind9 and postfix configuration files.|
| `generate-zone.py` | [script](/codes/generate-zone.py) and [example Yaml](/codes/security-protocol.com.yml)| It generates Bind9 zone files as per the yaml file .|
| `install-postfix.sh` | [script](/codes/install-postfix.sh) | It makes postfix support SNI. (Note: it requires root permission)
{{< /bootstrap-table >}}

## Summary of existing scenarios build to determine a mail provider's policy

{{< bootstrap-table "table table-dark table-striped table-bordered" >}}
| Scenario | Description 
| --- | --- |
| valid.security-protocol.com |  It serves proper TLSA and STARTTLS records 
| wrong-signature.security-protocol.com | It serves wrong RRSIG for TLSA record 
| missing-signature.security-protocol.com | It serves no RRSIG for TLSA record 
| expired-starttls-tlsa-3.security-protocol.com |  It serves an expired certificate and the usage of its matched TLSA record is set to 3  |
| missing-ds.security-protocol.com | It does not have the DS record, thus the chain-of-trust is missing  | 
| self-signed-starttls.security-protocol.com  | It serves a self-signed leaf certificate without TLSA records| 
| cn-diff-starttls.security-protocol.com | It serves a leaf certificate but its Common Name (CN) does not match with the domain name. | 
| different-cert.security-protocol.com | The certificate (provided from STARTTLS) is not matched with its TLSA record | 
| dane-diff-match.security-protocol.com | It serves a self-signed leaf certificate, but it does not match with a TLSA record due to the different Matching Type | 
| dane-diff-selector.security-protocol.com | It serves a self-signed leaf certificate, but the value of its Selector is undefined | 
| dane-diff-usage-1.security-protocol.com | It serves a self-signed leaf certificate with its TLSA record, which has the PKIX-EE usage. However, its Certificate Association Data does not match |
{{< /bootstrap-table >}}
<!-- | dane-diff-usage-3.security-protocol.com | It serves a CA and leaf certificate (signed by the CA certificate). | Domain issued certificate (and DANE-EE) which indicates a self-signed certificate to create TLSA record. | # tijay's comment: we don't need this scenario.   -->

# Reproducing the client configuration in the USENIX Security'20 paper

## 1. Setting up a Bind9 DNS server

<!-- Note: As DANE assumes your domain name supports DANE, your DNS server must support DNSSEC. -->

### Install a Bind9 DNS server in Ubuntu

```
$ sudo apt-get install bind9 bind9utils bind9-doc dnsutils
```

### Configure Bind9
#### (1) Enabling BIND9 log options. 

<!--
One of the important configuration file for bind is `/etc/bind/named.conf.options`, from this file we can set the followings parameters:

* Allow Query to your dns from your private network (as the name suggests only the systems from your private network can query dns sever for name to ip translation and vice-versa)
* Allow recursive query
* Specify the DNS port (53)
* Forwarders (DNS query will be forwarded to the forwarders when your local DNS server is unable to resolve query)

```
options {
        directory "/var/cache/bind";

        recursion yes;
        allow-recursion { trusted; };
        allow-transfer { none; };

        forwarders {
                8.8.8.8;
                8.8.4.4;
        };

		dnssec-validation auto;
        dnssec-enable yes;

        auth-nxdomain no;    # conform to RFC1035
        listen-on-v6 { any; };

};
```

-->

We need to log all incoming DNS queries to see if they do support DNSSEC (by checking EDNS0 and D0 bit) and have requested DNSKEY/DS/TLSA records.

```
logging {
        channel named       { file "named.log" versions 10 size 20M; print-time yes; print-category yes; };
        channel security    { file "security.log" versions 10 size 20M; print-time yes; };
        channel query_log   { file "query.log" versions 10 size 20M; severity debug; print-time yes; };
        channel query_error { file "query-errors.log" versions 10 size 20M; severity info; print-time yes; };
        channel transfer    { file "transfer.log" versions 10 size 10M; print-time yes; };
        channel dnssec_log  { file "dnssec.log"; severity debug 3; };

        category dnssec     { dnssec_log; };
        category default    { default_syslog; named; };
        category general    { default_syslog; named; };
        category security   { security; };
        category queries    { query_log; };
        category config     { named; };
        category xfer-in    { transfer; };
        category xfer-out   { transfer; };
        category notify     { transfer; };
};
```

#### (2) Create Forward Zone File

You can use the `generate-zone.py` script to generate a zone file automatically (assuming your domain name is security-protocol.com). 
<!-- Add the record type you need to represent in a zone in a YAML file as available in the [example Yaml](/codes/security-protocol.com.yml).  -->

` Note: update the serial value (in the SOA record) whenever you update your zone file.`

Example zone file:

```
;
; BIND data file for local loopback interface
;
$TTL    1
@       IN      SOA     ns01.valid.security-protocol.com. admin.valid.security-protocol.com. (
                             27         ; Serial
                         604800         ; Refresh
                          86400         ; Retry
                        2419200         ; Expire
                         604800 )       ; Negative Cache TTL
;
; name servers - NS records
        IN      NS      ns01.security-protocol.com.
        IN      NS      ns02.security-protocol.com.

; name servers - A records
ns01.valid.security-protocol.com.      IN      A       34.219.137.44
ns02.valid.security-protocol.com.      IN      A       34.219.137.44

; A record
valid.security-protocol.com.   IN      A       34.219.137.44

; MX record

mail.valid.security-protocol.com.      IN      A       34.219.137.44
@       IN      MX      10 mail.valid.security-protocol.com.

```

We need to sign the zones to support DNSSEC for each domains.
You can type the following commands to sign your zones in the directory that contains (private) key files (such as /etc/bind/keys/<domainname.com>),  

```
 $ sudo dnssec-keygen -a RSASHA256 -b 2048 -3 -f KSK -r /dev/urandom security-protocol.com
 $ sudo dnssec-keygen -a RSASHA256 -b 2048 -3 -r /dev/urandom security-protocol.com
```
The directory will have four keys - private/public pairs of ZSK and KSK. We have to serve those public keys as a DNSKEY record.

Sign the zone with the `dnssec-signzone` command.

```
$ dnssec-signzone -3 <salt> -A -N INCREMENT -o <zonename> -t <zonefilename>
```

Example:

```
$ sudo dnssec-signzone -S -K /etc/bind/keys/security-protocol -e 20250530144500 -g -a -r /dev/random -o security-protocol.com zones/db.security-protocol.com 
```

Next configuration file is `/etc/bind/named.conf.local`, in this file we will define the zone files for our domain, edit the file add the following entries:

`Note: If your domain is DNSSEC-enabled, then you need to point the signed zone in “/etc/bind/named.conf.local“`

```
zone "security-protocol.com" {
        type master;
        file "/etc/bind/zones/db.security-protocol.com.signed";
};

zone "security-protocol.com" {
        type master;
        file "/etc/bind/zones/db.security-protocol.com.signed";
};

zone "expired-starttls-tlsa-3.security-protocol.com" {
        type master;
        file "/etc/bind/zones/db.expired-starttls-tlsa-3.security-protocol.com.signed";
};

zone "expired-starttls-no-tlsa.security-protocol.com" {
        type master;
        file "/etc/bind/zones/db.expired-starttls-no-tlsa.security-protocol.com";
};

zone "different-cert.security-protocol.com" {
        type master;
        file "/etc/bind/zones/db.different-cert.security-protocol.com.signed";
};

...

```

Save file & exit. Now all we have to do is to restart the BIND service to implement the changes made,

```
$ sudo service bind9 restart
$ sudo service bind9 enable 
```

`Note:` Please execute the below command to allow 53 port if your firewall is blocking the port.

```
$ sudo ufw allow 53
```

## 2. Setting up postfix SMTP server

Below, we provide detailed instructions on how to install postfix MTA. We strongly recommend to use postfix 3.4.5 or above because they support SNI to serve multiple certificates.

### Install Postfix MTA

#### (1) Downloading Postfix
You can either use the `install-postfix.sh` script to automatically install postfix. However, if the script fails or would like to manually install postfix, please follow the below instruction.

Assuming that you are using a Linux flavoured operating system.

Download the latest version of postfix 3.4.8 from here:

```
ftp://ftp.porcupine.org/mirrors/postfix-release/official/postfix-3.4.8.tar.gz
```

You also need to download and apply this specific patch as well.

```
http://www.linuxfromscratch.org/patches/blfs/svn/postfix-3.4.8-glibc230_fix-1.patch
```

Postfix recommends the following dependencies

```
Berkeley DB-5.3.28
Cyrus SASL-2.1.27
libnsl-1.2.0
```

Once you have all the required dependencies for postfix, you can proceed to the installation process as follows:

#### (2) Adding users and groups

Before you compile the program, you need to create users and groups that will be expected to be in place during the installation. Add the users and groups with the following commands issued by the root user:

```
groupadd -g 32 postfix &&
groupadd -g 33 postdrop &&
useradd -c "Postfix Daemon User" -d /var/spool/postfix -g postfix \
        -s /bin/false -u 32 postfix &&
chown -v postfix:postfix /var/mail
```

#### (3) Configuring the Build

The README files are formatted to be read with a pager like Less or More. If you want to use a text editor, make them legible with the following sed:

```
sed -i 's/.\x08//g' README_FILES/*
```

Apply a patch to allow Postfix to compile on Glibc-2.30 where some macros were dropped:

```
patch -Np1 -i ../postfix-3.4.8-glibc230_fix-1.patch
```

**Cyrus-SASL:**

To use Cyrus-SASL with Postfix, use the following arguments:

```
CCARGS='-DUSE_SASL_AUTH -DUSE_CYRUS_SASL -I/usr/include/sasl'
AUXLIBS='-lsasl2'
```

#### (4) Configuring the database for postfix

You can utilse any of the database software such as sqlite, mysql or postgreSQL as below.
<br/>

**Sqlite:**

To use Sqlite with Postfix, use the following arguments:

```
CCARGS='-DHAS_SQLITE'
AUXLIBS='-lsqlite3 -lpthread'
```

**MySQL:**

To use MySQL with Postfix, use the following arguments:

```
CCARGS='-DHAS_MYSQL -I/usr/include/mysql'
AUXLIBS='-lmysqlclient -lz -lm'
```

**PostgreSQL:**

To use PostgreSQL with Postfix, use the following arguments:

```
CCARGS='-DHAS_PGSQL -I/usr/include/postgresql'
AUXLIBS='-lpq -lz -lm'
```

#### (5) Enabling the STARTTLS authentication

To use OpenSSL with Postfix, use the following arguments:

```
CCARGS='-DUSE_TLS -I/usr/include/openssl/'
AUXLIBS='-lssl -lcrypto'
```

#### (6) Installing Postfix

If you have Cyrus SASL and OpenSSL installed, now install Postfix by running the following commands:

```
make CCARGS="-DUSE_TLS -I/usr/include/openssl/                     \
             -DUSE_SASL_AUTH -DUSE_CYRUS_SASL -I/usr/include/sasl" \
     AUXLIBS="-lssl -lcrypto -lsasl2"                              \
     makefiles &&
make
```

Now, as the root user:

```
sh postfix-install -non-interactive \
   daemon_directory=/usr/lib/postfix \
   manpage_directory=/usr/share/man \
   html_directory=/usr/share/doc/postfix-3.4.8/html \
   readme_directory=/usr/share/doc/postfix-3.4.8/readme
```

### 3. Configure Postfix

In this section, you will configure the `/etc/postfix/main.cf` file to serve it as an external SMTP server.

Open the `/etc/postfix/main.cf` file with your favorite text editor:

```
sudo vim /etc/postfix/main.cf
```

Add the following parameters to the config file to enable STARTTLS.

```
smtpd_use_tls = yes
smtpd_tls_loglevel = 2
```

If you are missing any additional parameters in the postfix setup, do checkout our example configuration files found [here](/codes/configuration-bind-postfix.tar.gz)

#### (1) SNI configuration

Unlike the usual setup to serve a single TLS certificate file and a TLS key file in the postfix SMTP MTA configuration as to initiate STARTTLS security extension support, we wanted to serve multiple certificates in the same machine (w/ a single IP address) for simplicity sake. The configuration file specifies a very small subset of all the parameters that control the operation of the Postfix mail system.

<!-- Run through the initial configuration after the installation of postfix from the apt package and then, upgrade postfix through the installation from source. Further, when its is done, move on to configure SNI. -->

For the SNI setup, we created a few certificate chains. This was followed by creating a hash table using `sudo postmap -F` to hold the SNI chains where the domains are denoted as: 

```
domain1.com static:/path/to/pem1.pem 
domain2.com static:/path/to/pem2.pem
```

Which then is referred in the `/etc/postfix/main.cf` configuration of postfix using: 

`tls_server_sni_maps = hash:/etc/postfix/sni-chains`

In `/etc/postfix/main.cf` **Before**: 

```
smtpd_tls_key_file = /path/to/the/key/file/smtp_tls.key
smtpd_tls_cert_file = /path/to/the/cert/file/smtp_cert.pem
```

With this configuration parameter alone, we are only able to provide/serve single key and certificate file for the SMTP server for a specific single domain.

**Now:**

Our goal was to serve multiple certificates for each of the delegated domains as per the busted environment that we devised.

First, we provide a parameter ` smtpd_tls_chain_files` to the configuration file as to provide a default certificate to the SNI lookup table that is going to be created. The SNI lookup tables should also have entries for the domains that correspond to the Postfix SMTP server's default certificate(s). This ensures that the remote SMTP client's TLS SNI extension gets a positive response when it specifies one of the Postfix SMTP server's default  domains, and ensures that the Postfix SMTP server will not log an SNI name mismatch for such a domain. The Postfix SMTP server's default certificates are then only used when the client sends no SNI or when it sends SNI with a domain that the server knows no certificate(s) for.

```
smtpd_tls_chain_files = /etc/letsencrypt/live/security-protocol.com/privkey.pem, /etc/letsencrypt/live/security-protocol.com/cert.pem
```

Yes, having a default as such might be inconvenient for few use cases. Currently, postfix has this in place since default chain with an explicitly SNI mapping to that chain, is to suppress warnings in the logs about receiving SNI names that fail to match any entries in the table. Such warnings can be useful to identify misconfigured clients and servers. Setting up a wildcard default would completely defeat the purpose of the mismatch logging.

That is, smtpd_tls_chain_files parameter assures the client with a positive acknowledgement, and suppresses logging of SNI mismatch. Suppressing such logs for $myhostname since default chain is the right one to use.

Further we denote the SNI table created inside the configuration file through the parameter `tls_server_sni_maps`

```
main.cf:
       tls_server_sni_maps = hash:/etc/postfix/sni-chains
```

```
sni-chains: 
       mail.security-protocol.com	/etc/postfix/sni/domain1.example.pem 
       mail.domain2.security-protocol.com	/etc/postfix/sni/domain2.example.pem
```

The sni-chains is a SNI lookup table created for storing certificate chains mapped to the SNI domains. In postfix, we use a postmap command to create the hash table. The syntax is: 

`$ postmap -F hash:/etc/postfix/sni-chains`

Need to note that, You'll need to rebuild the table (again with "postmap -F") whenever you want to start using new certificates, adding new certificates  even if the file names are unchanged. 

Further also note that, The sni-chain must always list the private key before the associated certificate chain. You can list a file with just the key first, and then the certificate file. An advanced use case is to list multiple files for the same domain, each with a key and certificate chain for a different algorithm.

Example sni-chain file:
```
mail.security-protocol.com /etc/letsencrypt/live/security-protocol.com/privkey.pem /etc/letsencrypt/live/security-protocol.com/fullchain.pem
mail.valid.security-protocol.com /etc/letsencrypt/live/valid.security-protocol.com/privkey.pem /etc/letsencrypt/live/valid.security-protocol.com/fullchain.pem
mail.different-cert.security-protocol.com /etc/letsencrypt/live/security-protocol.com/privkey.pem /etc/letsencrypt/live/security-protocol.com/fullchain.pem
```

Save your changes.

Restart Postfix:

```
sudo service postfix restart
<<<<<<< HEAD
```

### 4. Reproducing client-side DANE results

After the installation of Bind9 DNS server software and compiling custom version of Postfix. We can start testing and see how to reproduce the client side table in the paper.

* Step 1: Create an account in any of email service provider you want to analyse. 
* Step 2: Check the DNS logs using ` tail -n 50 -f /var/cache/bind/query.log `

The below example DNS logs show the DNSSEC and DANE (TLSA) support of the resolver that the mail provider uses (i.e., D0 bit enabled, and DS, DNSKEY, and TLSA record fetched).

```
07-Feb-2020 19:55:54.593 client @0x7fc2c80e0720 74.208.114.131#31068 (valid.security-protocol.com): query: valid.security-protocol.com IN DS -E(0)D (172.31.27.143)
07-Feb-2020 19:55:55.469 client @0x7fc2c80e0720 74.208.114.131#29440 (valid.security-protocol.com): query: valid.security-protocol.com IN MX -E(0)D (172.31.27.143)
07-Feb-2020 19:55:55.530 client @0x7fc2c80e0720 74.208.114.131#45210 (valid.security-protocol.com): query: valid.security-protocol.com IN DS -E(0)D (172.31.27.143)
07-Feb-2020 19:55:55.591 client @0x7fc2c80e0720 74.208.114.131#52183 (valid.security-protocol.com): query: valid.security-protocol.com IN DS -E(0)D (172.31.27.143)
07-Feb-2020 19:55:55.651 client @0x7fc2c80e0720 74.208.114.131#25687 (security-protocol.com): query: security-protocol.com IN DNSKEY -E(0)D (172.31.27.143)
07-Feb-2020 19:55:55.712 client @0x7fc2c80e0720 74.208.114.131#29666 (valid.security-protocol.com): query: valid.security-protocol.com IN MX -E(0)D (172.31.27.143)
07-Feb-2020 19:55:55.770 client @0x7fc2c80e0720 74.208.114.131#44412 (valid.security-protocol.com): query: valid.security-protocol.com IN DNSKEY -E(0)D (172.31.27.143)
07-Feb-2020 19:55:55.891 client @0x7fc2c88a5900 74.208.114.131#39670 (valid.security-protocol.com): query: valid.security-protocol.com IN DNSKEY -E(0)TD (172.31.27.143)
07-Feb-2020 19:55:55.954 client @0x7fc2c80e0720 74.208.114.131#45964 (valid.security-protocol.com): query: valid.security-protocol.com IN DNSKEY -E(0)D (172.31.27.143)
07-Feb-2020 19:55:56.075 client @0x7fc2c8053140 74.208.114.131#36114 (valid.security-protocol.com): query: valid.security-protocol.com IN DNSKEY -E(0)TD (172.31.27.143)
07-Feb-2020 19:55:56.133 client @0x7fc2c80e0720 74.208.114.131#23476 (valid.security-protocol.com): query: valid.security-protocol.com IN DS -E(0)D (172.31.27.143)
07-Feb-2020 19:55:56.189 client @0x7fc2c80e0720 74.208.114.131#22369 (security-protocol.com): query: security-protocol.com IN DNSKEY -E(0)D (172.31.27.143)
07-Feb-2020 19:55:56.250 client @0x7fc2c80e0720 74.208.114.130#2351 (valid.security-protocol.com): query: valid.security-protocol.com IN DS -E(0)D (172.31.27.143)
07-Feb-2020 19:55:56.307 client @0x7fc2c80e0720 74.208.114.130#1782 (security-protocol.com): query: security-protocol.com IN DNSKEY -E(0)D (172.31.27.143)
07-Feb-2020 19:55:56.365 client @0x7fc2c80e0720 74.208.114.130#64954 (valid.security-protocol.com): query: valid.security-protocol.com IN DNSKEY -E(0)D (172.31.27.143)
07-Feb-2020 19:55:56.483 client @0x7fc2c890b590 74.208.114.130#36227 (valid.security-protocol.com): query: valid.security-protocol.com IN DNSKEY -E(0)TD (172.31.27.143)
07-Feb-2020 19:55:56.545 client @0x7fc2c80e0720 74.208.114.131#36696 (mail.valid.security-protocol.com): query: mail.valid.security-protocol.com IN DS -E(0)D (172.31.27.143)
07-Feb-2020 19:55:56.601 client @0x7fc2c80e0720 74.208.114.131#7328 (mail.valid.security-protocol.com): query: mail.valid.security-protocol.com IN A -E(0)D (172.31.27.143)
07-Feb-2020 19:55:56.662 client @0x7fc2c80e0720 74.208.114.131#27867 (mail.valid.security-protocol.com): query: mail.valid.security-protocol.com IN AAAA -E(0)D (172.31.27.143)
07-Feb-2020 19:55:56.723 client @0x7fc2c80e0720 74.208.114.130#47107 (mail.valid.security-protocol.com): query: mail.valid.security-protocol.com IN DS -E(0)D (172.31.27.143)
07-Feb-2020 19:55:56.784 client @0x7fc2c80e0720 74.208.114.130#43212 (mail.valid.security-protocol.com): query: mail.valid.security-protocol.com IN AAAA -E(0)D (172.31.27.143)
07-Feb-2020 19:55:56.843 client @0x7fc2c80e0720 74.208.114.131#4486 (_tcp.mail.valid.security-protocol.com): query: _tcp.mail.valid.security-protocol.com IN DS -E(0)D (172.31.27.143)
07-Feb-2020 19:55:56.901 client @0x7fc2c80e0720 74.208.114.131#36775 (_25._tcp.mail.valid.security-protocol.com): query: _25._tcp.mail.valid.security-protocol.com IN DS -E(0)D (172.31.27.143)
07-Feb-2020 19:55:56.957 client @0x7fc2c80e0720 74.208.114.131#32013 (_25._tcp.mail.valid.security-protocol.com): query: _25._tcp.mail.valid.security-protocol.com IN TLSA -E(0)D (172.31.27.143)
07-Feb-2020 19:55:57.017 client @0x7fc2c80e0720 74.208.114.131#23719 (security-protocol.com): query: security-protocol.com IN DNSKEY -E(0)D (172.31.27.143)
07-Feb-2020 19:55:57.084 client @0x7fc2c80e0720 74.208.114.131#8302 (valid.security-protocol.com): query: valid.security-protocol.com IN DS -E(0)D (172.31.27.143)
07-Feb-2020 19:55:57.144 client @0x7fc2c80e0720 74.208.114.131#54218 (security-protocol.com): query: security-protocol.com IN DNSKEY -E(0)D (172.31.27.143)
07-Feb-2020 19:55:57.204 client @0x7fc2c80e0720 74.208.114.131#26564 (valid.security-protocol.com): query: valid.security-protocol.com IN DNSKEY -E(0)D (172.31.27.143)
07-Feb-2020 19:55:57.324 client @0x7fc2c874e1e0 74.208.114.131#38430 (valid.security-protocol.com): query: valid.security-protocol.com IN DNSKEY -E(0)TD (172.31.27.143)
07-Feb-2020 19:55:57.385 client @0x7fc2c80e0720 74.208.114.130#53045 (valid.security-protocol.com): query: valid.security-protocol.com IN DS -E(0)D (172.31.27.143)
07-Feb-2020 19:55:57.444 client @0x7fc2c80e0720 74.208.114.130#17783 (security-protocol.com): query: security-protocol.com IN DNSKEY -E(0)D (172.31.27.143)
07-Feb-2020 19:55:57.505 client @0x7fc2c80e0720 74.208.114.130#61317 (valid.security-protocol.com): query: valid.security-protocol.com IN DNSKEY -E(0)D (172.31.27.143)
07-Feb-2020 19:55:57.623 client @0x7fc2c8510e40 74.208.114.130#45243 (valid.security-protocol.com): query: valid.security-protocol.com IN DNSKEY -E(0)TD (172.31.27.143)
```

* Step 3: Check the SMTP log using `tail -n 50 -f /var/log/mail.log`

The below example shows that the email provider supports STARTTLS. 

```
Feb  7 19:55:57 security-protocol postfix/smtpd[17916]: initializing the server-side TLS engine
Feb  7 19:55:57 security-protocol postfix/smtpd[17916]: connect from mout.gmx.com[74.208.4.200]
Feb  7 19:55:57 security-protocol postfix/smtpd[17916]: setting up TLS connection from mout.gmx.com[74.208.4.200]
Feb  7 19:55:57 security-protocol postfix/smtpd[17916]: mout.gmx.com[74.208.4.200]: TLS cipher list "aNULL:-aNULL:HIGH:MEDIUM:+RC4:@STRENGTH"
Feb  7 19:55:57 security-protocol postfix/smtpd[17916]: SSL_accept:before SSL initialization
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: SSL_accept:before SSL initialization
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: SSL_accept:SSLv3/TLS read client hello
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: SSL_accept:SSLv3/TLS write server hello
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: SSL_accept:SSLv3/TLS write change cipher spec
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: SSL_accept:TLSv1.3 write encrypted extensions
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: SSL_accept:SSLv3/TLS write certificate
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: SSL_accept:TLSv1.3 write server certificate verify
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: SSL_accept:SSLv3/TLS write finished
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: SSL_accept:TLSv1.3 early data
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: SSL_accept:TLSv1.3 early data
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: SSL_accept:SSLv3/TLS read finished
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: mout.gmx.com[74.208.4.200]: Issuing session ticket, key expiration: 1581107157
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: mout.gmx.com[74.208.4.200]: save session 763355DD0A89B45CB12D0E068A71F3ED0F960F5D974F66011CAC5BCBE405332D&s=smtp&l=269488143 to smtpd cache
Feb  7 19:55:58 security-protocol postfix/tlsmgr[23489]: put smtpd session id=763355DD0A89B45CB12D0E068A71F3ED0F960F5D974F66011CAC5BCBE405332D&s=smtp&l=269488143 [data 173 bytes]
Feb  7 19:55:58 security-protocol postfix/tlsmgr[23489]: write smtpd TLS cache entry 763355DD0A89B45CB12D0E068A71F3ED0F960F5D974F66011CAC5BCBE405332D&s=smtp&l=269488143: time=1581105358 [data 173 bytes]
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: SSL_accept:SSLv3/TLS write session ticket
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: Anonymous TLS connection established from mout.gmx.com[74.208.4.200] to mail.valid.security-protocol.com: TLSv1.3 with cipher TLS_AES_256_GCM_SHA384 (256/256 bits) server-signature RSA-PSS (2048 bits)
Feb  7 19:55:58 security-protocol postfix/smtpd[17916]: A2EAD42046: client=mout.gmx.com[74.208.4.200]
Feb  7 19:55:59 security-protocol postfix/cleanup[17920]: A2EAD42046: message-id=<trinity-72da751b-5cb4-4d3b-a1b4-64957a1e3074-1581105354301@3c-app-mailcom-lxa05>
Feb  7 19:55:59 security-protocol postfix/qmgr[23485]: A2EAD42046: from=<dane-test@mail.com>, size=2532, nrcpt=1 (queue active)
Feb  7 19:55:59 security-protocol postfix/local[17921]: A2EAD42046: to=<ubuntu@valid.security-protocol.com>, relay=local, delay=0.57, delays=0.55/0.02/0/0, dsn=2.0.0, status=sent (delivered to maildir)
Feb  7 19:55:59 security-protocol postfix/qmgr[23485]: A2EAD42046: removed
Feb  7 19:55:59 security-protocol postfix/smtpd[17916]: disconnect from mout.gmx.com[74.208.4.200] ehlo=2 starttls=1 mail=1 rcpt=1 data=1 quit=1 commands=7
Feb  7 19:57:17 security-protocol postfix/smtpd[17916]: connect from unknown[185.234.218.145]
Feb  7 19:57:18 security-protocol postfix/smtpd[17916]: lost connection after AUTH from unknown[185.234.218.145]
Feb  7 19:57:18 security-protocol postfix/smtpd[17916]: disconnect from unknown[185.234.218.145] ehlo=1 auth=0/1 commands=1/2
```

Step 4: Once recieved the logs, do check the `Maildir/` to see if you have received email that you sent.

Repeat the above steps by sending multiple emails to each different subdomain to infer the DNSSEC and (correct-) DANE support of the target mail provider.
