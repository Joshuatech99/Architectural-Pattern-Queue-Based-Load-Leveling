from abc import ABC, abstractmethod
from typing import List
import time
import datetime

# Import 
from state_pattern import ProposalContext, SubmittedState, RejectedState


# ============================================================
# OBSERVER INTERFACE
# ============================================================

class ProposalObserver(ABC):
    """
    Interface Observer.
    Semua notifier harus mengimplementasikan method update().
    """

    @abstractmethod
    def update(self, proposal: ProposalContext, event: str, detail: str = "") -> None:
        """
        Dipanggil oleh Subject ketika ada perubahan status.

        :param proposal: ProposalContext yang mengalami perubahan
        :param event:    Nama event, misal 'SUBMITTED', 'REJECTED', 'UPLOADING'
        :param detail:   Pesan tambahan (opsional)
        """
        pass


# ============================================================
# CONCRETE OBSERVERS
# ============================================================

class EmailNotifier(ProposalObserver):
    """
    Mock Email Notifier.
    Mensimulasikan pengiriman email kepada mahasiswa.
    """

    def update(self, proposal: ProposalContext, event: str, detail: str = "") -> None:
        timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        if event == "SUBMITTED":
            print(f"\n  [EmailNotifier] ============================")
            print(f"     Kepada  : {proposal.student_name}")
            print(f"     Subjek  : Proposal PKM Anda Telah Resmi Diterima!")
            print(f"     Isi     : Yth. {proposal.student_name},")
            print(f"               Proposal Anda dengan ID [{proposal.id}]")
            print(f"               bidang {proposal.pkm_type} telah berhasil")
            print(f"               diverifikasi dan RESMI DITERIMA oleh sistem.")
            print(f"     Waktu   : {timestamp}")
            print(f"  ============================================\n")

        elif event == "REJECTED":
            print(f"\n  [EmailNotifier] ============================")
            print(f"     Kepada  : {proposal.student_name}")
            print(f"     Subjek  : Proposal PKM Anda Perlu Diperbaiki")
            print(f"     Isi     : Yth. {proposal.student_name},")
            print(f"               Proposal Anda dengan ID [{proposal.id}]")
            print(f"               bidang {proposal.pkm_type} DITOLAK.")
            print(f"               Alasan  : {detail}")
            print(f"               Silakan perbaiki dan upload ulang.")
            print(f"     Waktu   : {timestamp}")
            print(f"  ============================================\n")

        elif event == "UPLOADING":
            print(f"\n  [EmailNotifier] Proposal [{proposal.id}] diterima, "
                  f"sedang diproses...\n")


class DashboardNotifier(ProposalObserver):
    """
    Mock Dashboard / Console Log Notifier.
    Mensimulasikan pembaruan status di portal web mahasiswa secara real-time.
    """

    def update(self, proposal: ProposalContext, event: str, detail: str = "") -> None:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        status_map = {
            "SUBMITTED"  : "BERHASIL DITERIMA",
            "REJECTED"   : "DITOLAK",
            "UPLOADING"  : "SEDANG DIPROSES",
            "VERIFYING"  : "SEDANG DIVERIFIKASI",
        }
        label = status_map.get(event, f"⚪ {event}")
        print(f"  [DashboardNotifier] [{timestamp}] "
              f"Portal diperbarui -> [{proposal.id}] {label}"
              + (f" | {detail}" if detail else ""))


class AuditLogObserver(ProposalObserver):
    """
    Audit Log Observer.
    Mencatat setiap perubahan status ke dalam log untuk keperluan audit.
    """

    def __init__(self):
        self._logs: List[str] = []

    def update(self, proposal: ProposalContext, event: str, detail: str = "") -> None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (f"[{timestamp}] AUDIT | ID={proposal.id} | "
                 f"Mahasiswa={proposal.student_name} | "
                 f"PKM={proposal.pkm_type} | Event={event}"
                 + (f" | Detail={detail}" if detail else ""))
        self._logs.append(entry)
        print(f"  [AuditLog] {entry}")

    def get_logs(self) -> List[str]:
        return list(self._logs)

    def print_all_logs(self) -> None:
        print("\n  [AuditLog] ===== RIWAYAT AUDIT =====")
        for log in self._logs:
            print(f"       {log}")
        print("  [AuditLog] ======================================\n")


# ============================================================
# SUBJECT (OBSERVABLE) — ProposalEventPublisher
# ============================================================

class ProposalEventPublisher:
    """
    Subject / Publisher dalam Observer Pattern.

    Kelas ini membungkus ProposalContext dan menambahkan kemampuan
    publish-subscribe. Setiap kali aksi penting dilakukan pada proposal
    (upload, verify), semua observer terdaftar akan diberitahu secara otomatis.

    Hubungan dengan State Pattern (Anggota A):
    - ProposalContext mengurus TRANSISI STATUS (state machine).
    - ProposalEventPublisher mengurus PEMBERITAHUAN setelah transisi terjadi.
    """

    def __init__(self, proposal: ProposalContext):
        self._proposal = proposal
        self._observers: List[ProposalObserver] = []
        print(f"[Publisher] Event publisher aktif untuk proposal {proposal.id}")

    # ---- Manajemen Observer ----

    def subscribe(self, observer: ProposalObserver) -> None:
        """Mendaftarkan observer baru."""
        if observer not in self._observers:
            self._observers.append(observer)
            print(f"  [Publisher] Observer '{observer.__class__.__name__}' terdaftar.")

    def unsubscribe(self, observer: ProposalObserver) -> None:
        """Mencabut pendaftaran observer."""
        if observer in self._observers:
            self._observers.remove(observer)
            print(f"  [Publisher] Observer '{observer.__class__.__name__}' dilepas.")

    def _notify_all(self, event: str, detail: str = "") -> None:
        """Memberitahu semua observer yang terdaftar."""
        print(f"  [Publisher] Mengirim event '{event}' ke "
              f"{len(self._observers)} observer(s)...")
        for observer in self._observers:
            observer.update(self._proposal, event, detail)

    # ---- Aksi Proposal (delegasi ke ProposalContext + notifikasi) ----

    def upload(self, file_content: str) -> bool:
        """Upload proposal dan notifikasi observer."""
        result = self._proposal.upload(file_content)
        if result:
            self._notify_all("UPLOADING")
        return result

    def verify(self) -> bool:
        """
        Verifikasi proposal.
        Setelah verifikasi, cek state akhir dan kirim notifikasi yang sesuai.
        """
        # Tandai state sebelum verifikasi
        self._notify_all("VERIFYING")

        # Simulasi delay proses background worker
        print("  [Publisher] Simulasi background worker memproses file...")
        time.sleep(1)

        result = self._proposal.verify()

        # Cek state akhir dan kirim event yang tepat
        final_state = self._proposal.get_state_object()
        if isinstance(final_state, SubmittedState):
            self._notify_all("SUBMITTED")
        elif isinstance(final_state, RejectedState):
            self._notify_all("REJECTED", final_state.reason)

        return result

    def edit(self, new_content: str) -> bool:
        """Edit proposal (hanya tersedia di state DRAFT / REJECTED)."""
        return self._proposal.edit(new_content)

    # ---- Getter ----

    def get_status(self) -> str:
        return self._proposal.get_status()

    @property
    def proposal(self) -> ProposalContext:
        return self._proposal


# ============================================================
# DEMO / TESTING
# ============================================================

#def demo_alur_diterima():
#    print("\n" + "=" * 60)
#    print("DEMO 1: Proposal Berhasil Diterima")
#    print("=" * 60)

#    from state_pattern import ProposalContext

    # Buat proposal
#    proposal = ProposalContext("PKM-2025-001", "Andi Mahasiswa", "PKM-K")

    # Buat publisher dan daftarkan observer
#    publisher = ProposalEventPublisher(proposal)
#    email_notif    = EmailNotifier()
#    dashboard      = DashboardNotifier()
#    audit_log      = AuditLogObserver()

#    publisher.subscribe(email_notif)
#    publisher.subscribe(dashboard)
#    publisher.subscribe(audit_log)

    # Alur: Upload -> Verify (berhasil, konten cukup panjang)
#    konten_valid = ("Proposal PKM-K bidang kewirausahaan. " * 5 +
#                    "Anggaran kas terlampir. " * 3)
#    publisher.upload(konten_valid)
#    publisher.verify()

#    print(f"\nStatus akhir: {publisher.get_status()}")
#    audit_log.print_all_logs()


#def demo_alur_ditolak():
#    print("\n" + "=" * 60)
#    print("DEMO 2: Proposal Ditolak (konten terlalu pendek)")
#    print("=" * 60)

#    from state_pattern import ProposalContext

#    proposal = ProposalContext("PKM-2025-002", "Budi Pelajar", "PKM-RE")
#    publisher = ProposalEventPublisher(proposal)

#    email_notif = EmailNotifier()
#    dashboard   = DashboardNotifier()
#    audit_log   = AuditLogObserver()

#    publisher.subscribe(email_notif)
#    publisher.subscribe(dashboard)
#    publisher.subscribe(audit_log)

    # Upload konten yang terlalu pendek -> akan ditolak (default validation)
#    publisher.upload("Isi proposal singkat.")
#    publisher.verify()

#    print(f"\n Status akhir: {publisher.get_status()}")

    # Mahasiswa memperbaiki dan upload ulang
#    print("\n--- Mahasiswa memperbaiki dan upload ulang ---")
#    proposal.edit("Proposal diperbaiki: " + "Detail lengkap penelitian. " * 5)
#    publisher.upload("Proposal diperbaiki: " + "Detail lengkap penelitian. " * 5)
#    publisher.verify()

#    print(f"\nStatus akhir setelah revisi: {publisher.get_status()}")
#    audit_log.print_all_logs()


#def demo_unsubscribe():
#    print("\n" + "=" * 60)
#    print("DEMO 3: Unsubscribe Observer")
#    print("=" * 60)

#    from state_pattern import ProposalContext

#    proposal  = ProposalContext("PKM-2025-003", "Citra Dewi", "PKM-PM")
#    publisher = ProposalEventPublisher(proposal)

#    email_notif = EmailNotifier()
#    dashboard   = DashboardNotifier()

#    publisher.subscribe(email_notif)
#    publisher.subscribe(dashboard)

    # Lepas email notifier — mahasiswa opt-out notifikasi email
#    publisher.unsubscribe(email_notif)

#    konten = "Proposal PKM-PM lengkap dengan rincian program pemberdayaan masyarakat. " * 3
#    publisher.upload(konten)
#    publisher.verify()

#    print(f"\nStatus akhir: {publisher.get_status()}")
#    print("  Email tidak dikirim karena EmailNotifier sudah unsubscribe.")


#if __name__ == "__main__":
#    demo_alur_diterima()
#    demo_alur_ditolak()
#    demo_unsubscribe()
#    print("\n Observer Pattern Test Complete")