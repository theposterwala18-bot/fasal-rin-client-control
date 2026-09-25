# Fasal Rin Client Control

This repository controls only the `FASAL_RIN_AUTOMATION` product. It is fully
separate from Mr Dhaliwal Creation subscriptions and repositories.

Each customer is activated from the same Fasal Rin portal Mobile No./User ID.
The public `licenses/subscription_manifest.json` stores only SHA-256 product
identities, dates, status, and access rights. Raw User IDs, customer names,
payment details, and owner notes stay in the ignored local registry files.
Every entitlement includes both
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

The application checks this signed manifest:

```text
https://raw.githubusercontent.com/theposterwala18-bot/fasal-rin-client-control/main/licenses/subscription_manifest.json
```

## Registry workflow

1. Open `Fasal Rin Subscription Registry`.
2. Save or update the customer using dates in `DD-MM-YYYY` format.
3. Use `Upload GitHub Now` for automatic upload.
4. For manual upload, use `Open Upload Folder`, open the GitHub repository's
   `licenses` folder, and upload only `subscription_manifest.json`.

The registry makes a dated daily backup in `registry_backups/daily` and also
keeps a timestamped backup before every change. These backup and registry files
are ignored by Git and stay owner-only.

The legacy hashed JSON file remains temporarily for older Fasal Rin builds. New
builds use only `subscription_manifest.json`.
