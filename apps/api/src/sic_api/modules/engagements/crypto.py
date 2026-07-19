from __future__ import annotations

import base64
import json
import os
from typing import Protocol

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from sic_api.modules.addresses.schemas import AddressView

from .schemas import BookingAddressView


class AddressCipher(Protocol):
    def encrypt(self, address: AddressView) -> str: ...
    def decrypt(self, value: str) -> BookingAddressView: ...


class AddressEncryptionConfigurationError(RuntimeError):
    pass


class AesGcmAddressCipher:
    associated_data = b"sic-booking-address-v1"

    def __init__(self, encoded_key: str) -> None:
        try:
            key = base64.urlsafe_b64decode(encoded_key.encode("ascii"))
        except (ValueError, UnicodeError) as error:
            raise AddressEncryptionConfigurationError("Booking address encryption key is invalid") from error
        if len(key) != 32:
            raise AddressEncryptionConfigurationError("Booking address encryption key must decode to 32 bytes")
        self.aes = AESGCM(key)

    def encrypt(self, address: AddressView) -> str:
        payload = BookingAddressView(
            label=address.label,
            formatted_address=address.formatted_address,
            street=address.street,
            street_number=address.street_number,
            unit=address.unit,
            city=address.city,
            province=address.province,
            postal_code=address.postal_code,
        ).model_dump_json().encode("utf-8")
        nonce = os.urandom(12)
        encrypted = self.aes.encrypt(nonce, payload, self.associated_data)
        return base64.urlsafe_b64encode(nonce + encrypted).decode("ascii")

    def decrypt(self, value: str) -> BookingAddressView:
        try:
            raw = base64.urlsafe_b64decode(value.encode("ascii"))
            payload = self.aes.decrypt(raw[:12], raw[12:], self.associated_data)
            return BookingAddressView.model_validate(json.loads(payload.decode("utf-8")))
        except Exception as error:
            raise AddressEncryptionConfigurationError("Booking address snapshot could not be decrypted") from error
