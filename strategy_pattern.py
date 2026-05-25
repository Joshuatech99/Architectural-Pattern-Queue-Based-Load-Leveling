from abc import ABC, abstractmethod
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from state_pattern import ProposalContext


class ValidationStrategy(ABC):

    @abstractmethod
    def validate(self, proposal: "ProposalContext") -> Tuple[bool, str]:
        pass


class PKMKValidation(ValidationStrategy):

    REQUIRED_KEYWORDS = ("anggaran", "rab")

    def validate(self, proposal: "ProposalContext") -> Tuple[bool, str]:
        if proposal.pkm_type.upper() != "PKM-K":
            return False, (
                f"Tipe proposal '{proposal.pkm_type}' tidak sesuai dengan strategi PKM-K."
            )

        filename_lower = proposal.filename.lower()
        if not any(kw in filename_lower for kw in self.REQUIRED_KEYWORDS):
            return False, (
                f"File '{proposal.filename}' tidak mengandung kata kunci 'anggaran' atau 'rab'. "
                f"PKM-K wajib menyertakan Rencana Anggaran Biaya (RAB)."
            )

        return True, (
            f"File '{proposal.filename}' mengandung RAB. Validasi PKM-K berhasil."
        )


class PKMREValidation(ValidationStrategy):

    REQUIRED_KEYWORDS = ("izin_lab", "izinlab", "izin lab", "lab_permit")

    def validate(self, proposal: "ProposalContext") -> Tuple[bool, str]:
        if proposal.pkm_type.upper() != "PKM-RE":
            return False, (
                f"Tipe proposal '{proposal.pkm_type}' tidak sesuai dengan strategi PKM-RE."
            )

        filename_lower = proposal.filename.lower()
        if not any(kw in filename_lower for kw in self.REQUIRED_KEYWORDS):
            return False, (
                f"File '{proposal.filename}' tidak mengandung bukti izin laboratorium. "
                f"PKM-RE wajib melampirkan surat izin penggunaan lab atau fasilitas riset."
            )

        return True, (
            f"File '{proposal.filename}' mengandung bukti izin lab. Validasi PKM-RE berhasil."
        )


class PKMPMValidation(ValidationStrategy):

    REQUIRED_KEYWORDS = ("mitra", "kemitraan", "partner")

    def validate(self, proposal: "ProposalContext") -> Tuple[bool, str]:
        if proposal.pkm_type.upper() != "PKM-PM":
            return False, (
                f"Tipe proposal '{proposal.pkm_type}' tidak sesuai dengan strategi PKM-PM."
            )

        filename_lower = proposal.filename.lower()
        if not any(kw in filename_lower for kw in self.REQUIRED_KEYWORDS):
            return False, (
                f"File '{proposal.filename}' tidak mengandung lampiran mitra. "
                f"PKM-PM wajib menyertakan surat kemitraan atau persetujuan dari mitra masyarakat."
            )

        return True, (
            f"File '{proposal.filename}' mengandung lampiran mitra. Validasi PKM-PM berhasil."
        )


class DefaultValidation(ValidationStrategy):

    def validate(self, proposal: "ProposalContext") -> Tuple[bool, str]:
        return False, (
            f"Tipe PKM '{proposal.pkm_type}' tidak tersedia dalam sistem. "
            f"Tipe yang didukung: PKM-K, PKM-RE, PKM-PM."
        )


def get_strategy(pkm_type: str) -> ValidationStrategy:
    mapping = {
        "PKM-K":  PKMKValidation,
        "PKM-RE": PKMREValidation,
        "PKM-PM": PKMPMValidation,
    }
    strategy_class = mapping.get(pkm_type.upper(), DefaultValidation)
    return strategy_class()
