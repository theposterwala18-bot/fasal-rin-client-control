# Fasal Rin Client Control

This repository controls only the `FASAL_RIN_AUTOMATION` product. It is fully
separate from Mr Dhaliwal Creation subscriptions and repositories.

Each customer is activated from the same Fasal Rin portal Mobile No./User ID.
The public repository stores only its SHA-256 product identity, dates, status,
and access rights. Raw User IDs, customer names, and owner notes stay in the
ignored `secrets/customer_ledger.json`. Every entitlement includes both
`standalone` and `integrated` access and is signed with the owner-only private
key.

## One-time setup

```powershell
py -3 license_admin.py keygen
```

Keep `secrets/fasal_rin_private_key.pem` owner-only and backed up securely. It
must never be uploaded or included in a client setup. Copy
`fasal_rin_public_key.pem` into the Fasal Rin application as
`license_public_key.pem`.

Create a separate GitHub repository named `fasal-rin-client-control` and upload
this folder except `secrets/`. The application checks:

```text
https://raw.githubusercontent.com/theposterwala18-bot/fasal-rin-client-control/main/licenses/{license_id}.json
```

## Activate or renew

```powershell
py -3 license_admin.py activate --user-id 9815036664 --expires-on 2027-03-31 --customer-name "PACS Name"
git add licenses
git commit -m "Activate Fasal Rin subscription"
git push
```

## Revoke

```powershell
py -3 license_admin.py revoke --user-id 9815036664 --notes "Payment pending"
git add licenses
git commit -m "Revoke Fasal Rin subscription"
git push
```
