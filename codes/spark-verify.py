from pyspark import SparkContext, StorageLevel, SparkConf, broadcast
from pyspark.sql import SQLContext, Row
import pydoop.hdfs as hdfs
import ujson as json
import os
from datetime import *
from operator import itemgetter
import numpy as np
from sumin_tree import *

def mergeAndSort(path):
    cmdMerge = "cat {0}/* >> /tmp/tmp-tjchung".format(path)
    os.system(cmdMerge)

    cmdSort  = "sort -k1,1 /tmp/tmp-tjchung > {0}".format(path + ".tsv")
    os.system(cmdSort)

    cmdErase = "rm /tmp/tmp-tjchung"
    os.system(cmdErase)

def toTSV(data):
    return "\t".join(unicode(d) for d in data)

def ip2binary(prefix_addr, prefix_len):
    if("." in prefix_addr): # IPv4
        octets = map(lambda v: int(v), prefix_addr.split("."))
        octets = map(lambda v: format(v, "#010b")[2:], octets)

    else: # IPv6
        octets = map(lambda v: str(v), prefix_addr.split(":"))
        prefix_addrs = prefix_addr.split(":")
        
        for i in range( 8 - len(prefix_addrs)):
            idx = prefix_addrs.index("")
            prefix_addrs.insert(idx, "")

        prefix_addrs += [""] * (8 - len(prefix_addrs)) # 8 groups, each of them has 16 bytes (= four hexadecimal digits)

        octets = []
        for p in prefix_addrs:
            if( len(p) != 4): # 4 bytes 
                p += (4 - len(p)) * '0'
            octets.append( "".join(map(lambda v: format(int(v, 16), "#010b")[6:], p)) )

    return "".join(octets)[:int(prefix_len)]

def getCovered( prefix, prefix_len, smtree_v4, smtree_v6):
    key = ip2binary(prefix, prefix_len)
    if(":" in prefix):
        return smGetAllKeys(smtree_v6, key)
    else:
        return smGetAllKeys(smtree_v4, key)
    
def isPrefixCover(roa_px_dict, time, prefix_addr, prefix_len):
    if time not in roa_px_dict: return False 

    binary_prefix = ip2binary(prefix_addr, prefix_len)
    for roa_binary_prefix in roa_px_dict[time]:
        if( roa_binary_prefix in binary_prefix):
            return True
    
    return False

def validateOrigin(prefix_addr, prefix_len, asID, roa_px_dict, time):
    """
        This implementation is based on RFC 6811; Section 2
    """
    BGP_PFXV_STATE_NOT_FOUND = 0 # Unknown
    BGP_PFXV_STATE_VALID     = 1 # Valid
    BGP_PFXV_STATE_HIJACKING  = 2 # Covered ROA found, non-identical AS, matched
    BGP_PFXV_STATE_MISCONF = 3 # Covered ROA found, identical AS, but non-matched
    BGP_PFXV_STATE_SUBHIJACK   = 4 # Covered ROA Found, non-identical AS, non-matched
    
    if time not in roa_px_dict: return None 

    roas      = roa_px_dict[time][0]
    smtree_v4 = roa_px_dict[time][1]
    smtree_v6 = roa_px_dict[time][2]
    
    try:
        entries = getCovered( prefix_addr, prefix_len, smtree_v4, smtree_v6)
    except:
        return None


    result = BGP_PFXV_STATE_NOT_FOUND

    prefix_exists = False
    hasIdenticalAS = False
    covered_prefixes = set()
    
    #if(entries is not None):
    results = []
    if(len(entries) != 0):  
        prefix_exists = True
        for binary_prefix in entries:
            for vrp_prefix, vrp_prefixlen, vrp_maxlen, vrp_asID in roas[binary_prefix]:
                if(vrp_asID == asID):
                    """
                        We have found covered ROAs and also AS matched.
                        If matched ROAs found, then the result will be
                        BGP_PFXV_STATE_VALID and returned.

                    """
                    hasIdenticalAS = True
                    covered_prefixes.add("%s/%s-%s" % (vrp_prefix, vrp_prefixlen, vrp_maxlen))

                if(prefix_len <= vrp_maxlen):
                    if( asID is not None and\
                            vrp_asID != 0): 

                        if(asID == vrp_asID): 
                            result = BGP_PFXV_STATE_VALID
                        else:
                            result = BGP_PFXV_STATE_HIJACKING
                        
                        #return result, vrp_asID, " "
                        results.append( ",".join(map(str, [result, vrp_asID, "+".join(list(covered_prefixes))] )))

    if(prefix_exists):
        if(hasIdenticalAS):
            """
            (1) covered ROA found, 
            (2) Identical AS found
            (3) but can't found matched ROA.
            It is highly likely due to misconfiguration.
            """
            result = BGP_PFXV_STATE_MISCONF
            r = ",".join(map(str, [result, vrp_asID, "+".join(list(covered_prefixes))]))
            results.append( r ) 
        else:
            result = BGP_PFXV_STATE_SUBHIJACK
            r = ",".join(map(str, [result, vrp_asID, "None"] ))
            results.append( r ) 
            
        """
        print prefix_addr, prefix_len, asID
        print map(binary2ip, entries)
        for binary_prefix in entries:
            print roa_px[binary_prefix]
        print "--"
        """
    
    return results

def parseRISandRouteView(line):
    if("INCOMPLETE" in line): return None

    c = line.split("|")
    
    try:
        vp      = c[0]
        time    = c[2]

        m, d, y = time.split(' ')[0].split("/")
        time    = "20" + y + m + d
        datetime.strptime(time, "%Y%m%d")


        peer    = c[4]
        peerASN = c[5]

        as_path = c[7].split("{")[0].rstrip()
        as_path = map(lambda v: v.split(":")[0], as_path.split(" "))

        origin  = int(as_path[-1])


        prefix_addr, prefix_len = c[6].split("/")

        return (time, (peer, peerASN, prefix_addr, int(prefix_len), "+".join(as_path), origin))

    except:
        return None

def parseAkamaiTable(line):
    c =  line.split("|")

    if("INCOMPLETE" in line): return None # tijay added at Apr 27

    try:
        time    = c[1]
        time    = datetime.utcfromtimestamp(int(time)).strftime('%Y%m%d')

        peer    = c[3]
        peerASN = c[4]

        as_path = c[6].split("{")[0].rstrip()
        as_path = map(lambda v: v.split(":")[0], as_path.split(" "))

        try   : origin  = int(as_path[-1])
        except: return None

        prefix_addr, prefix_len = c[5].split("/")

        return (time, (peer, peerASN, prefix_addr, int(prefix_len), "+".join(as_path), origin))
    except:
        return None 


def parseAkamai(line):
    c =  line.split("|")

    if("INCOMPLETE" in line): return None # tijay added at Apr 27

    try:
        if(c[2] != "A"): return None

        time    = c[1]
        time    = datetime.utcfromtimestamp(int(time)).strftime('%Y%m%d')

        peer    = c[3]
        peerASN = c[4]

        as_path = c[6].split("{")[0].rstrip()
        as_path = map(lambda v: v.split(":")[0], as_path.split(" "))

        try   : origin  = int(as_path[-1])
        except: return None

        prefix_addr, prefix_len = c[5].split("/")

        return (time, (peer, peerASN, prefix_addr, int(prefix_len), "+".join(as_path), origin))
    except:
        return None 

def parse(dataset, line):
    if(dataset == "akamai"):
        return parseAkamai(line)
    elif(dataset == "akamai-bgp-table"):
        return parseAkamaiTable(line)
    else:
        return parseRISandRouteView(line)

def sanityCheck( (time, (peer, peerASN, prefix_addr, prefix_len, as_path, origin))):
    try:
        int(origin)
        int(prefix_len)
    except:
        return False
    
    return True


def parseROA(line):
    if("#" in line): return  None # header 

    time, prefix_addr, prefix_len, maxlen, asID, num_ip, cc, tal = line.rstrip().split("\t")
    prefix_len = int(prefix_len)
    if(maxlen == "None"):
        maxlen = prefix_len

    maxlen =  int(maxlen)
    asID = int(asID) 
    return (time, (prefix_addr, prefix_len, maxlen, asID))

def makeROABinaryPrefixDict(list_roas):
    roas = {}
    smtree_v4 = {}
    smtree_v6 = {}

    for prefix_addr, prefix_len, max_len, asID in list_roas:
        binary_prefix = ip2binary(prefix_addr, prefix_len)

        if(binary_prefix not in roas):
            roas[binary_prefix] = set()
        roas[binary_prefix].add( (prefix_addr, prefix_len, max_len, asID) )
        if(":" in prefix_addr):
            smInsert(smtree_v6, binary_prefix)
        else:
            smInsert(smtree_v4, binary_prefix)

    return roas, smtree_v4, smtree_v6

def getOrgCountry(caida_as_org, days,  date, asnum):
    try:
        diff = map(lambda v: abs( (datetime.strptime(v, "%Y%m%d") - datetime.strptime(date, "%Y%m%d")).days), days)
        dbdate = days[diff.index(min(diff))]
        
        asnum = str(asnum)
        if asnum not in caida_as_org[dbdate]:
            return "None", "None"
    
        org, country = caida_as_org[dbdate][asnum]
        if(country == ""): country = 'None'
        if(org == ""): org = 'None'

        return unicode(org), unicode(country)
    except:
        return "None", "None"

def getASRelationship(caida_as_rel, days, date, asnum1, asnum2):
    days = sorted(caida_as_rel.keys())
    diff = map(lambda v: abs((datetime.strptime(v, "%Y%m%d") - datetime.strptime(date, "%Y%m%d")).days), days)
    dbdate = days[diff.index(min(diff))]

    """
    key = str(asnum1) + "+" + str(asnum2)
    if( key in caida_as_rel[dbdate]):
        return caida_as_rel[dbdate][key]
    else:
        return "None"
    """

    if(asnum1 in caida_as_rel[dbdate] and asnum2 in caida_as_rel[dbdate][asnum1]):
        return caida_as_rel[dbdate][asnum1][asnum2]
    elif(asnum2 in caida_as_rel[dbdate] and asnum1 in caida_as_rel[dbdate][asnum2]):
        return -1 * caida_as_rel[dbdate][asnum2][asnum1]
    return "None"

def addMetaInformation(v, origin, time, caida_as_org, caida_as_rel, caida_as_org_days, caida_as_rel_days):
    try:
        verify = []
        for r in v:
            verify_state, vrp_asID, covered_prefixes = r.split(",")

            vrp_isp, vrp_country = getOrgCountry(caida_as_org, caida_as_org_days, time, vrp_asID)
            vrp_rel = getASRelationship(caida_as_rel, caida_as_rel_days, time, vrp_asID, origin)
            verify.append( ",".join([verify_state, vrp_asID, vrp_isp.replace(",", " "), vrp_country, vrp_rel, covered_prefixes]))
    
    except:
        pass

    return "\t".join(verify)

def runSparkVerify(sc, dataset, year, month, dates):
    readPath = []
    roa_prefix_asn = []
    savePath = "/user/tjchung/rpki/results/bgp-verify/%s/%s" % (dataset, year + month + dates[0] +"-" +dates[-1] )

    for d in dates:
        r = "hdfs:///user/tjchung/rpki/dataset/daily/%s-reduced/%s/%s/%s" % (dataset, year, month, year+month+d)
        if(hdfs.path.exists(r)): readPath.append(r)
        p = "hdfs:///user/tjchung/rpki/ripe/ripe-objects/roa-prefix-asn/%s/%s" % (year, year + month + d)
        if(hdfs.path.exists(p)): roa_prefix_asn.append(p)
    
    readPath = ",".join(readPath)
    roa_prefix_asn = ",".join(roa_prefix_asn)
    
    print savePath

    try: hdfs.rmr(savePath)
    except: pass
    
    caida_as_org        = json.load(open("/net/data-backedup/rpki/caida-as-org/data/as2isp.json"))
    caida_as_rel        = json.load(open("/net/data-backedup/rpki/caida-as-rel/data/caida-as-rel.json"))
    caida_as_org_days   = sorted(caida_as_org.keys())
    caida_as_rel_days   = sorted(caida_as_rel.keys())
    
    roa_px_dict  = sc.textFile(roa_prefix_asn)\
            .map(parseROA)\
            .filter(lambda v: v is not None)\
            .groupByKey()\
            .map(lambda (time, list_roas): (time, makeROABinaryPrefixDict(list_roas)))\
            .collectAsMap()

    roa_px_dict         = sc.broadcast(roa_px_dict).value
    caida_as_org        = sc.broadcast(caida_as_org).value
    caida_as_rel        = sc.broadcast(caida_as_rel).value
    caida_as_org_days   = sc.broadcast(caida_as_org_days).value
    caida_as_rel_days   = sc.broadcast(caida_as_rel_days).value
    
    print 'roa_px_dict is broadcasted' 

    #.map(parseRISandRouteView)\
    #.map(parseAkamai)\
    verify = sc.textFile(readPath)\
            .map(lambda v: parse(dataset, v))\
            .filter(lambda v: v is not None)\
            .filter(sanityCheck)\
            .map(lambda ( time, (peer, peerASN, prefix_addr, prefix_len, as_path, origin)):\
                        ( time, peer, peerASN, prefix_addr, prefix_len, as_path, origin, getOrgCountry(caida_as_org, caida_as_org_days, time, origin), validateOrigin(prefix_addr, prefix_len, origin, roa_px_dict, time)))\
            .filter(lambda (time, peer, peerASN, prefix_addr, prefix_len, as_path, origin, (origin_isp, origin_country), v): v is not None)\
            .map(lambda (time, peer, peerASN, prefix_addr, prefix_len, as_path, origin, (origin_isp, origin_country), v):\
                (time, peer, peerASN, prefix_addr, prefix_len, as_path, origin, origin_isp.replace(",", " "), origin_country, addMetaInformation(v, origin, time, caida_as_org, caida_as_rel, caida_as_org_days, caida_as_rel_days)))\
            .map(toTSV)

    #for i in verify.take(10): print i
    verify.saveAsTextFile(savePath)    

def runSparkVerifyWithoutMetaInfo(sc, dataset, year, month, dates):
    readPath = []
    roa_prefix_asn = []

    savePath = "/user/tjchung/rpki/results/bgp-verify-nometa/%s/%s" % (dataset, year + month + dates[0] +"-" +dates[-1] )
    #savePath = "/user/tjchung/rpki/results/bgp-verify-nometa-noIncomplete/%s/%s" % (dataset, year)
    
    subdirs = []
    if(dataset == "routeviews"):
        l = hdfs.fs.hdfs().list_directory("/user/tjchung/rpki/dataset/daily/routeviews-reduced")
        subdirs = map(lambda v: v["name"].split("/")[-1], l)
    
    tals = ["apnic", "apnic-iana", "apnic-afrinic", "apnic-arin", "apnic-lacnic ","apnic-ripe", "lacnic", "ripencc", "arin",  "afrinic", "localcert"]
    #for month in months: 
    for d in dates:
        if(len(subdirs) != 0): # this only applies to "routeviews"
            for sub in subdirs:
                r = "/user/tjchung/rpki/dataset/daily/%s-reduced/%s/%s" % (dataset, sub, year+month+d)

                if(hdfs.path.exists(r)): readPath.append(r)
        else:
            if(dataset == "akamai-bgp-table"):
                r = "/user/tjchung/rpki/dataset/daily/%s-reduced/%s/%s" % (dataset, year, year+month+d)
            else:
                r = "/user/tjchung/rpki/dataset/daily/%s-reduced/%s/%s/%s" % (dataset, year, month, year+month+d)
            if(hdfs.path.exists(r)): readPath.append(r)

    
        for tal in tals:
            p = "/user/tjchung/rpki/ripe/ripe-new-objects/roa-prefix-asn/%s/%s-%s.txt" % (year, year + month + d, tal)
            if(hdfs.path.exists(p)): roa_prefix_asn.append(p)
        
    readPath = ",".join(readPath)
    roa_prefix_asn = ",".join(roa_prefix_asn)
    
    print 'tijay log'
    print readPath
    print roa_prefix_asn
    print savePath
    
    try: hdfs.rmr(savePath)
    except: pass
    
    roa_px_dict  = sc.textFile(roa_prefix_asn)\
            .map(parseROA)\
            .filter(lambda v: v is not None)\
            .groupByKey()\
            .map(lambda (time, list_roas): (time, makeROABinaryPrefixDict(list_roas)))\
            .collectAsMap()

    roa_px_dict         = sc.broadcast(roa_px_dict).value
    
    print 'roa_px_dict is broadcasted' 
    #.filter(lambda ( time, (peer, peerASN, prefix_addr, prefix_len, as_path, origin)): int(origin) == 39572 and peer == "84.53.143.254" and prefix_addr =="2a02:b48:8101::")\

    verify = sc.textFile(readPath)\
            .map(lambda v: parse(dataset, v))\
            .filter(lambda v: v is not None)\
            .filter(sanityCheck)\
            .map(lambda ( time, (peer, peerASN, prefix_addr, prefix_len, as_path, origin)):\
                        ( time, peer, peerASN, prefix_addr, prefix_len, as_path, origin, validateOrigin(prefix_addr, prefix_len, origin, roa_px_dict, time)))\
            .filter(lambda (time, peer, peerASN, prefix_addr, prefix_len, as_path, origin, v): v is not None)\
            .map(lambda (time, peer, peerASN, prefix_addr, prefix_len, as_path, origin, v): (time, peer, peerASN, prefix_addr, prefix_len, as_path, origin, "\t".join(v)))\
            .map(toTSV)
    
    #for i in verify.collect(): print i
    verify.saveAsTextFile(savePath)    

def runSparkCalcPrefixes(sc, dataset, year, month, dates ):

    readPath = []
    subdirs = []

    if(dataset == "routeviews"):
        l = hdfs.fs.hdfs().list_directory("/user/tjchung/rpki/dataset/daily/routeviews-reduced")
        subdirs = map(lambda v: v["name"].split("/")[-1], l)

    for d in dates:
        if(len(subdirs) != 0): # this only applies to "routeviews"
            for sub in subdirs:
                r = "/user/tjchung/rpki/dataset/daily/%s-reduced/%s/%s" % (dataset, sub, year+month+ d)
                if(hdfs.path.exists(r)): readPath.append(r)
        else:
            r = "/user/tjchung/rpki/dataset/daily/%s-reduced/%s/%s/%s" % (dataset, year, month, year+month+d)
            if(hdfs.path.exists(r)): readPath.append(r)


    readPath = ",".join(readPath)
    #print readPath
    num = sc.textFile(readPath)\
            .map(lambda v: parse(dataset, v))\
            .filter(lambda v: v is not None)\
            .filter(sanityCheck)\
            .map(lambda ( time, (peer, peerASN, prefix_addr, prefix_len, as_path, origin)): (prefix_addr, prefix_len, origin))\
            .distinct()\
            .collect()
    '''
    unique (prefix_addr, prefix_len) during the last month
        Routeviews  :   958,544
        Akamai      : 1,939,158
        RIPE-RIS    :   905,916

    unique (prefix_addr, prefix_len, origin) during the last month
        Routeviews  : 1,000,221
        Akamai      : 1,982,595
        RIPE-RIS    :   938,262

    unique (prefix_addr, prefix_len, origin) during the last day of the dataset:
        Routeviews  : 790,516
        Akamai      : 684,169
        RIPE-RIS    : 745,594
    '''
    print len(num)


def fetch(savePath, dstPath, saveDir):
    hdfs.get(savePath, os.path.join(dstPath, saveDir))
    mergeAndSort(os.path.join(dstPath, saveDir))

if __name__ == "__main__":
    conf = SparkConf()\
            .setAppName("RPKI: Akamai dataset verification")
            #.setMaster("local[20]")
            #.set("spark.executor.heartbeatInterval","1799")\
            #.set("dfs.client.socket-timeout", "300000")\
            #.set("java.net.SocketTimeoutException", "300000")
            #.set("spark.speculation", "false")\
            #.set("spark.kryoserializer.buffer.max", "512M")\
            #.set("spark.driver.maxResultSize", "8g")\
    #print sc.getConf().getAll() 
    
    sc = SparkContext(conf=conf)

    sc.setLogLevel("WARN")
    
    datasets = ["routeviews", "akamai", "ripe-ris"]
    for dataset in datasets:
        dates = ["27"]
        if(dataset == "akamai"):
            dates = ["31"]
        #dates = map(lambda v: "%02d" % v, range(1, 32))
        #runSparkCalcPrefixes(sc, dataset, "2018", "12", dates)


    sc.addPyFile("lib.zip")
        
    #datasets = ["akamai"] #"routeviews", "akamai", "ripe-ris"]
    #dataset = "akamai-bgp-table"
    #dates = map(lambda v: "%02d" % v, range(1, 32))
    #runSparkVerifyWithoutMetaInfo(sc, dataset, "2018", "12", dates)

    #datasets = ["routeviews", "akamai", "ripe-ris"]
    #datasets = ['ripe-ris']
    dataset = 'akamai-bgp-table'
    dates = map(lambda v: "%02d" % v, range(1, 32))
    runSparkVerifyWithoutMetaInfo(sc, dataset, "2018", "09", dates)
    runSparkVerifyWithoutMetaInfo(sc, dataset, "2018", "10", dates)

    datasets = ['akamai-bgp-table']
    for dataset in datasets:
        years = range(2011, 2019)
        #/user/tjchung/rpki/results/bgp-verify-nometa/routeviews/20161101-31
        for year in years:
            if("akamai" in dataset and year < 2018 ): continue
            #if(year != 2017): continue
            year = str(year)
            for month in range(1, 13): 
                if("akamai" in dataset and year == "2018" and month < 6): continue
                month = str("%02d") % month
                for dates in [range(1, 32)]:
                    #dates = range(1,32)
                    dates = map(lambda v: "%02d" % v, dates)
                    print "[tijay] runSpark verify %s%s%s "  % (year, month,dates)
                    #runSparkVerifyWithoutMetaInfo(sc, dataset, year, month, dates)
                #sys.exit(1)
    sc.stop()
    #fetch(savePath, dstPath, saveDir)

