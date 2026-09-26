# MFA and authenticator problems

Category: mfa
Owner: Service Desk (L1). Time: 10 minutes.

Symptoms: new phone, authenticator app empty, "code invalid", no codes arriving.

1. Verify identity by callback or manager confirmation before touching MFA. Never reset MFA from an email request alone.
2. New phone: in the admin console, Users > MFA > "Require re-registration". The requester signs in on a laptop, gets the QR code, scans it with the Authenticator app on the new phone.
3. Codes invalid: on the phone, Authenticator > Settings > "Time correction" (or turn automatic date and time on). Wait one minute and try a fresh code.
4. No push notifications: check the phone has internet, notifications are allowed for Authenticator, and the app is up to date.
5. Give a one time temporary access pass if the requester is travelling and cannot re-register today. It expires in 8 hours.
6. Note the ticket and close.

Escalate if: the requester reports sign in prompts they did not start (security, L2), or the account has admin roles.
