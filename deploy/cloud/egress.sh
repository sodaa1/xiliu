#!/bin/sh
set -eu
# Runs only in the dedicated network guard; the application has no capabilities.
iptables -P OUTPUT DROP
iptables -F OUTPUT
iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
# Docker rewrites the DNS stub destination port before the filter table.
iptables -A OUTPUT -d 127.0.0.11 -p udp -m conntrack --ctorigdstport 53 -j ACCEPT
iptables -A OUTPUT -d 127.0.0.11 -p tcp -m conntrack --ctorigdstport 53 -j ACCEPT
# Health checks only; user-configured HTTP clients still refuse all loopback URLs.
iptables -A OUTPUT -d 127.0.0.1 -p tcp --dport 8765 -j ACCEPT
for range in 0.0.0.0/8 10.0.0.0/8 100.64.0.0/10 127.0.0.0/8 \
  169.254.0.0/16 172.16.0.0/12 192.0.0.0/24 192.0.2.0/24 192.168.0.0/16 \
  192.88.99.0/24 198.18.0.0/15 198.51.100.0/24 203.0.113.0/24 \
  168.63.129.16/32 224.0.0.0/4 240.0.0.0/4; do
  iptables -A OUTPUT -d "$range" -j REJECT
done
iptables -A OUTPUT -p tcp -m multiport --dports 80,443 -j ACCEPT
# Fail closed for IPv6; API hosts with A and AAAA records prefer validated IPv4.
if [ -f /proc/net/if_inet6 ]; then
  ip6tables -P OUTPUT DROP
  ip6tables -F OUTPUT
  ip6tables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
fi
touch /run/egress-ready
exec sleep infinity
