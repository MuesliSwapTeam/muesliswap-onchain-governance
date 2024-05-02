import dataclasses

import pycardano


@dataclasses.dataclass
class FixedTxHashTransaction:
    """
    Substrate type because pycardano does not support fixed tx hashes
    and always computes them live, but may generate imprecise deserializations of transactions
    """

    transaction: pycardano.Transaction
    hash: str

    @property
    def id(self):
        return pycardano.TransactionId.from_primitive(bytes.fromhex(self.hash))

    @property
    def transaction_body(self):
        return self.transaction.transaction_body

    @property
    def transaction_witness_set(self):
        return self.transaction.transaction_witness_set

    @property
    def valid(self):
        return self.transaction.valid

    @property
    def auxiliary_data(self):
        return self.transaction.auxiliary_data
