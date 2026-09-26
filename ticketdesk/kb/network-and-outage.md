# Network problems for a floor or office, and outages

Category: network outage
Owner: Network team (L3 incident). The Service Desk opens the incident and keeps people informed. Time: immediate.

1. Confirm scope in two minutes: how many people, which office, which floor, wired or Wi-Fi, since when. One person is not an outage (check their laptop first).
2. Declare the incident: open the incident ticket, post in the #it-status Teams channel with what is affected and the next update time (30 minutes).
3. Wi-Fi for a whole floor: network team checks the floor access points and the controller; a power cycle of the floor switch is a last resort and needs the network team.
4. One office cannot reach a server in the other office: check the site link (ISP status page and the link monitor). Failover to the backup link is a network team action.
5. Email or portal down for everyone: check the vendor status page (status.office.com, status.freshservice.com) before touching anything; most whole company outages are the vendor.
6. Update every 30 minutes until resolved, then post the all clear and write the short postmortem on the ticket.

Escalate if: always L3. Anything affecting a whole floor, an office, or all users.
