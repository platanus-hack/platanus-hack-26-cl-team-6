# Shared notes
[agent 1] Starting: reviewing logs for initial malicious document delivery (process/proxy/dns/auth).
[agent 0] Chain on WS-903 (luis.munoz): 08:51 GET galmon.com/invoice_12052.docm allowed -> 08:52 winword opens invoice_12052.docm -> powershell -enc (hidden). Earlier datgal.co docm was blocked. Answer: galmon.com
[agent 1] FINAL: WS-903 luis.munoz downloaded invoice_12052.docm from galmon.com (DNS 08:50:58, proxy GET 08:51 allowed); winword opened it 08:52; encoded powershell 08:52:20; C2 bexfirsky.com. Decoy datgal.co (WS-589, blocked) ignored. Answer: galmon.com
