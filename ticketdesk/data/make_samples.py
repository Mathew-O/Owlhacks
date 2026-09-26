"""Writes data/sample_tickets.json: 30 tickets with the level a human would give (for eval.py)."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

T = [
    # (subject, body, requester, category, level)
    ("Locked out of my account", "I typed my password wrong a few times this morning and now it says my account is locked. I have a client call at 10.", "maria.lopez@northline.com", "password", "L1"),
    ("Password expired, can't log in", "Got the password expired message on my laptop and cannot log in at all now. Working from the Philadelphia office today.", "james.carter@northline.com", "password", "L1"),
    ("Reset password please", "Forgot my password after vacation. Can you reset it?", "priya.nair@northline.com", "password", "L1"),
    ("New phone, MFA codes gone", "I got a new iPhone yesterday and the Authenticator app is empty. Cannot get past the verification code screen.", "tom.becker@northline.com", "mfa", "L1"),
    ("Authenticator keeps saying code invalid", "Every code from the authenticator app says invalid. Time on the phone looks right.", "ana.silva@northline.com", "mfa", "L1"),
    ("VPN will not connect from home", "GlobalProtect spins and then says could not connect to gateway. Home Wi-Fi works fine for everything else.", "kevin.wu@northline.com", "vpn", "L1"),
    ("How do I set up VPN on the new laptop", "Just got the new laptop from the office. Where do I get GlobalProtect and what portal address do I use?", "sara.kim@northline.com", "vpn", "L1"),
    ("Printer on 4th floor NY not printing", "The Canon on the 4th floor in New York shows my job as sent but nothing comes out. Other people can print.", "derek.jones@northline.com", "printer", "L1"),
    ("Scan to email not working", "Scanning from the Philadelphia lobby printer, the email never arrives. Tried twice.", "linda.park@northline.com", "printer", "L1"),
    ("Outlook stuck on updating inbox", "Outlook has said updating inbox since yesterday. Webmail shows new mail. Restarted twice.", "omar.hassan@northline.com", "email", "L1"),
    ("Not receiving emails from a vendor", "Emails from billing@acmecorp.com never arrive. They say they sent three. Nothing in junk.", "grace.chen@northline.com", "email", "L1"),
    ("Shared mailbox missing in Outlook", "I was told I have access to the sales shared mailbox but it does not show up in Outlook.", "nick.rossi@northline.com", "email", "L1"),
    ("How do I share my calendar with my manager", "Is there a way to let my manager see my calendar details, not just free or busy?", "emily.wright@northline.com", "how_to", "L1"),
    ("How to record a Teams meeting", "Can you show me where the record button is in Teams, and where the recording ends up?", "raj.patel@northline.com", "how_to", "L1"),
    ("Access to the finance shared drive", "Please add me to the finance shared drive. My manager Dana approved it in our 1:1.", "lucas.brown@northline.com", "access_request", "L2"),
    ("New hire starts Monday", "Jordan Lee starts Monday in marketing, New York office. Needs laptop, email, Teams, and access to the marketing drive.", "hannah.moore@northline.com", "access_request", "L2"),
    ("Need Visio installed", "I need Visio for network diagrams for the audit. Can it be installed this week?", "victor.ramos@northline.com", "software", "L2"),
    ("Adobe Acrobat licence", "Acrobat says my licence is not valid anymore. I sign contracts daily so this is blocking.", "sophie.turner@northline.com", "software", "L2"),
    ("Laptop will not turn on", "My laptop will not turn on at all. No light, tried the charger from a colleague. Philadelphia office.", "ben.foster@northline.com", "hardware", "L2"),
    ("Docking station only shows one monitor", "Since the update my dock only drives one of my two monitors. Swapped cables, same thing.", "ivy.zhang@northline.com", "hardware", "L2"),
    ("Reporting server disk is full", "The reporting server (RPT-01) says disk full and the nightly job failed. Finance needs the report by noon.", "mark.evans@northline.com", "server", "L2"),
    ("Backup job failed last night", "The backup job for the file server shows failed with error 0x8007 in the console. Second night in a row.", "olivia.scott@northline.com", "server", "L2"),
    ("Suspicious email asking for gift cards", "I got an email that looks like it is from our CEO asking me to buy gift cards. I did not click anything. Is this phishing?", "chloe.adams@northline.com", "security", "L2"),
    ("I clicked a link in a strange email", "I clicked a link in an email about a shared document and it asked me to log in. I typed my password before I realised. What do I do?", "daniel.green@northline.com", "security", "L2"),
    ("Firewall rule for ping and traceroute", "We need to allow ping and traceroute from the New York office to the monitoring server in Philadelphia for the new NOC tool.", "alex.murphy@northline.com", "firewall_change", "L2"),
    ("Open port 8443 for vendor appliance", "Vendor needs inbound 8443 to the new appliance in the PA data closet from their support range.", "nina.petrov@northline.com", "firewall_change", "L2"),
    ("Wi-Fi down on the whole 3rd floor", "Nobody on the 3rd floor in New York can get on Wi-Fi since about 9am. Wired desks work.", "paul.walker@northline.com", "network", "L3"),
    ("Philadelphia office cannot reach the file server", "Everyone in Philadelphia gets a timeout opening the file server. New York is fine. Started 20 minutes ago.", "rachel.diaz@northline.com", "network", "L3"),
    ("Email is down for everyone", "Nobody can send or receive email, the whole office is affected. Outlook and webmail both fail.", "steve.hall@northline.com", "outage", "L3"),
    ("Freshservice portal down for all users", "The support portal returns a 503 for all users in both offices. We cannot log tickets.", "julia.king@northline.com", "outage", "L3"),
]

rows = []
base = dt.datetime.now().replace(second=0, microsecond=0) - dt.timedelta(hours=len(T))
for i, (subject, body, who, cat, lvl) in enumerate(T):
    rows.append({"id": f"INC-{1001 + i}", "subject": subject, "body": body, "requester": who,
                 "created": (base + dt.timedelta(hours=i)).isoformat(timespec="minutes"), "status": "new", "stage": "new",
                 "expected": {"category": cat, "level": lvl},
                 "history": [{"at": (base + dt.timedelta(hours=i)).isoformat(timespec="minutes"), "event": "created"}]})

out = Path(__file__).with_name("sample_tickets.json")
out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"wrote {len(rows)} tickets to {out}")
