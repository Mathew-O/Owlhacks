# Firewall change requests

Category: firewall_change
Owner: Network team (L2) through the change process. Time: about one week (review meeting, two day comment window, approval meeting).

1. Collect the five facts: source (office or subnet), destination (server and IP), ports and protocol (for example ICMP echo for ping, UDP 33434 to 33534 for traceroute, TCP 8443), direction, and the business reason.
2. Check whether the rule already exists (network team can read the current config). If it does, reply with that and close.
3. Write the change on the firewall change template (OneNote) with the five facts, the impact, and the backout plan.
4. Put it on the weekly review meeting agenda. After review, the change goes into the change record with a two day comment window.
5. Approval meeting decides. The network team pushes the change and confirms with the requester.

Escalate if: always L2 (change process). Rules that open inbound access from the internet need Security sign off too.
