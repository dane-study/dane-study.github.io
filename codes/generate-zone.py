#!/usr/bin/env python3

# Copyright 2020 Aniketh Girish 

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import yaml
import jinja2
import time
import datetime
import argparse
import ipaddress

TEMPLATE = """\
$ORIGIN {{ zone.origin }}
$TTL {{ zone.ttl }}
@             IN  SOA  {{ zone.soa.ns }} {{ zone.soa.user }} (
              {{ zone.soa.serial }} ; serial number of this zone file
              1d         ; slave refresh (1 day)
              2h         ; slave retry time in case of a problem (2 hours)
              4w         ; slave expiration time (4 weeks)
              1h         ; maximum caching time in case of failed lookups (1 hour)
              )

{% for record in zone.records -%}
{{ record }}
{% endfor %}
"""

def parse_args():
    "parse application arguments"
    parser = argparse.ArgumentParser(
            description = 'bind zone file generator.',
            epilog = __doc__,
            formatter_class = argparse.RawTextHelpFormatter)
    group = parser.add_mutually_exclusive_group(required = True)
    group.add_argument('filename', nargs = '?',
                       help = 'yaml file containing zone info')

    return parser.parse_args()

class Records(object):
    "container class for record formatting methods."

    mask = 0

    @staticmethod
    def fields_ns(record):
        "format an NS record"
        return ['', record['type'], record['value']]

    @staticmethod
    def fields_mx(record):
        "format an MX record"
        return ['', record['type'],
                str(record['priority']) + '  ' + record['value']]

    @staticmethod
    def fields_a(record):
        "format an A record"
        return [record[x] for x in ['host', 'type', 'value']]

    @staticmethod
    def fields_aaaa(record):
        "Format an AAAA record. Same as an A record."
        return Records.fields_a(record)

    @staticmethod
    def fields_cname(record):
        "Format a CNAME record. Same as an A record."
        return Records.fields_a(record)

    @staticmethod
    def fields_ptr(record):
        "Format a PTR record."
        return [reverse_addr_host(record['value'], Records.mask),
                record['type'], record['host']]

def reverse_addr_mask(cidr):
    "Return the mask of cidr. IPv6 is nibbles, IPv4 is octets."
    if ':' in cidr:
        return 32 - int(cidr.split('/')[1]) // 4
    else:
        return 4 - int(cidr.split('/')[1]) // 8

def reverse_addr_origin(addr, mask):
    "Return addr as a reverse origin domain."
    if ':' in addr:
        addr = ipaddress.IPv6Address(addr).exploded.replace(':', '')[::-1]
        return '.'.join(addr[mask:]) + '.ip6.arpa.'
    else:
        addr = addr.split('.')[::-1]
        return '.'.join(addr[mask:]) + '.in-addr.arpa.'

def reverse_addr_host(addr, mask):
    "Return addr as a reverse host record."
    if ':' in addr:
        addr = ipaddress.IPv6Address(addr).exploded.replace(':', '')[::-1]
        return '.'.join(addr[:mask])
    else:
        addr = addr.split('.')[::-1]
        return '.'.join(addr[:mask])

def format_record(record):
    "Format a DNS record by calling the matching fields_* function."
    fmt_str = '%-16s IN  %-6s %s'
    try:
        method = getattr(Records, 'fields_' + record['type'].lower())
        return fmt_str % tuple(method(record))
    except KeyError:
        return '; error in record: ' + str(record)


def main():
    "Main application function."
    args = parse_args()
    template = jinja2.Template(TEMPLATE)

    input_file = open(args.filename)
    zone = yaml.safe_load(input_file)

    zone['soa']['serial'] = str(int(time.time()))

    if 'type' in zone and zone['type'] == 'reverse':
        Records.mask = reverse_addr_mask(zone['origin'])
        addr = zone['origin'].split('/')[0]
        zone['origin'] = reverse_addr_origin(addr, Records.mask)

    zone['records'] = [format_record(x) for x in zone['records']]
    errors = [x.startswith(';') for x in zone['records']]
    exit_code = 0
    if True in errors:
        exit_code = 1

    print(template.render(zone = zone))

    sys.exit(exit_code)

if __name__ == '__main__':
    main()
