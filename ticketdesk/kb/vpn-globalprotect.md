# VPN (GlobalProtect) will not connect, and first time setup

Category: vpn
Owner: Service Desk (L1). Time: 10 minutes.

Symptoms: "could not connect to gateway", spinning forever, works in the office but not at home, new laptop has no VPN.

1. First time setup: install GlobalProtect from the company portal (Software Center on Windows, Self Service on Mac). Portal address: vpn.northline.com. Sign in with the normal account and MFA.
2. Will not connect: check the requester has internet without VPN (open any website). If not, it is the home network, not the VPN.
3. Restart GlobalProtect: right click the tray icon > Disable, then Enable. Then reboot the laptop once.
4. Check the portal address is exactly vpn.northline.com (no typo, no old address).
5. Home router problem: ask them to try a phone hotspot. If the hotspot works, their router or ISP blocks the VPN; suggest restarting the router.
6. Check the account is not locked (see password-reset.md), a locked account looks like a VPN failure.

Escalate if: several users from the same location fail at the same time (network, L3), or the gateway is unreachable from the office too (L2 network team).
