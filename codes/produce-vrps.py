''' This script produces verified IPv4 and IPv6 prefixes
    with their AS numbers.  This dataset will be used to verify the BGP
    announcement collected from (1) Routeview, (2) RIPE-RIS, and (3) Akamai BGP collector.

'''

import os
import sys
import base64
from datetime import *
from ipaddress import *
from rpki.POW import ROA
from intervaltree import *
from multiprocessing import *


ROA_PATH   = None # The path where ROA objects are stored.
ROA_OUTPUT = None # The output path where VRPs will be stored. 
NRO_PATH = None # The path where NRO (https://www.nro.net/about/rirs/statistics/) files are stored.

def getNumIPAddresses(prefix, prefixlen, maxlen):
    from_address = u'%s/%s' % (prefix, prefixlen)
    to_address = u'%s/%s' % (prefix, maxlen)
     
    if(prefixlen == maxlen or maxlen is None):
        return ip_network(from_address).num_addresses
    
    return ip_network(from_address).num_addresses - ip_network(to_address).num_addresses


def readNRO(date):

    cc_ipv4 = {}
    cc_ipv6 = {}
    
    ### nrostats for ipv4
    """
    prefix,rir,date,country_code,status,block_start,block_ip_count
    1.0.0.0/24,apnic,20110811,AU,assigned,1.0.0.0,256
    1.0.1.0/24,apnic,20110414,CN,allocated,1.0.1.0,256
    """
    
    nrostats_ipv4 = os.path.join(NRO_PATH, "nrostats-%s-v4.csv" % date)
    if(not os.path.exists(nrostats_ipv4)): return None, None

    for line in open(nrostats_ipv4):
        prefix, rir, d, country_code, status, block_start, block_ip_cnt = line.split(",")
        if("prefix" == prefix): continue
        ipv4 = IPv4Address(unicode(prefix.split("/")[0]))
        cc_ipv4[int(ipv4)] = country_code

    index = sorted(cc_ipv4)
    rd_ipv4 = IntervalTree()
    for prev, next in zip(index[:-1], index[1:]):
        rd_ipv4[prev:next] = cc_ipv4[prev]

    ### nrostats for ipv6
    '''
    prefix,rir,date,country_code,status
    2001:5::/32,ripencc,20161115,EU,allocated
    2001:200::/35,apnic,19990813,JP,allocated
    '''
    for line in open(os.path.join(NRO_PATH, "nrostats-%s-v6.csv" % date)):
        prefix, rir, d, country_code, status = line.split(",")
        if("prefix" == prefix): continue
        ipv6 = IPv6Address(unicode(prefix.split("/")[0]))
        cc_ipv6[int(ipv6)] = country_code

    index = sorted(cc_ipv6)
    rd_ipv6 = IntervalTree()
    for prev, next in zip(index[:-1], index[1:]):
        rd_ipv6[prev:next] = cc_ipv6[prev]

    return rd_ipv4, rd_ipv6



def produceAsidPrefix(f):
    output = open(os.path.join(ROA_OUTPUT, f), "w")
    
    rd_ipv4, rd_ipv6 = readNRO(f)
    
    cnt = 0
    idx = ['time', 'prefix', 'prefix-len', 'max-len', 'num-covered-ip-addresses', 'AS-id', 'CountryCode', 'TAL']
    output.write('#%s\n' % '\t'.join(idx))

    for line in open(os.path.join(ROA_PATH, f)):
        cnt += 1
        date, fname, _, skid, akid, ee_cert, roa = line.rstrip().split(",")
        roa = ROA.derRead(base64.b64decode(roa)) # object 1:1 mapping with certificate 
        roa.extractWithoutVerifying()
        
        _tmp = date.split("-")
        date = _tmp[0]
        irr = _tmp[1].replace(".txt", "")

        v4prefixes, v6prefixes = roa.getPrefixes()
        asID = roa.getASID()

        cc = "" # country-code

        if (v4prefixes is not None):
            for prefix, prefixlen, maxlen in v4prefixes:
                num = ip_network(u'%s/%s' % (prefix, prefixlen)).num_addresses
                if(rd_ipv4 is not None):
                    ipv4 = IPv4Address(unicode("%s" % prefix))
                    cc = list(rd_ipv4[int(ipv4)])[0][2]

                if(maxlen is None): maxlen = prefixlen

                s = [date, prefix, prefixlen, maxlen, asID, num, cc, irr]

                output.write("%s\n" % "\t".join(map(str, s)))

        if (v6prefixes is not None):
            for prefix, prefixlen, maxlen in v6prefixes:
                num = ip_network(u'%s/%s' % (prefix, prefixlen)).num_addresses

                if(rd_ipv6 is not None):
                    ipv6 = IPv6Address(unicode("%s" % prefix ))
                    cc = list(rd_ipv6[int(ipv6)])[0][2]

                if(maxlen is None): maxlen = prefixlen

                s = [date, prefix, prefixlen, maxlen, asID, num, cc, irr]

                output.write("%s\n" % "\t".join(map(str, s)))
    output.close()
    print f, cnt

def run(q, counter, lock):
    while not q.empty():
        f, num_all = q.get()
        produceAsidPrefix(f)

        with lock:
            counter.value += 1
        print counter.value, f, num_all

if __name__ == "__main__":
    files =  os.listdir(ROA_PATH)

    v = Value('i', 0)
    lock = Lock()
    q = Queue()
    for f in files:
        q.put( (f, len(files)))
    
    procs = [Process(target=run, args=(q, v, lock)) for i in range(30)]
    for p in procs: p.start()
    for p in procs: p.join()
