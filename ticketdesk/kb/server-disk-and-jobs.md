# Server disk full, failed jobs, one service down

Category: server
Owner: L2 infrastructure. The Service Desk collects the facts. Time: 1 hour to respond.

1. Collect: server name, what failed (job name, error code), since when, who is affected, is there a deadline.
2. Disk full: do not delete anything from the Service Desk. L2 checks the usual suspects: old log files, temp folders, orphaned report exports. RPT-01 has a cleanup script at C:\ops\cleanup-reports.ps1.
3. Failed backup job (error 0x8007xxxx): L2 checks the backup console, the target share, and free space on the backup target; re-run the job manually once fixed.
4. One service down for one team: L2 restarts the service, checks the event log, and notes the root cause on the ticket.
5. Tell the requester the expected time and keep the ticket updated every hour until fixed.

Escalate if: the server hosts a core service for everyone (email, files, ERP) or more than one server shows the same fault (L3 incident).
