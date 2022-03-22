# flow_broker
ulogd to uds flow broker

Install these on your cirrus.
![Screen Shot 2022-03-22 at 4 40 55 PM](https://user-images.githubusercontent.com/8184748/159594564-18a09913-c692-4f3c-81fc-3b99821c0ca8.png)


![Screen Shot 2022-03-22 at 4 42 15 PM](https://user-images.githubusercontent.com/8184748/159594654-60c89028-ce54-4ff6-a564-b422df2fb386.png)


IPtables rules

iptables -t raw -I PREROUTING 1 -i 3g-wwan -j NFLOG --nflog-group 2 --nflog-prefix ip2 --nflog-size 128

iptables -t raw -I PREROUTING 2 -i eth1 -j NFLOG --nflog-group 2 --nflog-prefix ip2 --nflog-size 128

iptables -t raw -A OUTPUT -o 3g-wwan -j NFLOG --nflog-group 2 --nflog-prefix ip2 --nflog-size 128

iptables -t raw -A OUTPUT -o eth1 -j NFLOG --nflog-group 2 --nflog-prefix ip2 --nflog-size 128


Add those to the custom rules and restart the firewall.
