"""Owner-only utility for Fasal Rin subscription documents."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


PRODUCT_ID = "FASAL_RIN_AUTOMATION"
SCHEMA_VERSION = 1
ROOT = Path(__file__).resolve().parent
LICENSE_DIR = ROOT / "licenses"
PRIVATE_KEY_FILE = ROOT / "secrets" / "fasal_rin_private_key.pem"
PUBLIC_KEY_FILE = ROOT / "fasal_rin_public_key.pem"
CUSTOMER_LEDGER_FILE = ROOT / "secrets" / "customer_ledger.json"


def normalize_user_id(value: str) -> str:
    return "".join(ch for ch in str(value or "").upper().strip() if ch.isalnum())


def license_identity(user_id: str) -> str:
    normalized = normalize_user_id(user_id)
    if not normalized:
        raise ValueError("Mobile No./User ID required hai.")
    source = f"{PRODUCT_ID}|{normalized}".encode("utf-8")
    return hashlib.sha256(source).hexdigest()


def canonical_payload(payload: dict) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def keygen() -> None:
    if PRIVATE_KEY_FILE.exists():
        raise FileExistsError(
            f"Private key already exists: {PRIVATE_KEY_FILE}. It was not replaced."
        )
    PRIVATE_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    PRIVATE_KEY_FILE.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    PUBLIC_KEY_FILE.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print(f"Private key: {PRIVATE_KEY_FILE}")
    print(f"Public key:  {PUBLIC_KEY_FILE}")


def load_private_key():
    if not PRIVATE_KEY_FILE.is_file():
        raise FileNotFoundError("Private signing key missing hai. Pehla keygen run karo.")
    return serialization.load_pem_private_key(
        PRIVATE_KEY_FILE.read_bytes(), password=None
    )


def write_signed_document(payload: dict, target: Path) -> Path:
    private_key = load_private_key()
    signature = private_key.sign(
        canonical_payload(payload),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    envelope = {
        "payload": payload,
        "signature": base64.b64encode(signature).decode("ascii"),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return target


def write_license(payload: dict) -> Path:
    target = LICENSE_DIR / f"{payload['license_id']}.json"
    return write_signed_document(payload, target)


def update_customer_ledger(user_id: str, values: dict) -> None:
    normalized = normalize_user_id(user_id)
    ledger: dict[str, dict] = {}
    if CUSTOMER_LEDGER_FILE.is_file():
        ledger = json.loads(CUSTOMER_LEDGER_FILE.read_text(encoding="utf-8"))
    current = dict(ledger.get(normalized) or {})
    current.update(values)
    ledger[normalized] = current
    CUSTOMER_LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    CUSTOMER_LEDGER_FILE.write_text(json.dumps(ledger, indent=2), encoding="utf-8")


def activate(args: argparse.Namespace) -> None:
    valid_from = date.fromisoformat(args.valid_from)
    expires_on = date.fromisoformat(args.expires_on)
    if expires_on < valid_from:
        raise ValueError("Expiry date start date ton pehla nahi ho sakdi.")
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    license_id = license_identity(args.user_id)
    payload = {
        "schema": SCHEMA_VERSION,
        "product_id": PRODUCT_ID,
        "license_id": license_id,
        "status": "active",
        "valid_from": valid_from.isoformat(),
        "expires_on": expires_on.isoformat(),
        "access": ["standalone", "integrated"],
        "updated_at": now,
    }
    target = write_license(payload)
    update_customer_ledger(
        args.user_id,
        {
            "license_id": license_id,
            "customer_name": args.customer_name.strip(),
            "notes": args.notes.strip(),
            "status": "active",
            "valid_from": valid_from.isoformat(),
            "expires_on": expires_on.isoformat(),
            "updated_at": now,
        },
    )
    print(f"ACTIVE: {license_id}")
    print(f"FILE:   {target}")


def revoke(args: argparse.Namespace) -> None:
    license_id = license_identity(args.user_id)
    target = LICENSE_DIR / f"{license_id}.json"
    if not target.is_file():
        raise FileNotFoundError(f"License file nahi mili: {target}")
    envelope = json.loads(target.read_text(encoding="utf-8"))
    payload = dict(envelope.get("payload") or {})
    payload["status"] = "revoked"
    payload["updated_at"] = datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat()
    write_license(payload)
    update_customer_ledger(
        args.user_id,
        {
            "status": "revoked",
            "notes": args.notes.strip() or "Revoked by owner",
            "updated_at": payload["updated_at"],
        },
    )
    print(f"REVOKED: {license_id}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fasal Rin subscription manager")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("keygen", help="Create the one-time signing key pair")

    identity = commands.add_parser("identity", help="Show hashed license identity")
    identity.add_argument("--user-id", required=True)

    add = commands.add_parser("activate", help="Activate or renew one customer")
    add.add_argument("--user-id", required=True)
    add.add_argument("--expires-on", required=True, help="YYYY-MM-DD")
    add.add_argument("--valid-from", default=date.today().isoformat())
    add.add_argument("--customer-name", default="")
    add.add_argument("--notes", default="")

    remove = commands.add_parser("revoke", help="Revoke one customer")
    remove.add_argument("--user-id", required=True)
    remove.add_argument("--notes", default="")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "keygen":
        keygen()
    elif args.command == "identity":
        print(license_identity(args.user_id))
    elif args.command == "activate":
        activate(args)
    elif args.command == "revoke":
        revoke(args)


if __name__ == "__main__":
    main()
