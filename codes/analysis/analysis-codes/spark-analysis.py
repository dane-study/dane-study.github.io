"""

"""

from pyspark import SparkContext, StorageLevel, SparkConf, broadcast
from pyspark.sql import SQLContext, Row
from datetime import datetime
from datetime import date, timedelta
from ipaddress import *
import pydoop.hdfs as hdfs
import ujson as json
import os
import sys
import shutil

BGP_PFXV_STATE_NOT_FOUND   = 0 # Unknown
BGP_PFXV_STATE_VALID       = 1 # Valid
BGP_PFXV_STATE_HIJACKING   = 2 # Covered ROA found, non-identical AS, matched
BGP_PFXV_STATE_MISCONF     = 3 # Covered ROA found, identical AS, but non-matched
BGP_PFXV_STATE_SUBHIJACK   = 4 # Covered ROA Found, non-identical AS, non-matched
TMP_PATH = "/tmp/spark"

"""
Source: http://bgpfilterguide.nlnog.net/guides/bogon_asns/

BOGON_ASNS = [ 0,                      # RFC 7607
              23456,                  # RFC 4893 AS_TRANS
              64496..64511,           # RFC 5398 and documentation/example ASNs
              64512..65534,           # RFC 6996 Private ASNs
              65535,                  # RFC 7300 Last 16 bit ASN
              65536..65551,           # RFC 5398 and documentation/example ASNs
              65552..131071,          # RFC IANA reserved ASNs
              4200000000..4294967294, # RFC 6996 Private ASNs
              4294967295 ];           # RFC 7300 Last 32 bit ASN

"""
BOGON_ASNS = set(map(str, ([0, 23456] + range(64496, 64512) + range(64512, 65534) + [65535] + range(65536, 65551) + range(65552, 131071))))

_verify_state = {1: "BGP_PFXV_STATE_VALID",
                 2: "BGP_PFXV_STATE_HIJACKING",
                 3: "BGP_PFXV_STATE_MISCONF",
                 4: "BGP_PFXV_STATE_SUBHIJACK"}

def getListVRPs(list_of_dict):
    s = set()
    for another_list in list_of_dict:
        for d in another_list:
            s.add(",".join([str(d['verify_state']), str(d['vrp_asID']), d['vrp_isp'], d['vrp_country'], str(d['vrp_relationship']), d['covered_prefix']]))

    return "\t".join(list(s))


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

def getMergeAndSort(savePath, localPath, label = None):
    tmp_path = "/tmp/tmp-spark"
    try: os.mkdirs(tmp_path)
    except: pass

    hdfs.get(savePath, tmp_path)

    cmdMerge = """find %s -name "*" -print0 | xargs -0 cat >> /tmp/tmp-spark""" % tmp_path
    print cmdMerge
    os.system(cmdMerge)

    cmdSort  = "sort -k1,1 /tmp/tmp-spark > {0}".format(os.path.join(localPath, localPath.split("/")[-1] +".tsv"))

    os.system(cmdSort)
    
    if(label is not None):
        cmd = "sed -i '1s/^/%s\\n/' %s" % (label, path +  ".tsv")
        print cmd
        os.system(cmd)

    cmdErase = "rm /tmp/tmp-spark"
    os.system(cmdErase)

    try: shutil.rmtree(tmp_path)
    except: pass

def mergeAndSort(path, label=None):
    try: os.mkdirs(path)
    except: pass

    #cmdMerge = "cat {0}/* >> /tmp/tmp-spark".format(path)
    cmdMerge = """find %s -name "*" -print0 | xargs -0 cat >> /tmp/tmp-spark""" % path
    print cmdMerge
    os.system(cmdMerge)

    cmdSort  = "sort -k1,1 /tmp/tmp-spark > {0}".format(path + ".tsv")
    os.system(cmdSort)
    
    if(label is not None):
        cmd = "sed -i '1s/^/%s\\n/' %s" % (label, path +  ".tsv")
        print cmd
        os.system(cmd)

    cmdErase = "rm /tmp/tmp-spark"
    os.system(cmdErase)

def grep(path, dates, label=None):
    for date in dates:
        new_path = "/".join(path.split("/")[:-1]) + "/%s.tsv" % date
        cmdMerge = """find %s -name "*" -print0 | xargs -0 cat | grep "%s" >> /tmp/tmp-spark""" % (path, date)
        os.system(cmdMerge)
        
        os.system("rm %s" % new_path)
        cmdSort  = "sort -k1,1 /tmp/tmp-spark > {0}".format(new_path)
        os.system(cmdSort)
        
        if(label is not None):
            cmd = "sed -i '1s/^/%s\\n/' %s" % (label, new_path)
            print cmd
            os.system(cmd)

        cmdErase = "rm /tmp/tmp-spark"
        os.system(cmdErase)


def toTSV(data):
    return "\t".join(unicode(d) for d in data)


def isRPKIEnabled(line, hasMeta=False):
    l = line.rstrip().split("\t") 
    #time, peer, peerASN, prefix_addr, prefix_len, as_path, origin_as, origin_isp, origin_country = l[:9]
    if(hasMeta) : s = l[9:]
    else        : s = l[7:]

    if(len(s) == 0): RPKI_ENABLED = False
    else           : RPKI_ENABLED = True

    return RPKI_ENABLED 

def parseVerifyLineUniquePrefixNoMeta(line):
    l = line.rstrip().split("\t") 

    time, prefix_addr, prefix_len, origin_as = l[:4]
    s = l[4:]

    j = {'time': time,
            'prefix_addr': prefix_addr,
            'prefix_len': int(prefix_len),
            'origin_as': int(origin_as),
            'vrps': []}

    for _ in s:
        verifyState, vrp_asID, vrp_isp, vrp_country, vrp_relationship, covered_prefix = _.rstrip().split(",")
        tmp = {'verify_state': int(verifyState), 
                'vrp_asID' : int(vrp_asID),
                'vrp_isp'  : vrp_isp,
                'vrp_country' : vrp_country,
                'vrp_relationship' : vrp_relationship,
                'covered_prefix' : covered_prefix}

        j['vrps'].append(tmp)
    return j

def parseVerifyLineUniquePrefix(line, hasASPath = False):

    l = line.rstrip().split("\t") 

    #time, prefix_addr, prefix_len, as_path, origin_as, origin_isp, origin_country = l[:7]
    if(not hasASPath):
        time, prefix_addr, prefix_len, origin_as, origin_isp, origin_country = l[:6]
        if(origin_as in BOGON_ASNS): return None

        s = l[6:]

        j = {'time': time,
                'prefix_addr': prefix_addr,
                'prefix_len': int(prefix_len),
                #'as_path': as_path,
                'origin_as': int(origin_as),
                'origin_isp': origin_isp,
                'origin_country': origin_country,
                'vrps': []}
    else:
        time, prefix_addr, prefix_len, as_path, origin_as, origin_isp, origin_country = l[:7]
        if(origin_as in BOGON_ASNS): return None
        s = l[7:]

        j = {'time': time,
                'prefix_addr': prefix_addr,
                'prefix_len': int(prefix_len),
                'as_path': as_path,
                'origin_as': int(origin_as),
                'origin_isp': origin_isp,
                'origin_country': origin_country,
                'vrps': []}

    for _ in s:
        verifyState, vrp_asID, vrp_isp, vrp_country, vrp_relationship, covered_prefix = _.rstrip().split(",")
        tmp = {'verify_state': int(verifyState), 
                'vrp_asID' : int(vrp_asID),
                'vrp_isp'  : vrp_isp,
                'vrp_country' : vrp_country,
                'vrp_relationship' : vrp_relationship,
                'covered_prefix' : covered_prefix}

        j['vrps'].append(tmp)

    return j


def parseVerifyline(line, hasMeta = False, isJson = False): 
    if(isJson):
        return json.loads(line)

    l = line.rstrip().split("\t") 
    
    if(hasMeta):
        time, peer, peerASN, prefix_addr, prefix_len, as_path, origin_as, origin_isp, origin_country, origin_registry = l[:10]
        if(origin_as in BOGON_ASNS): return None
        s = l[10:]

        if("/" in as_path): return None
        
        j = {   'time': time,
                'peer': peer,
                'peerASN': peerASN,
                'prefix_addr': prefix_addr,
                'prefix_len': int(prefix_len),
                'as_path': as_path,
                'origin_as': int(origin_as),
                'origin_isp': origin_isp,
                'origin_country': origin_country,
                'origin_registry': origin_registry,
                'vrps': []}
        
        for _ in s:
            verifyState, vrp_asID, vrp_isp, vrp_country, vrp_relationship, vrp_ever_relationship, vrp_registry, covered_prefix = _.rstrip().split(",")
            tmp = {'verify_state': int(verifyState), 
                    'vrp_asID' : vrp_asID,
                    'vrp_isp'  : vrp_isp,
                    'vrp_country' : vrp_country,
                    'vrp_relationship' : vrp_relationship,
                    'vrp_ever_relationship' : vrp_ever_relationship,
                    'vrp_registry' : vrp_registry,
                    'covered_prefix' : covered_prefix}

            j['vrps'].append(tmp)
    
        return j

    else:
        time, peer, peerASN, prefix_addr, prefix_len, as_path, origin_as = l[:7]
        if(origin_as in BOGON_ASNS): return None
        
        if("/" in as_path): return None

        j = {   'time': time,
                'peer': peer,
                'peerASN': peerASN,
                'prefix_addr': prefix_addr,
                'prefix_len': int(prefix_len),
                'as_path': as_path,
                'origin_as': int(origin_as),
                #'origin_isp': origin_isp,
                #'origin_country': origin_country,
                'vrps': []}
                
        s = l[7:]

        for _ in s:
            verifyState, vrp_asID, covered_prefix = _.rstrip().split(",")
            tmp = {'verify_state': int(verifyState), 
                    'vrp_asID' : vrp_asID,
                    'vrp_isp'  : "None",
                    'vrp_country' : "None",
                    'vrp_relationship' : "None",
                    'covered_prefix' : covered_prefix}

            j['vrps'].append(tmp)
    
        return j

def dumpJsonLine(j):
    r = []
    for v in j['vrps']:
        r.append(",".join([str(v['verify_state']), v['vrp_asID'], v['vrp_isp'].replace(",", " "), v['vrp_country'], v['vrp_relationship'], v['covered_prefix']]))

    return "\t".join([j['time'], j['peer'], j['peerASN'], j['prefix_addr'], str(j['prefix_len']), j['as_path'], str(j['origin_as']), j['origin_isp'].replace(",", " "), j['origin_country'], "\t".join(r)])

def classifyBGPAdvSparse(j):
    if( len(j['vrps']) == 0 ):
        return "non-rpki"
    
    verify_state = set()
    for vrp in j['vrps']: 
        verify_state.add(vrp['verify_state'])
    
    if( BGP_PFXV_STATE_VALID in verify_state):
        return "rpki-valid"
    
    return "rpki-invalid"  

def getInvalidReasons(j):
    return list(set(map(lambda v: v['verify_state'], j['vrps'])))

def getInvalidReason(j):
    _verify_states = set(map(lambda v: v['verify_state'], j['vrps']))
    if(BGP_PFXV_STATE_MISCONF in _verify_states):
        return BGP_PFXV_STATE_MISCONF
    if(BGP_PFXV_STATE_HIJACKING in _verify_states):
        return BGP_PFXV_STATE_HIJACKING
    else:
        return BGP_PFXV_STATE_SUBHIJACK

def isLargerSlash24(j):
    return j['prefix_len'] > 24

def isLargerSlashX(j, x):
    return j['prefix_len'] >= int(x)

def isIPv4v6(j, ip_type):
    if (ip_type == "ipv4"):
        return "." in j['prefix_addr'] 
    elif (ip_type == "ipv6"):
        return ":" in j['prefix_addr'] 
    # ip_type == "all"
    return True

def addMetaInformation(j, caida_as_org, caida_as_rel, caida_as_org_days, caida_as_rel_days):

    time     = j['time']
    origin   = j['origin_as']  

    origin_isp, origin_country = getOrgCountry(caida_as_org, caida_as_org_days, time, j['origin_as'])

    j['origin_isp'] = origin_isp
    j['origin_country'] = origin_country

    for r in j['vrps']:
        vrp_asID = r['vrp_asID']

        vrp_isp, vrp_country = getOrgCountry(caida_as_org, caida_as_org_days, time, vrp_asID)
        vrp_rel = getASRelationship(caida_as_rel, caida_as_rel_days, time, vrp_asID, origin)

        r['vrp_isp']            = vrp_isp
        r['vrp_country']        = vrp_country
        r['vrp_relationship']   = vrp_rel

    return j

def onlyHijackAttempt(v):
    r = getInvalidReason(v)
    return r == BGP_PFXV_STATE_HIJACKING or r == BGP_PFXV_STATE_SUBHIJACK

def classifyHijack(j):
    ddos_protection = [20940, 16625, 32787, # akamai
            209, 3561, # CenturyLink
            13335, # CloudFlare
            19324, #DOSarrest
            55002, #F5 Networks
            19551, #Incapsula
            3549, 3356, 11213, 10753, #Level 3
            7786, 12008, 19905, #Neustar
            26415, 30060, # Verisign
            200020 #Nawas
            ]

    r = getInvalidReason(j)
    status = "None"

    for v in j['vrps']:
        vs  = v['verify_state']
        isp = v['vrp_isp']
        vrp_relationship = v['vrp_relationship']

        origin_as = j['origin_as']

        if( (vs == BGP_PFXV_STATE_SUBHIJACK and r == BGP_PFXV_STATE_SUBHIJACK) or
            (vs == BGP_PFXV_STATE_HIJACKING and r == BGP_PFXV_STATE_HIJACKING)):
            if(isp != "None" and j['origin_isp'] == isp): 
                status = "sameISP"
                return status

            elif (vrp_relationship != "None"):
                """
                <provider-as>|<customer-as>|-1
                <peer-as>|<peer-as>|0
                """
                if(vrp_relationship == "-1"):
                    status = "provider"
                elif(vrp_relationship == "1"):
                    status = "customer"
                elif(vrp_relationship == "0"):
                    status = "peer"

                return status
            
            elif ( origin_as in ddos_protection):
                status = "DDoS"
                return status

    return status  # should be None

def runSparkCountNumAnnouncements(sc, dataset):
    print 'runSparkCountNumAnnouncements', dataset
    readPath  = "/spark-hdfs-path/rpki/results/bgp-verify-nometa/%s/*" % (dataset)
    
    if(dataset == "akamai-public-prefix"):
        # this dataset only contains v4
        s = sc.textFile(readPath)\
                .count()
    else:
        s = sc.textFile(readPath)\
                .filter(lambda v: ":" not in v)\
                .count()
    
    # ALL
    # RIPE-RIS      : 10,588,676,329
    # RouteViews    : 29,804,884,527

    # IPV4
    # RIPE-RIS      :  9,647,948,673
    # RouteViews    : 28,526,919,866


    print s

def runSparkCalcRPKIEnabledAdv(sc, dataset, ip_type, year):
    print "runSparkCalcRPKIEnabledAdv", dataset, year
    """
        It calculates the *number* of BGP announcements that 
            (1) can't be verified against RPKI
            (2) can be verified against RPKI and invalid
            (3) can be verified against RPKI and valid
        
        Note: 
            BGP announcements are distinct based on three tuples:
            (peer_ip, prefix_addr, as_path) given on a date
    """
    
    readPath  = "/spark-hdfs-path/rpki/results/bgp-verify-nometa/%s/%s*" % (dataset, year)
    savePath  = "/spark-hdfs-path/rpki/results/rpki-enabled-adv-%s/%s/%s" % (ip_type, dataset, year)
    localPath = "/local-spark-result-path/research/rpki/src/spark/results/rpki-enabled-adv-%s/%s/%s" % (ip_type, dataset, year)


    try: hdfs.rmr(savePath)
    except: pass
    
    isJson = False 
    if(dataset  == "akamai-public-prefix"): isJson = True
    hasMeta   = False
    k = sc.textFile(readPath)\
            .map(lambda v: parseVerifyline(v, hasMeta, isJson))\
            .filter(lambda v: v is not None)\
            .filter(lambda v: isIPv4v6(v, ip_type))\
            .map(lambda j: ( (j['time'], classifyBGPAdvSparse(j)), 1))\
            .reduceByKey(lambda a, b: a + b)\
            .map(lambda ( (time, rpki_type), cnt): (time, rpki_type, cnt))

    sqlContext = SQLContext(sc)
    df = sqlContext.createDataFrame( k, ['timestamp', 'rpkiType', 'cnt'] )

    grouped = df.rdd\
                .map(lambda row: (row.timestamp, (row.rpkiType, row.cnt)))\
                .groupByKey()

    def make_row(kv):
        k, vs = kv # time: [(-1, cnt), (0, cnt), (1, cnt)] ...  
        tmp = dict(list(vs) + [("timestamp", k)])
        return Row(**{k: tmp.get(k, 0) for k in ["timestamp", "non-rpki", "rpki-invalid", "rpki-valid"]})
    
    reshaped = sqlContext.createDataFrame(grouped.map(make_row))

    k = reshaped.rdd\
            .map(lambda row: (row['timestamp'], row['non-rpki'], row['rpki-invalid'], row['rpki-valid']))\
            .map(toTSV)
    
    k.saveAsTextFile(savePath)
    
    try: shutil.rmtree(localPath)
    except: pass

    try: os.makedirs(localPath)
    except: pass
    
    hdfs.get(savePath, localPath)
    mergeAndSort(localPath)


def runSparkValidationUniquePrefixAllPrefix(sc, dataset, ip_type):
    print "runSparkValidationUniquePrefixAllPrefix"

    readPath  = "/spark-hdfs-path/rpki/results/rpki-enabled-unique-prefix-asn-%s/%s" % (ip_type, dataset)
    savePath  = "/spark-hdfs-path/rpki/results/rpki-enabled-unique-prefix-asn-adv-%s-nofiltering/%s" % (ip_type, dataset)

    localPath = "/local-spark-result-path/research/rpki/src/spark/results/rpki-enabled-unique-prefix-asn-adv-%s-nofiltering/%s" % (ip_type, dataset)


    try: hdfs.rmr(savePath)
    except: pass


    k = sc.textFile(readPath)\
            .map(lambda v: parseVerifyLineUniquePrefix(v))\
            .filter(lambda v: v is not None)\
            .filter(lambda v: notDataError(dataset, v))\
            .filter(lambda v: isIPv4v6(v, ip_type))\
            .map(lambda j: ( (j['time'], classifyBGPAdvSparse(j)), 1))\
            .reduceByKey(lambda a, b: a + b)\
            .map(lambda ( (time, rpki_type), cnt): (time, rpki_type, cnt))

    sqlContext = SQLContext(sc)
    df = sqlContext.createDataFrame( k, ['timestamp', 'rpkiType', 'cnt'] )

    grouped = df.rdd\
                .map(lambda row: (row.timestamp, (row.rpkiType, row.cnt)))\
                .groupByKey()

    def make_row(kv):
        k, vs = kv # time: [(-1, cnt), (0, cnt), (1, cnt)] ...  
        tmp = dict(list(vs) + [("timestamp", k)])
        return Row(**{k: tmp.get(k, 0) for k in ["timestamp", "non-rpki", "rpki-invalid", "rpki-valid"]})
    
    reshaped = sqlContext.createDataFrame(grouped.map(make_row))

    k = reshaped.rdd\
            .map(lambda row: (row['timestamp'], row['non-rpki'], row['rpki-invalid'], row['rpki-valid']))\
            .map(toTSV)
    
    k.saveAsTextFile(savePath)
    
    try: shutil.rmtree(localPath)
    except: pass

    try: os.makedirs(localPath)
    except: pass
    
    hdfs.get(savePath, localPath)
    mergeAndSort(localPath)

    
def runSparkValidationUniquePrefix(sc, dataset, ip_type):
    
    readPath  = "/spark-hdfs-path/rpki/results/rpki-enabled-unique-prefix-asn-%s/%s" % (ip_type, dataset)
    savePath  = "/spark-hdfs-path/rpki/results/rpki-enabled-unique-prefix-asn-adv-%s/%s" % (ip_type, dataset)

    localPath = "/local-spark-result-path/research/rpki/src/spark/results/rpki-enabled-unique-prefix-asn-adv-%s/%s" % (ip_type, dataset)


    try: hdfs.rmr(savePath)
    except: pass


    k = sc.textFile(readPath)\
            .map(lambda v: parseVerifyLineUniquePrefix(v))\
            .filter(lambda v: v is not None)\
            .filter(lambda v: notDataError(dataset, v))\
            .filter(lambda v: isIPv4v6(v, ip_type))\
            .filter(lambda v: ip_type == "ipv6" or not isLargerSlash24(v))\
            .map(lambda j: ( (j['time'], classifyBGPAdvSparse(j)), 1))\
            .reduceByKey(lambda a, b: a + b)\
            .map(lambda ( (time, rpki_type), cnt): (time, rpki_type, cnt))

    sqlContext = SQLContext(sc)
    df = sqlContext.createDataFrame( k, ['timestamp', 'rpkiType', 'cnt'] )

    grouped = df.rdd\
                .map(lambda row: (row.timestamp, (row.rpkiType, row.cnt)))\
                .groupByKey()

    def make_row(kv):
        k, vs = kv # time: [(-1, cnt), (0, cnt), (1, cnt)] ...  
        tmp = dict(list(vs) + [("timestamp", k)])
        return Row(**{k: tmp.get(k, 0) for k in ["timestamp", "non-rpki", "rpki-invalid", "rpki-valid"]})
    
    reshaped = sqlContext.createDataFrame(grouped.map(make_row))

    k = reshaped.rdd\
            .map(lambda row: (row['timestamp'], row['non-rpki'], row['rpki-invalid'], row['rpki-valid']))\
            .map(toTSV)
    
    k.saveAsTextFile(savePath)
    
    try: shutil.rmtree(localPath)
    except: pass

    try: os.makedirs(localPath)
    except: pass
    
    hdfs.get(savePath, localPath)
    mergeAndSort(localPath)

def runSparkClassifyHijackingUniquePrefixDuration(sc, dataset, ip_type):
    readPath  = "/spark-hdfs-path/rpki/results/rpki-enabled-unique-prefix-asn-%s/%s" % (ip_type, dataset)
    savePath  = "/spark-hdfs-path/rpki/results/rpki-enabled-unique-prefix-classify-hijack-duration-%s/%s" % (ip_type, dataset)
    localPath = "/local-spark-result-path/research/rpki/src/spark/results/rpki-unique-prefix-classify-hijack-duration-%s/%s" % (ip_type, dataset)

    try: hdfs.rmr(savePath)
    except: pass


    k = sc.textFile(readPath)\
            .map(lambda v: parseVerifyLineUniquePrefix(v))\
            .filter(lambda v: v is not None)\
            .filter(lambda v: notDataError(dataset, v))\
            .filter(lambda v: isIPv4v6(v, ip_type))\
            .filter(lambda v: classifyBGPAdvSparse(v) == "rpki-invalid")\
            .filter(lambda v: ip_type == "ipv6" or not isLargerSlash24(v))\
            .filter(lambda v: onlyHijackAttempt(v))\
            .map(lambda v: ( (classifyHijack(v), v['prefix_addr'], v['prefix_len'], v['origin_as']), v['time']))\
            .groupByKey()\
            .map(lambda ((classifyHijack, prefix_addr, prefix_len, origin), list_of_time): (classifyHijack, prefix_addr, prefix_len, origin, len(set(list_of_time))))\
            .map(toTSV)\
            .saveAsTextFile(savePath)


    try: shutil.rmtree(localPath)
    except: pass

    try: os.makedirs(localPath)
    except: pass
    
    hdfs.get(savePath, localPath)
    mergeAndSort(localPath)

def runSparkClassifyHijackingUniquePrefixList(sc, dataset, ip_type):
    readPath  = "/spark-hdfs-path/rpki/results/rpki-enabled-unique-prefix-asn-%s/%s" % (ip_type, dataset)
    savePath  = "/spark-hdfs-path/rpki/results/rpki-enabled-unique-prefix-classify-hijack-list-%s/%s" % (ip_type, dataset)
    localPath = "/local-spark-result-path/research/rpki/src/spark/results/rpki-unique-prefix-classify-hijack-list-%s/%s" % (ip_type, dataset)

    try: hdfs.rmr(savePath)
    except: pass


    k = sc.textFile(readPath)\
            .map(lambda v: parseVerifyLineUniquePrefix(v))\
            .filter(lambda v: v is not None)\
            .filter(lambda v: notDataError(dataset, v))\
            .filter(lambda v: isIPv4v6(v, ip_type))\
            .filter(lambda v: classifyBGPAdvSparse(v) == "rpki-invalid")\
            .filter(lambda v: ip_type == "ipv6" or not isLargerSlash24(v))\
            .filter(lambda v: onlyHijackAttempt(v))\
            .map(lambda v: ((v['time'], classifyHijack(v)), json.dumps(v)))\
            .map(toTSV)\
            .saveAsTextFile(savePath)

    try: shutil.rmtree(localPath)
    except: pass

    try: os.makedirs(localPath)
    except: pass
    
    hdfs.get(savePath, localPath)
    mergeAndSort(localPath)


def runSparkClassifyHijackingUniquePrefix(sc, dataset, ip_type):

    readPath  = "/spark-hdfs-path/rpki/results/rpki-enabled-unique-prefix-asn-%s/%s" % (ip_type, dataset)
    savePath  = "/spark-hdfs-path/rpki/results/rpki-enabled-unique-prefix-classify-hijack-%s/%s" % (ip_type, dataset)
    localPath = "/local-spark-result-path/research/rpki/src/spark/results/rpki-unique-prefix-classify-hijack-%s/%s" % (ip_type, dataset)

    try: hdfs.rmr(savePath)
    except: pass

    k = sc.textFile(readPath)\
            .map(lambda v: parseVerifyLineUniquePrefix(v))\
            .filter(lambda v: v is not None)\
            .filter(lambda v: notDataError(dataset, v))\
            .filter(lambda v: isIPv4v6(v, ip_type))\
            .filter(lambda v: classifyBGPAdvSparse(v) == "rpki-invalid")\
            .filter(lambda v: ip_type == "ipv6" or not isLargerSlash24(v))\
            .filter(lambda v: onlyHijackAttempt(v))\
            .map(lambda v: ((v['time'], classifyHijack(v)), 1))\
            .reduceByKey(lambda a, b: a + b)\
            .map(lambda ( (time, status), cnt): (time, status, cnt))

    sqlContext = SQLContext(sc)
    df = sqlContext.createDataFrame( k, ['timestamp', 'hijackType', 'cnt'] )

    grouped = df.rdd\
                .map(lambda row: (row.timestamp, (row.hijackType, row.cnt)))\
                .groupByKey()

    def make_row(kv):
        k, vs = kv # time: [(-1, cnt), (0, cnt), (1, cnt)] ...  
        tmp = dict(list(vs) + [("timestamp", k)])
        return Row(**{k: tmp.get(k, 0) for k in ["timestamp", "sameISP", "provider", "customer", "peer", "DDoS", "None"]})
    
    reshaped = sqlContext.createDataFrame(grouped.map(make_row))

    k = reshaped.rdd\
            .map(lambda row: (row['timestamp'], row['sameISP'], row['provider'], row['customer'], row['peer'], row['DDoS'], row['None']))\
            .map(toTSV)
    
    k.saveAsTextFile(savePath)
    
    try: shutil.rmtree(localPath)
    except: pass

    try: os.makedirs(localPath)
    except: pass
    
    hdfs.get(savePath, localPath)
    mergeAndSort(localPath)

if __name__ == "__main__":
    conf    = SparkConf()\
            .setAppName("RPKI analysis")

    sc = SparkContext(conf=conf)
    sc.setLogLevel("WARN")

    datasets = ["ripe-ris", "routeviews"]

    for ip_type in ["ipv4", "ipv6"]:
        for dataset in datasets:    
            runSparkClassifyHijackingUniquePrefix(sc, dataset, ip_type)
            runSparkValidationUniquePrefixAllPrefix(sc, dataset, ip_type)
            runSparkValidationUniquePrefix(sc, dataset, ip_type)

            runSparkClassifyHijackingUniquePrefixList(sc, dataset, ip_type)
            runSparkClassifyHijackingUniquePrefixDuration(sc, dataset, ip_type)

            for year in range(2011, 2019): ## Due to the massive size of the dataset, we split the dataset into multiple years.
                year = str(year)
                runSparkCalcRPKIEnabledAdv(sc, dataset, ip_type, year)
    
    sc.stop()
    
