# Outlook and mailbox problems

Category: email
Owner: Service Desk (L1). Time: 15 minutes.

Symptoms: Outlook stuck on "updating inbox", mail from one sender never arrives, shared mailbox missing.

1. Compare with webmail (outlook.office.com). If webmail is fine, the problem is the Outlook app on the laptop, not the mailbox.
2. Stuck on updating inbox: close Outlook, open it with Work Offline off, and if it still hangs, create a new Outlook profile (Control Panel > Mail > Show Profiles > Add).
3. Mail from one sender never arrives: check the junk folder and the quarantine portal (security.microsoft.com > Quarantine). Release it and add the sender to safe senders.
4. Shared mailbox missing: confirm the requester was added to the shared mailbox in the admin console. It appears in Outlook up to one hour later. Restart Outlook.
5. Calendar sharing questions: the requester does it themselves, see how-to-microsoft-365.md.
6. Note the ticket and close.

Escalate if: webmail is also failing for more than one person (outage, L3), or a mailbox is over its size limit and needs an archive change (L2).
