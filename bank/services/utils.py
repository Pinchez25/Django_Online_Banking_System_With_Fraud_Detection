import secrets

TRANSACTION_TYPES = (
    ("D", "Deposit"),
    ("W", "Withdrawal"),
    ("T", "Transfer"),
)

# Crockford-style Base32 alphabet: excludes ambiguous characters such as 0/O and 1/I.
TRANSACTION_REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TRANSACTION_REFERENCE_LENGTH = 10


def generate_transaction_id():
    """Generate a short, opaque, cryptographically random transaction reference.

    Ten Base32 characters provide 50 bits of randomness while remaining short enough
    for a customer-facing transaction code. The database UNIQUE constraint is the
    final authority on uniqueness; generation is intentionally independent of
    transaction volume and does not expose an account's transaction count.
    """
    return "".join(
        secrets.choice(TRANSACTION_REFERENCE_ALPHABET)
        for _ in range(TRANSACTION_REFERENCE_LENGTH)
    )
