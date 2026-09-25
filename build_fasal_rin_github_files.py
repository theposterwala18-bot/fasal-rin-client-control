from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from license_admin import (
    PRODUCT_ID,
    SCHEMA_VERSION,
    license_identity,
    write_signed_document,
)


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "fasal_rin_registry.csv"
LICENSES_DIR = ROOT / "licenses"
PUBLISH_LICENSES_DIR = ROOT / "publish" / "licenses"
SUMMARY_PATH = ROOT / "publish" / "build_summary.txt"
MANIFEST_NAME = "subscription_manifest.json"
MANIFEST_PATH = LICENSES_DIR / MANIFEST_NAME
UPLOAD_GUIDE_PATH = ROOT / "publish" / "MANUAL GITHUB UPLOAD GUIDE.txt"


def clean(value: object) -> str:
    return str(value or "").strip()


def normalize_user_id(value: object) -> str:
    return "".join(ch for ch in clean(value).upper() if ch.isalnum())


def normalize_date(value: object, row_number: int, field_name: str) -> str:
    text = clean(value)
    for date_format in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, date_format).date().isoformat()
        except ValueError:
            continue
    raise ValueError(
        f"Row {row_number}: {field_name} date invalid hai. DD-MM-YYYY use karo."
    )


def main() -> int:
    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"Fasal Rin registry nahi mili: {CSV_PATH}")

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    seen_users: set[str] = set()
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    subscriptions: dict[str, dict[str, object]] = {}

    for row_number, raw in enumerate(rows, start=2):
        user_id = normalize_user_id(raw.get("mobile_user_id"))
        if not user_id:
            continue
        if user_id in seen_users:
            raise ValueError(f"Duplicate Mobile No./User ID row {row_number}: {user_id}")
        seen_users.add(user_id)

        valid_from = clean(raw.get("valid_from"))
        expires_at = clean(raw.get("expires_at"))
        if not valid_from or not expires_at:
            raise ValueError(f"Row {row_number}: Valid From/Expires At required ne.")
        valid_from = normalize_date(valid_from, row_number, "Valid From")
        expires_at = normalize_date(expires_at, row_number, "Expires At")
        if expires_at < valid_from:
            raise ValueError(f"Row {row_number}: Expires At, Valid From ton pehla hai.")

        license_id = license_identity(user_id)
        commercial_status = clean(raw.get("status")).lower() or "paid"
        public_status = "revoked" if commercial_status == "blocked" else "active"
        subscriptions[license_id] = {
            "schema": SCHEMA_VERSION,
            "product_id": PRODUCT_ID,
            "license_id": license_id,
            "status": public_status,
            "valid_from": valid_from,
            "expires_on": expires_at,
            "access": ["standalone", "integrated"],
            "updated_at": generated_at,
        }

    LICENSES_DIR.mkdir(parents=True, exist_ok=True)
    manifest_payload = {
        "schema": SCHEMA_VERSION,
        "product_id": PRODUCT_ID,
        "manifest_type": "subscription_manifest",
        "generated_at": generated_at,
        "subscriptions": subscriptions,
    }
    write_signed_document(manifest_payload, MANIFEST_PATH)

    if PUBLISH_LICENSES_DIR.exists():
        shutil.rmtree(PUBLISH_LICENSES_DIR)
    PUBLISH_LICENSES_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MANIFEST_PATH, PUBLISH_LICENSES_DIR / MANIFEST_NAME)

    UPLOAD_GUIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_GUIDE_PATH.write_text(
        "FASAL RIN - MANUAL GITHUB UPLOAD\n"
        "=================================\n\n"
        "1. GitHub te fasal-rin-client-control repository kholo.\n"
        "2. Repository de licenses folder nu kholo.\n"
        "3. Add file > Upload files click karo.\n"
        "4. publish\\licenses\\subscription_manifest.json file upload karo.\n"
        "5. Commit directly to main choose karke Commit changes click karo.\n"
        "6. Upload complete hon ton 1-2 minute baad Fasal Rin subscription check karo.\n\n"
        "Repository:\n"
        "https://github.com/theposterwala18-bot/fasal-rin-client-control\n\n"
        "Upload sirf subscription_manifest.json nu karna hai. Registry CSV, backup, "
        "private key ja client details GitHub te upload nahi karniyan.\n",
        encoding="utf-8",
    )

    summary = {
        "product_id": PRODUCT_ID,
        "generated_at": generated_at,
        "client_count": len(subscriptions),
        "github_folder": "licenses",
        "upload_file": MANIFEST_NAME,
        "manual_upload_folder": str(PUBLISH_LICENSES_DIR),
        "manual_guide": str(UPLOAD_GUIDE_PATH),
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Fasal Rin GitHub manifest ready: {len(subscriptions)} client(s)")
    print(PUBLISH_LICENSES_DIR / MANIFEST_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
