""" This scripts will
    (1) identify a pair of the attacker and victim AS,
    (2) produces a CDF that the number of vicitm ASes that a single attacker announces a wrong BGP announcement, 
    (3) produces a CDF that the number of attacker ASes that announce IP prefixes of an actual owner AS.

"""
import json
from generate_cdf import *
import operator
import sys
import os

BGP_PFXV_STATE_HIJACKING = 2 # Covered ROA found, non-identical AS, matched

def getPairsOfAttack(dataset):
    attacker_cnt_byAS = {}
    victim_cnt_byAS = {}
    pair_cnt_byAS = {}
    pair_cnt_byAS_date = {}

    path = "spark/results/rpki-unique-prefix-hijack-None/ipv4" 

    for line in open(os.path.join(path, "%s.tsv" % dataset)):
        date, j = line.rstrip().split("\t")
        j = json.loads(j)
        attacker_AS = (j['origin_as'], j['origin_isp'], j['origin_country'])
         

        hijack = None
        sub_hijack = None
        for vrp in j['vrps']:
            victim_AS = (vrp['vrp_asID'], vrp['vrp_isp'], vrp['vrp_country'])
            if(vrp['verify_state'] == BGP_PFXV_STATE_HIJACKING):
                hijack = victim_AS
            else: # BGP_PFXV_STATE_SUBHIJACK
                sub_hijack = victim_AS
        
        if(hijack is not None): victim_AS = hijack
        else: victim_AS = sub_hijack
        
        if attacker_AS not in attacker_cnt_byAS: attacker_cnt_byAS[attacker_AS] = set()

        if victim_AS not in victim_cnt_byAS: victim_cnt_byAS[victim_AS] = set()
    
        pair = (attacker_AS, victim_AS)
        if pair not in pair_cnt_byAS_date: pair_cnt_byAS_date[pair] = set()

        attacker_cnt_byAS[attacker_AS].add(victim_AS)
        victim_cnt_byAS[victim_AS].add(attacker_AS)
        pair_cnt_byAS[pair] = pair_cnt_byAS.get(pair, 0) + 1

        pair_cnt_byAS_date[pair].add(date)

    
    w_path = "spark/results/rpki-unique-prefix-hijack-ipv4-None-pairs/"

    attacker_cnt_byAS_list = map(lambda v: len(attacker_cnt_byAS[v]), attacker_cnt_byAS)
    victim_cnt_byAS_list = map(lambda v: len(victim_cnt_byAS[v]), victim_cnt_byAS)
    pair_cnt_byAS_list = pair_cnt_byAS.values()
    
    generateCDFFromList(attacker_cnt_byAS_list, os.path.join(w_path, "%s-attacker-cnt-byAS.txt" % dataset))
    generateCDFFromList(victim_cnt_byAS_list, os.path.join(w_path, "%s-victim-cnt-byAS.txt" % dataset))
    generateCDFFromList(pair_cnt_byAS_list, os.path.join(w_path, "%s-pair-cnt-byAS.txt" % dataset))
    
    w = open(os.path.join(w_path, "%s-attacker-cnt-byAS-map.txt" % dataset), "w")
    for attacker in sorted(attacker_cnt_byAS, key=lambda v: len(attacker_cnt_byAS[v]), reverse=True):
        w.write("%s\t%s\n" % (attacker, len(attacker_cnt_byAS[attacker])))
    w.close()

    w = open(os.path.join(w_path, "%s-victim-cnt-byAS-map.txt" % dataset), "w")
    for victim in sorted(victim_cnt_byAS, key=lambda v: len(victim_cnt_byAS[v]), reverse=True):
        w.write("%s\t%s\n" % (victim, len(victim_cnt_byAS[victim])))
    w.close()
    
    w = open(os.path.join(w_path, "%s-pair-cnt-byAS-map.txt" % dataset), "w")
    for pair, value in sorted(pair_cnt_byAS.items(), key=operator.itemgetter(1), reverse=True):
        w.write("%s\t%s\t%s\n" % (pair, value, len(pair_cnt_byAS_date[pair])))
    w.close()

if __name__ == "__main__":
    for dataset in ["routeviews", "ripe-ris", "akamai"]:
        getPairsOfAttack(dataset)
