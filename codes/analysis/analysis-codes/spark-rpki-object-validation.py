from pyspark import SparkContext, StorageLevel, SparkConf, broadcast
from pyspark.sql import SQLContext, Row

from datetime import *
from ipaddress import *
from sumin_tree import *
from operator import itemgetter

import shutil
import os
import numpy as np
import ujson as json
import pydoop.hdfs as hdfs

def parseNRO(line, ip_type ):
    if ("prefix" in line): return None # header
    
    if(ip_type == "ipv4"):
        time, prefix, rir, date, country_code, status, b_s, b_c = line.split(",")
    else:
        time, prefix, rir, date, country_code, status = line.split(",")

    return ((time, rir), int(b_c))


def createDates(year):
    base = datetime(year=year, month=1, day=1)
    date_list = [ (base + timedelta(days=x)).strftime("%Y%m%d") for x in range(0, 365)]

    return date_list

def set_days_scope(caida_as_org_days, as_org_days, min_date, max_date):
    for _from, _to in zip(caida_as_org_days[:-1], caida_as_org_days[1:]):

        _from = datetime.strptime(_from, "%Y%m%d")
        _to   = datetime.strptime(_to, "%Y%m%d")

        span = (_to - _from).days

        for i in range(0, span):
            key = _from + timedelta(days=i)
            if( _from != min_date and _to != max_date):
                if( i < span/2):
                    as_org_days[ key.strftime("%Y%m%d") ] = _from.strftime("%Y%m%d")
                else:
                    as_org_days[ key.strftime("%Y%m%d") ] = _to.strftime("%Y%m%d")
            else:
                if(_from == min_date):
                    as_org_days[ key.strftime("%Y%m%d") ] = _to.strftime("%Y%m%d")
                else: # _to == max_date:
                    as_org_days[ key.strftime("%Y%m%d") ] = _from.strftime("%Y%m%d")


def mergeAndSort(path, label=None):

    cmdMerge = """find %s -name "*" -print0 | xargs -0 cat >> /tmp/tmp-spark""" % path
    os.system(cmdMerge)

    cmdSort  = "sort -k1,1 /tmp/tmp-spark > {0}".format(path + ".tsv")
    os.system(cmdSort)

    if(label is not None):
        cmd = "sed -i '1s/^/%s\\n/' %s" % (label, path +  ".tsv")
        print cmd
        os.system(cmd)

    cmdErase = "rm /tmp/tmp-spark"
    os.system(cmdErase)

def toTSV(data):
    return "\t".join(unicode(d) for d in data)

def toCSV(data):
    return ",".join(unicode(d) for d in data)

def isIPv4v6(prefix_addr, ip_type):
    if (ip_type == "ipv4"):
        return "." in prefix_addr
    elif (ip_type == "ipv6"):
        return ":" in prefix_addr
    elif( ip_type == "all"):
        return True
    # ip_type == "all"
    return False

def runSparkROAsIPPercentage(sc, year, ip_type): # only support v4
    def getNumIPs(list_of_ips, ip_type):
        s = []
        for (prefix_addr, prefix_len) in list_of_ips:
            if(ip_type == "ipv4"):
                prefix = IPv4Network("%s/%s" % (prefix_addr, prefix_len))
            else:
                prefix = IPv6Network("%s/%s" % (prefix_addr, prefix_len))
            s.append(prefix)
        
        return str(sum(map(lambda v: v.num_addresses, collapse_addresses(s))))


    
    tals = ["apnic", "lacnic", "ripencc", "arin", "afrinic"]

    nro_stats = "/hdfs-to-local-path/rpki/nrostats-withdate/nrostats-%s*-v4.csv" % year
    roa_prefix_asn = "/hdfs-to-local-path/rpki/ripe/ripe-new-objects/roa-prefix-asn/%s/*" % year
    savePath = "/hdfs-to-local-path/rpki/results/roas-covering-IPcnt-%s/%s" % (ip_type, year)
    localPath = "/home/tjchung/research/rpki/src/spark/results/roas-covering-IPcnt-%s/%s" % (ip_type, year)
    try: hdfs.rmr(savePath)
    except: pass

    a  = sc.textFile(nro_stats)\
            .map(lambda v: parseNRO(v, ip_type))\
            .filter(lambda v: v is not None)\
            .reduceByKey(lambda a, b: a+ b)\
            .map(lambda ((time, rir), num_ips):  ( (time, rir), str(num_ips)))
    

    k  = sc.textFile(roa_prefix_asn)\
        .filter(lambda line: "#" not in line)\
        .map(lambda line: line.rstrip().split("\t"))\
        .filter(lambda (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal): isIPv4v6(prefix_addr, ip_type) and tal != "localcert")\
        .map(lambda (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal): (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal))\
        .distinct()\
        .map(lambda (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal): ((time, tal), (prefix_addr, prefix_len)))\
        .groupByKey()\
        .map(lambda ( (time, tal), list_ip_prefixes): ((time, tal), getNumIPs(list_ip_prefixes, ip_type)))\
        .join(a)\
        .map(lambda ((time, tal), (num_rpki_ips, all_ips)): (time, tal, "%s\t%s" % (num_rpki_ips, all_ips)))

    
    sqlContext = SQLContext(sc)
    df = sqlContext.createDataFrame( k, ['date', 'tal', 'num_ips'] )

    grouped = df.rdd\
                .map(lambda row: (row.date, (row.tal, row.num_ips)))\
                .groupByKey()

    def make_row(kv):
        k, vs = kv # time: [(-1, cnt), (0, cnt), (1, cnt)] ...  
        tmp = dict(list(vs) + [("date", k)])
        return Row(**{k: tmp.get(k, "0\t0") for k in ["date"] + tals})
    
    reshaped = sqlContext.createDataFrame(grouped.map(make_row))

    k = reshaped.rdd\
            .map(lambda row: (row['date'], row["apnic"], row["lacnic"], row["ripencc"], row["arin"], row["afrinic"]))\
            .map(toTSV)
    
    k.saveAsTextFile(savePath)

    try: shutil.rmtree(localPath)
    except: pass

    try: os.makedirs(localPath)
    except: pass
    
    hdfs.get(savePath, localPath)
    mergeAndSort(localPath)

def runSparkROAsIPCnt(sc, ip_type):
    roa_prefix_asn = "/hdfs-to-local-path/rpki/ripe/ripe-new-objects/roa-prefix-asn/*"
    savePath = "/hdfs-to-local-path/rpki/results/roas-covering-IPcnt-%s" % ip_type
    localPath = "/home/tjchung/research/rpki/src/spark/results/roas-covering-IPcnt-%s" % ip_type

    def getNumIPs(list_of_ips, ip_type):
        s = []
        for (prefix_addr, prefix_len) in list_of_ips:
            if(ip_type == "ipv4"):
                prefix = IPv4Network("%s/%s" % (prefix_addr, prefix_len))
            else:
                prefix = IPv6Network("%s/%s" % (prefix_addr, prefix_len))
            s.append(prefix)
        
        return str(sum(map(lambda v: v.num_addresses, collapse_addresses(s))))


    try: hdfs.rmr(savePath)
    except: pass
    
    tals = ["apnic", "apnic-iana", "apnic-afrinic", "apnic-arin", "apnic-lacnic","apnic-ripe", "lacnic", "ripencc", "arin",  "afrinic", "localcert"]

    k  = sc.textFile(roa_prefix_asn)\
        .filter(lambda line: "#" not in line)\
        .map(lambda line: line.rstrip().split("\t"))\
        .filter(lambda (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal): isIPv4v6(prefix_addr, ip_type))\
        .distinct()\
        .map(lambda (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal): ((time, tal), (prefix_addr, prefix_len)))\
        .groupByKey()\
        .map(lambda ( (time, tal), list_ip_prefixes): (time, tal, getNumIPs(list_ip_prefixes, ip_type)))
    
    sqlContext = SQLContext(sc)
    df = sqlContext.createDataFrame( k, ['date', 'tal', 'num_ips'] )

    grouped = df.rdd\
                .map(lambda row: (row.date, (row.tal, row.num_ips)))\
                .groupByKey()

    def make_row(kv):
        k, vs = kv # time: [(-1, cnt), (0, cnt), (1, cnt)] ...  
        tmp = dict(list(vs) + [("date", k)])
        return Row(**{k: tmp.get(k, 0) for k in ["date"] + tals})
    
    reshaped = sqlContext.createDataFrame(grouped.map(make_row))

    k = reshaped.rdd\
            .map(lambda row: (row['date'], row["apnic"], row["apnic-iana"], row["apnic-afrinic"], row["apnic-arin"], row["apnic-lacnic"], row["apnic-ripe"], row["lacnic"], row["ripencc"], row["arin"], row["afrinic"], row["localcert"]))\
            .map(toTSV)
    
    k.saveAsTextFile(savePath)

    try: shutil.rmtree(localPath)
    except: pass

    try: os.makedirs(localPath)
    except: pass
    
    hdfs.get(savePath, localPath)
    mergeAndSort(localPath)

def runSparkGetTotalASNs(sc):
    readPath = "/hdfs-to-local-path/rpki/as-registry"
    a = sc.textFile(readPath)\
            .map(lambda v: v.split(","))\
            .map(lambda (date, tal, asn): ( (date, tal), asn))\
            .groupByKey()\
            .map(lambda ((date, tal), list_of_asn): ((date, tal),  len(list_of_asn)))
    
    return a

def runSparkNumASesInROAs(sc, ip_type):

    roa_prefix_asn = "/hdfs-to-local-path/rpki/ripe/ripe-new-objects/roa-prefix-asn/*"

    savePath = "/hdfs-to-local-path/rpki/results/roas-covering-AScnt-%s" % ip_type
    localPath = "/home/tjchung/research/rpki/src/spark/results/roas-covering-AScnt-%s" % ip_type

    try: hdfs.rmr(savePath)
    except: pass
    
    tals = ["apnic", "apnic-iana", "apnic-afrinic", "apnic-arin", "apnic-lacnic","apnic-ripe", "lacnic", "ripencc", "arin",  "afrinic", "localcert"]

    k  = sc.textFile(roa_prefix_asn)\
        .filter(lambda line: "#" not in line)\
        .map(lambda line: line.rstrip().split("\t"))\
        .filter(lambda (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal): isIPv4v6(prefix_addr, ip_type))\
        .distinct()\
        .map(lambda (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal): ((time, tal), asID))\
        .groupByKey()\
        .map(lambda ( (time, tal), num_ases): (time, tal, len(set(num_ases))))
    
    sqlContext = SQLContext(sc)
    df = sqlContext.createDataFrame( k, ['date', 'tal', 'num_ASes'] )

    grouped = df.rdd\
                .map(lambda row: (row.date, (row.tal, row.num_ASes)))\
                .groupByKey()

    def make_row(kv):
        k, vs = kv # time: [(-1, cnt), (0, cnt), (1, cnt)] ...  
        tmp = dict(list(vs) + [("date", k)])
        return Row(**{k: tmp.get(k, 0) for k in ["date"] + tals})
    
    reshaped = sqlContext.createDataFrame(grouped.map(make_row))

    k = reshaped.rdd\
            .map(lambda row: (row['date'], row["apnic"], row["apnic-iana"], row["apnic-afrinic"], row["apnic-arin"], row["apnic-lacnic"], row["apnic-ripe"], row["lacnic"], row["ripencc"], row["arin"], row["afrinic"], row["localcert"]))\
            .map(toTSV)
    
    k.saveAsTextFile(savePath)

    try: shutil.rmtree(localPath)
    except: pass

    try: os.makedirs(localPath)
    except: pass
    
    hdfs.get(savePath, localPath)
    mergeAndSort(localPath)

def runSparkPercentageASesInROAs(sc, ip_type):

    caida_as_org_days = ['20110420', '20110701', '20111003', '20120105', '20120401', '20120629', '20121002', '20130101', '20130401', '20130701', '20131001', '20140401', '20140701', '20141001', '20150101', '20150701', '20151001', '20160101', '20160401', '20160701', '20161001', '20170101', '20170401', '20170701', '20171001', '20180101', '20180401', '20180703', '20181001', '20190101']

    d = []
    for year in range(2011, 2020):
        d += createDates(year)


    caida_as_org_days = [ d[0] ] + caida_as_org_days + [ d[-1] ]
    as_org_days = dict.fromkeys(d, 0)

    min_date = datetime.strptime(d[0], "%Y%m%d")
    max_date = datetime.strptime(d[-1], "%Y%m%d")

    set_days_scope(caida_as_org_days, as_org_days, min_date, max_date)

    roa_prefix_asn = "/hdfs-to-local-path/rpki/ripe/ripe-new-objects/roa-prefix-asn/*"
    savePath = "/hdfs-to-local-path/rpki/results/roas-covering-AScnt-%s" % ip_type
    localPath = "/home/tjchung/research/rpki/src/spark/results/roas-covering-AScnt-%s" % ip_type

    try: hdfs.rmr(savePath)
    except: pass
    
    tals = ["apnic", "lacnic", "ripencc", "arin",  "afrinic"]

    a  = runSparkGetTotalASNs(sc) 

    k  = sc.textFile(roa_prefix_asn)\
        .filter(lambda line: "#" not in line)\
        .map(lambda line: line.rstrip().split("\t"))\
        .filter(lambda (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal):\
                    isIPv4v6(prefix_addr, ip_type) and \
                    tal != "localcert")\
        .map(lambda (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal): ((time, tal.split("-")[0]), asID))\
        .distinct()\
        .groupByKey()\
        .map(lambda ( (time, tal), num_ases): ( (as_org_days[time], tal), (time, len(set(num_ases)))))\
        .join(a)\
        .map(lambda ((time, tal), ((real_time, num_activated_asns), all_asns)): (real_time, tal, "%s\t%s" % (num_activated_asns, all_asns)))
    
    sqlContext = SQLContext(sc)
    df = sqlContext.createDataFrame( k, ['date', 'tal', 'num_ASes'] )

    grouped = df.rdd\
                .map(lambda row: (row.date, (row.tal, row.num_ASes)))\
                .groupByKey()

    def make_row(kv):
        k, vs = kv 
        tmp = dict(list(vs) + [("date", k)])
        return Row(**{k: tmp.get(k, "0\t0") for k in ["date"] + tals})
    
    reshaped = sqlContext.createDataFrame(grouped.map(make_row))

    k = reshaped.rdd\
            .map(lambda row: (row['date'], row["apnic"], row["lacnic"], row["ripencc"], row["arin"], row["afrinic"]))\
            .map(toTSV)
    
    k.saveAsTextFile(savePath)

    try: shutil.rmtree(localPath)
    except: pass

    try: os.makedirs(localPath)
    except: pass
    
    hdfs.get(savePath, localPath)
    mergeAndSort(localPath, label="\t".join(["#apnic", "lacnic", "ripencc", "arin", "afrinic"]))

def runSparkNumROAs(sc):
    def parse(line):
        time_tal, filename, _, skid, akid, ee, roa = line.rstrip().split(",")
        time = time_tal[:8]
        tal  = time_tal[9:-4]
        #time, tal = time_tal.replace(".txt", "").split("-")

        return (time, tal, filename)

    roas = "/hdfs-to-local-path/rpki/ripe/ripe-new-objects/roas/*"
    savePath = "/hdfs-to-local-path/rpki/results/num-roas"
    localPath = "/home/tjchung/research/rpki/src/spark/results/num-roas"

    try: hdfs.rmr(savePath)
    except: pass
    
    tals = ["apnic", "apnic-iana", "apnic-afrinic", "apnic-arin", "apnic-lacnic","apnic-ripe", "lacnic", "ripencc", "arin",  "afrinic", "localcert"]


    k  = sc.textFile(roas)\
        .map(parse)\
        .distinct()\
        .map(lambda (time, tal, filename): ((time, tal), 1))\
        .reduceByKey(lambda a, b : a +b )\
        .map(lambda ( (time, tal), num_roas): (time, tal, num_roas))
    
    sqlContext = SQLContext(sc)
    df = sqlContext.createDataFrame( k, ['date', 'tal', 'num_roas'] )

    grouped = df.rdd\
                .map(lambda row: (row.date, (row.tal, row.num_roas)))\
                .groupByKey()

    def make_row(kv):
        k, vs = kv # time: [(-1, cnt), (0, cnt), (1, cnt)] ...  
        tmp = dict(list(vs) + [("date", k)])
        return Row(**{k: tmp.get(k, 0) for k in ["date"] + tals})
    
    reshaped = sqlContext.createDataFrame(grouped.map(make_row))

    k = reshaped.rdd\
            .map(lambda row: (row['date'], row["apnic"], row["apnic-iana"], row["apnic-afrinic"], row["apnic-arin"], row["apnic-lacnic"], row["apnic-ripe"], row["lacnic"], row["ripencc"], row["arin"], row["afrinic"], row["localcert"]))\
            .map(toTSV)
    
    k.saveAsTextFile(savePath)

    try: shutil.rmtree(localPath)
    except: pass

    try: os.makedirs(localPath)
    except: pass
    
    hdfs.get(savePath, localPath)
    mergeAndSort(localPath)

def runSparkNumVRP(sc, ip_type):
    roa_prefix_asn = "/hdfs-to-local-path/rpki/ripe/ripe-new-objects/roa-prefix-asn/*"
    localPath = "/home/tjchung/research/rpki/src/spark/results/vrp-growth/"
    savePath = "/hdfs-to-local-path/rpki/results/vrp-growth"

    try: hdfs.rmr(savePath)
    except: pass
    k  = sc.textFile(roa_prefix_asn)\
        .filter(lambda line: "#" not in line)\
        .map(lambda line: line.rstrip().split("\t"))\
        .filter(lambda (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal): isIPv4v6(prefix_addr, ip_type) )\
        .map(lambda (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal): (time, prefix_addr, prefix_len, tal))\
        .distinct()\
        .map(lambda (time, prefix_addr, prefix_len, tal): ((time, tal), 1))\
        .reduceByKey(lambda a, b: a+ b)\
        .map(lambda ((time, tal), cnt): (time, tal, cnt))

    sqlContext = SQLContext(sc)
    df = sqlContext.createDataFrame( k, ['date', 'tal', 'num_vrps'] )

    grouped = df.rdd\
                .map(lambda row: (row.date, (row.tal, row.num_vrps)))\
                .groupByKey()

    tals = ["apnic", "apnic-iana", "apnic-afrinic", "apnic-arin", "apnic-lacnic","apnic-ripe", "lacnic", "ripencc", "arin",  "afrinic", "localcert"]

    def make_row(kv):
        k, vs = kv # time: [(-1, cnt), (0, cnt), (1, cnt)] ...  
        tmp = dict(list(vs) + [("date", k)])
        return Row(**{k: tmp.get(k, 0) for k in ["date"] + tals})
    
    reshaped = sqlContext.createDataFrame(grouped.map(make_row))

    k = reshaped.rdd\
            .map(lambda row: (row['date'], row["apnic"], row["apnic-iana"], row["apnic-afrinic"], row["apnic-arin"], row["apnic-lacnic"], row["apnic-ripe"], row["lacnic"], row["ripencc"], row["arin"], row["afrinic"], row["localcert"]))\
            .map(toTSV)
    
    k.saveAsTextFile(savePath)

    try: shutil.rmtree(localPath)
    except: pass

    try: os.makedirs(localPath)
    except: pass
    
    hdfs.get(savePath, localPath)
    mergeAndSort(localPath)


def runSparkNumPrefixWithMaxlen(sc, ip_type = "ipv4"):

    roa_prefix_asn = "/hdfs-to-local-path/rpki/ripe/ripe-new-objects/roa-prefix-asn/*"
    localPath = "/home/tjchung/research/rpki/src/spark/results/roa-prefix-with-maxlength"
    savePath = "/hdfs-to-local-path/rpki/results/roa-prefix-with-maxlength"

    try: hdfs.rmr(savePath)
    except: pass
    k  = sc.textFile(roa_prefix_asn)\
        .filter(lambda line: "#" not in line)\
        .map(lambda line: line.rstrip().split("\t"))\
        .filter(lambda (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal): isIPv4v6(prefix_addr, ip_type) )\
        .map(lambda (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal): (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal))\
        .distinct()\
        .map(lambda (time, prefix_addr, prefix_len, maxlen, asID, num_ips, cc, tal): ((time,  str(int( (prefix_len != maxlen) and maxlen != "None" ))), 1))\
        .reduceByKey(lambda a, b: a+ b)\
        .map(lambda ((time, hasMaxlen), cnt): (time, hasMaxlen, cnt))

    sqlContext = SQLContext(sc)
    df = sqlContext.createDataFrame( k, ['date', 'hasMaxlen', 'cnt'] )

    grouped = df.rdd\
                .map(lambda row: (row.date, (row.hasMaxlen, row.cnt)))\
                .groupByKey()

    def make_row(kv):
        k, vs = kv 
        tmp = dict(list(vs) + [("date", k)])
        return Row(**{k: tmp.get(k, 0) for k in ["date", "0", "1"] }) # 1 means has a maxlen
    
    reshaped = sqlContext.createDataFrame(grouped.map(make_row))

    k = reshaped.rdd\
            .map(lambda row: (row['date'], row['0'], row['1']))\
            .map(toTSV)
    
    
    k.saveAsTextFile(savePath)

    try: shutil.rmtree(localPath)
    except: pass

    try: os.makedirs(localPath)
    except: pass
    
    hdfs.get(savePath, localPath)
    mergeAndSort(localPath)


if __name__ == "__main__":
    conf = SparkConf()\
            .setAppName("spark-rpki-object-validation")

    sc = SparkContext(conf=conf)
    sc.setLogLevel("WARN")
        
    runSparkNumPrefixWithMaxlen(sc)

    runSparkROAsIPCnt(sc, "ipv4")
    runSparkROAsIPCnt(sc, "ipv6")
    runSparkNumASesInROAs(sc, "ipv4")
    runSparkNumASesInROAs(sc, "ipv6")
    runSparkPercentageASesInROAs(sc, "ipv4")
    runSparkPercentageASesInROAs(sc, "ipv6")

    sc.stop()

