"""
STATE PATTERN - PKM PROPOSAL SYSTEM
Dibuat oleh: llham Syawal ALfata
File ini akan di-import oleh Anggota B
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, Tuple


# ============================================================
# STATE INTERFACE
# ============================================================

class ProposalState(ABC):

    @abstractmethod
    def get_name(self) -> str:
        pass
    
    @abstractmethod
    def upload(self, proposal: 'ProposalContext', file_content: str) -> bool:
        pass
    
    @abstractmethod
    def verify(self, proposal: 'ProposalContext') -> bool:
        pass
    
    @abstractmethod
    def edit(self, proposal: 'ProposalContext', new_content: str) -> bool:
        pass
    
    @abstractmethod
    def can_upload(self) -> bool:
        pass
    
    @abstractmethod
    def can_verify(self) -> bool:
        pass
    
    @abstractmethod
    def can_edit(self) -> bool:
        pass


# ============================================================
# CONCRETE STATES
# ============================================================

class DraftState(ProposalState):
    def get_name(self) -> str:
        return "DRAFT"
    
    def upload(self, proposal: 'ProposalContext', file_content: str) -> bool:
        print(f"  📤 [State] Mengupload file ke proposal {proposal.id}...")
        proposal.file_content = file_content
        proposal.set_state(UploadingState())
        print(f"  ✅ [State] Upload selesai! Status → {proposal.get_status()}")
        return True
    
    def verify(self, proposal: 'ProposalContext') -> bool:
        print(f"  ❌ [State] Tidak bisa verifikasi dari status DRAFT. Upload dulu.")
        return False
    
    def edit(self, proposal: 'ProposalContext', new_content: str) -> bool:
        print(f"  ✏️ [State] Mengedit proposal {proposal.id}...")
        proposal.file_content = new_content
        print(f"  ✅ [State] Edit berhasil.")
        return True
    
    def can_upload(self) -> bool:
        return True
    
    def can_verify(self) -> bool:
        return False
    
    def can_edit(self) -> bool:
        return True


class UploadingState(ProposalState):
    def get_name(self) -> str:
        return "UPLOADING"
    
    def upload(self, proposal: 'ProposalContext', file_content: str) -> bool:
        print(f"  ❌ [State] Tidak bisa upload ulang. Proposal sedang dalam antrean.")
        return False
    
    def verify(self, proposal: 'ProposalContext') -> bool:
        print(f"  🔍 [State] Memulai verifikasi proposal {proposal.id}...")
        proposal.set_state(VerifyingState())
        return True
    
    def edit(self, proposal: 'ProposalContext', new_content: str) -> bool:
        print(f"  ❌ [State] Tidak bisa edit. Proposal sedang dalam antrean verifikasi.")
        return False
    
    def can_upload(self) -> bool:
        return False
    
    def can_verify(self) -> bool:
        return True
    
    def can_edit(self) -> bool:
        return False


class VerifyingState(ProposalState):
    def __init__(self):
        self._verification_result: Optional[bool] = None
    
    def get_name(self) -> str:
        return "VERIFYING"
    
    def upload(self, proposal: 'ProposalContext', file_content: str) -> bool:
        print(f"  ❌ [State] Tidak bisa upload. Proposal sedang diverifikasi.")
        return False
    
    def verify(self, proposal: 'ProposalContext') -> bool:
        print(f"  🔍 [State] Sedang memverifikasi dokumen...")
        
        # Panggil strategy yang sudah di-set oleh Anggota B
        if proposal.validation_strategy:
            is_valid, message = proposal.validation_strategy.validate(
                proposal.file_content, 
                proposal.pkm_type
            )
            
            if is_valid:
                proposal.set_state(SubmittedState())
                print(f"  ✅ [State] Verifikasi BERHASIL! Status → SUBMITTED")
            else:
                proposal.set_state(RejectedState(message))
                print(f"  ❌ [State] Verifikasi GAGAL: {message}")
            
            return is_valid
        else:
            # Fallback jika strategy belum di-set
            print(f"  ⚠️ [State] Belum ada validation_strategy, menggunakan validasi default")
            if len(proposal.file_content) >= 50:
                proposal.set_state(SubmittedState())
                print(f"  ✅ [State] Verifikasi BERHASIL (default)!")
                return True
            else:
                proposal.set_state(RejectedState("Konten terlalu pendek (default validation)"))
                print(f"  ❌ [State] Verifikasi GAGAL (default)!")
                return False
    
    def edit(self, proposal: 'ProposalContext', new_content: str) -> bool:
        print(f"  ❌ [State] Tidak bisa edit. Proposal sedang diverifikasi.")
        return False
    
    def can_upload(self) -> bool:
        return False
    
    def can_verify(self) -> bool:
        return True
    
    def can_edit(self) -> bool:
        return False


class SubmittedState(ProposalState):
    def get_name(self) -> str:
        return "SUBMITTED"
    
    def upload(self, proposal: 'ProposalContext', file_content: str) -> bool:
        print(f"  ❌ [State] Proposal sudah SUBMITTED. Tidak bisa upload ulang.")
        return False
    
    def verify(self, proposal: 'ProposalContext') -> bool:
        print(f"  ℹ️ [State] Proposal sudah terverifikasi dan SUBMITTED.")
        return True
    
    def edit(self, proposal: 'ProposalContext', new_content: str) -> bool:
        print(f"  ❌ [State] Proposal sudah SUBMITTED. Tidak bisa diedit.")
        return False
    
    def can_upload(self) -> bool:
        return False
    
    def can_verify(self) -> bool:
        return False
    
    def can_edit(self) -> bool:
        return False


class RejectedState(ProposalState):
    def __init__(self, reason: str = ""):
        self.reason = reason
    
    def get_name(self) -> str:
        return "REJECTED"
    
    def get_reason(self) -> str:
        return self.reason
    
    def upload(self, proposal: 'ProposalContext', file_content: str) -> bool:
        print(f"  📤 [State] Mengupload ulang proposal {proposal.id} (setelah ditolak)...")
        proposal.file_content = file_content
        proposal.set_state(UploadingState())
        print(f"  ✅ [State] Upload ulang berhasil! Status → {proposal.get_status()}")
        return True
    
    def verify(self, proposal: 'ProposalContext') -> bool:
        print(f"  ❌ [State] Proposal ditolak. Upload ulang terlebih dahulu.")
        return False
    
    def edit(self, proposal: 'ProposalContext', new_content: str) -> bool:
        print(f"  ✏️ [State] Mengedit proposal {proposal.id} (status ditolak)...")
        proposal.file_content = new_content
        print(f"  ✅ [State] Edit berhasil. Silakan upload ulang.")
        return True
    
    def can_upload(self) -> bool:
        return True
    
    def can_verify(self) -> bool:
        return False
    
    def can_edit(self) -> bool:
        return True


# ============================================================
# CONTEXT (PROPOSAL)
# ============================================================

class ProposalContext:
    """
    Context untuk State Pattern
    Kelas ini akan digunakan oleh Anggota B (Strategy Pattern)
    """
    
    def __init__(self, proposal_id: str, student_name: str, pkm_type: str):
        self.id = proposal_id
        self.student_name = student_name
        self.pkm_type = pkm_type
        self.file_content: str = ""
        self._state: ProposalState = DraftState()
        self.validation_strategy = None  # Akan di-set oleh Anggota B
        
        print(f"📄 [Context] Proposal {self.id} dibuat dengan status: {self._state.get_name()}")
    
    def set_state(self, new_state: ProposalState):
        old_state = self._state.get_name()
        self._state = new_state
        print(f"  🔄 [Context] Status berubah: {old_state} → {self._state.get_name()}")
    
    def get_status(self) -> str:
        if isinstance(self._state, RejectedState):
            return f"{self._state.get_name()} - {self._state.get_reason()}"
        return self._state.get_name()
    
    def get_state_object(self) -> ProposalState:
        return self._state
    
    def set_validation_strategy(self, strategy):
        """Method untuk Anggota B menyetel strategy validasi"""
        self.validation_strategy = strategy
        print(f"🔧 [Context] Validation strategy telah di-set untuk proposal {self.id}")
    
    # Actions
    def upload(self, file_content: str) -> bool:
        print(f"\n[ACTION] Mahasiswa {self.student_name} mengupload proposal {self.id}")
        return self._state.upload(self, file_content)
    
    def verify(self) -> bool:
        print(f"\n[ACTION] Sistem memverifikasi proposal {self.id}")
        return self._state.verify(self)
    
    def edit(self, new_content: str) -> bool:
        print(f"\n[ACTION] Mahasiswa {self.student_name} mengedit proposal {self.id}")
        return self._state.edit(self, new_content)
    
    def can_upload(self) -> bool:
        return self._state.can_upload()
    
    def can_verify(self) -> bool:
        return self._state.can_verify()
    
    def can_edit(self) -> bool:
        return self._state.can_edit()


# ============================================================
# TESTING (Untuk Anggota A)
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING STATE PATTERN - Anggota A")
    print("="*60)
    
    proposal = ProposalContext("TEST-1", "Bayu Test", "PKM-K")
    proposal.upload("Ini adalah konten proposal yang cukup panjang untuk lulus validasi default." * 2)
    proposal.verify()
    
    print(f"\n📊 Status akhir: {proposal.get_status()}")
    print("\n✅ State Pattern Test Complete")