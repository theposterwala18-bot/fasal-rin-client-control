from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from license_admin import PRODUCT_ID, SCHEMA_VERSION, license_identity, write_license


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "fasal_rin_registry.csv"
LICENSES_DIR = ROOT / "licenses"
PUBLISH_LICENSES_DIR = ROOT / "publish" / "licenses"
SUMMARY_PATH = ROOT / "publish" / "build_summary.txt"


def clean(value: object) -> str:
    return str(value or "").strip()


def normalize_user_id(value: object) -> str:
    return "".join(ch for ch in clean(value).upper() if ch.isalnum())


def main() -> int:
    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"Fasal Rin registry nahi mili: {CSV_PATH}")

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    active_ids: set[str] = set()
    seen_users: set[str] = set()
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    built = 0

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

        license_id = license_identity(user_id)
        commercial_status = clean(raw.get("status")).lower() or "paid"
        public_status = "revoked" if commercial_status == "blocked" else "active"
        payload = {
            "schema": SCHEMA_VERSION,
            "product_id": PRODUCT_ID,
            "license_id": license_id,
            "status": public_status,
            "valid_from": valid_from,
            "expires_on": expires_at,
            "access": ["standalone", "integrated"],
            "updated_at": generated_at,
        }
        write_license(payload)
        active_ids.add(license_id)
        built += 1

    LICENSES_DIR.mkdir(parents=True, exist_ok=True)
    for path in LICENSES_DIR.glob("*.json"):
        if path.stem not in active_ids:
            path.unlink()

    if PUBLISH_LICENSES_DIR.exists():
        shutil.rmtree(PUBLISH_LICENSES_DIR)
    PUBLISH_LICENSES_DIR.mkdir(parents=True, exist_ok=True)
    for path in LICENSES_DIR.glob("*.json"):
        shutil.copy2(path, PUBLISH_LICENSES_DIR / path.name)

    summary = {
        "product_id": PRODUCT_ID,
        "generated_at": generated_at,
        "client_count": built,
        "github_folder": "licenses",
        "manual_upload_folder": str(PUBLISH_LICENSES_DIR),
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Fasal Rin GitHub files ready: {built}")
    print(PUBLISH_LICENSES_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
