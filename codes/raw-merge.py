#!/usr/bin/python3
import sys
import datetime
import os
from os import listdir
import json

inputPath = "" # ex) /home/ubuntu/raw_dataset/virginia/
outputPath = "" # ex) /home/ubuntu/aggregated/virginia/


def getTLSA(filename, time, dnMap):
    f = open(filename, "r")

    while True:
        line = f.readline()
        if not line: break
        line = line[:-1]
        line = line.split(", ")

        dn = line[0].split(".")
        port = dn[0].split("_")[1]
        dn = ".".join(dn[2:])

        name = dn + ":" + port

        dnMap[name] = {"domain":dn, "port":port, "time":time, "city":line[1]}
        
        if not (line[2] == "NoData"):
            dnMap[name]["tlsa"] = {}
            dnMap[name]["tlsa"]["dnssec"] = line[2]
            if line[2] == "Bogus":
                dnMap[name]["tlsa"]["why_bogus"] = line[3]
                dnMap[name]["tlsa"]["record_raw"] = line[4]
            else:
                dnMap[name]["tlsa"]["record_raw"] = line[3]

    return dnMap

def removeFake(certs):
    result = []
    for cert in certs:
        if cert == "" or cert == " ":
            continue
        else:
            result.append(cert)
    return result

def getSTLS(filename, dnMap):
    f = open(filename, "r")

    while True:
        line = f.readline()
        if not line: break
        line = line[:-1]
        line = line.split(", ")

        name = line[0] + ":" + line[1]

        if not (name in dnMap):
            print(line)

        dnMap[name]["starttls"] = {}
        if line[3] == "Success":
            certs = removeFake(line[5:])
            dnMap[name]["starttls"]["certs"] = certs
        else:
            dnMap[name]["starttls"]["why_fail"] = line[4]
    return dnMap

def writeDnMap(dnMap, fOut):
    keys = dnMap.keys()

    for key in keys:
        if not 'starttls' in dnMap[key]:
            dnMap[key]["starttls"] = {"why_fail":"NoData"}
        
        json.dump(dnMap[key], fOut)
        fOut.write("\n")
        

def aggregateAux(dates):

    for date in dates:
        print(date)
        prefix = inputPath
        tlsaHours = listdir(os.path.join(prefix, "tlsa", date))
        stlsHours = listdir(os.path.join(prefix, "starttls", date))

        hours = list(set(tlsaHours) & set(stlsHours))

        for hour in hours:
            fOut = open(os.path.join(outputPath, date + "_" + hour + ".txt"), "w")
            dnMap = {}
            files = listdir(os.path.join(prefix, "tlsa", date, hour))
            for filename in files:
                dnMap = getTLSA(os.path.join(prefix, "tlsa", date, hour, filename), "20"+date+" " + hour, dnMap)
                
            files = listdir(os.path.join(prefix, "starttls", date, hour))
            for filename in files:
                dnMap = getSTLS(os.path.join(prefix, "starttls", date, hour, filename), dnMap)
            
            writeDnMap(dnMap, fOut)
            fOut.close()



if __name__ == "__main__":
    start = sys.argv[1] # first date
    end = sys.argv[2] # last date
    # ex) python3 raw-merge.py 190711 191031 virginia

    start = datetime.datetime.strptime(start, "%y%m%d")
    end = datetime.datetime.strptime(end, "%y%m%d")

    dates = [(start+datetime.timedelta(days=x)).strftime("%y%m%d") for x in range(0, (end-start).days+1)]

    aggregateAux(dates)
