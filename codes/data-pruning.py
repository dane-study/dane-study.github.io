""" This script obtains BGP announcements that are unique to (timestamp,
    announcement, IP and AS of a vantage point, announced IP prefix, AS_PATH.
"""

import os
import gzip
from multiprocessing import *
import sys

def parseAkamai(f, date, w):
    try: 
        if("gz" in f): f = gzip.open(f, 'rb') 
        else: f = open(f)
    except:
        return

    try:
        for line in f:
            c = line.split("|")
            try:
                if(c[2] != "A"): continue
                rp = c[7]

                #if(rp == "EGP"):
                w.write( "|".join( [c[0]] + [date] + c[2:]  ))
            except:
                pass
    except:
        pass

read_routeview     = None # Path to BGP dataset 
write_routeview    = None # Temporary write path
cp_path            = None # Final path to save minimized BGP dataset

finish = []

def parseAkamaiDay( (year, month, day) ):
    global finish
    date = year + month + day
    fname = os.path.join(write_routeview, "daily-data")
    try   : os.makedirs(fname)
    except: pass

    fname = os.path.join(fname, date)
    w = open(fname, "w")
    
    dirs =  os.listdir(os.path.join(read_routeview, year, month, day, "BGP"))
    for f in dirs:
        print "%s [%s/%s] processing, finished: %s" % (date, dirs.index(f), len(dirs), ",".join(finish))
        path  = os.path.join(read_routeview, year, month, day, "BGP", f)
        parseAkamai(path, date, w)
    w.close()

    """
    An example of BGP announcements:

    BGP4MP|1534560105|A|203.192.178.254|10026|117.78.24.0/21|10026 4538 4538 4538 133111 55990|IGP|203.192.178.254|0|0|4538:10 4538:4538 10026:4200 10026:4310 10026:32344 10026:40142|NAG||
    """
    cmd = "sort -t'|' -k2,2 -k3,3 -k4,4 %s > /tmp/%s"% (fname, date)
    print cmd
    os.system(cmd)

    cmd = " uniq /tmp/%s  > %s " % (date, fname)
    print cmd
    os.system(cmd)

    cmd = " rm /tmp/%s " % (date)
    print cmd

    os.system(cmd)
    finish.append(date)


def pig( (year, month, day) ):
    path = os.path.join(read_routeview, year, month, day, "BGP")

    date = year + month + day

    unsorted_dst = "/scratch/tmp/tijay/routeview-%s" % date
    unsorted_dst_dir = "/scratch/tmp/tijay/routeview-%s-directory" % date
    
    cmd = """cp -r %s %s""" % (path, unsorted_dst_dir)
    print cmd
    os.system(cmd)

    cmd  = """unpigz -p 20 -c %s/*.gz | grep "|A|" >  %s 
    """ % (unsorted_dst_dir, unsorted_dst)

    print cmd
    os.system(cmd)

    sort = """sort -t '|' -k5,5 -k6,6 -k7,7 -u %s > %s""" % (unsorted_dst, os.path.join(cp_path, date))
    print sort
    os.system(sort)

    delete = """rm %s""" % unsorted_dst
    print delete
    os.system(delete)

    delete = """rm -rf %s""" % unsorted_dst_dir
    print delete
    os.system(delete)

if __name__ == "__main__":
    dates  = sys.argv[1] 
    dates = dates.split(",")
    for date in dates:
        year  = date[:4] 
        month = date[4:6]
        jobList = []
        for y in os.listdir(read_routeview):
            if (y != year): continue
            for m in os.listdir(os.path.join(read_routeview, year)):
                if( m != month): continue

                for day in os.listdir(os.path.join(read_routeview, year, month)):
                    jobList.append((y, m, day))
        
        print jobList
        p = Pool(3)
        p.map(pig, jobList)

