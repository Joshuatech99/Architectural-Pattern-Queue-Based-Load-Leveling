"""
  - Proxy Pattern      (DocumentValidationProxy)
  - asyncio.Queue      (antrean proposal in-memory)
  - Main Loop          (interactive CLI)

"""

import asyncio
from typing import Tuple, Dict
from state_pattern import ProposalContext
from strategy_pattern import get_strategy
from observer_pattern import (
    ProposalEventPublisher,
    EmailNotifier,
    DashboardNotifier,
    AuditLogObserver,
)

# menyimpan proposal yang berstatus REJECTED agar user bisa mengedit kontennya dan mengirim ulang
rejected_proposals: Dict[str, ProposalContext] = {}

# Proxy pattern bertindak sebagai gatekeeper sebelum proposal masuk
# ke antrean asyncio.Queue.  Dua validasi dilakukan:
#   1. Ekstensi file harus .pdf (case-insensitive)
#   2. Ukuran file harus <= 5 MB

class DocumentValidationProxy:

    ALLOWED_EXTENSION = ".pdf"
    MAX_SIZE_MB = 5.0

    # cek apakah nama file berakhiran .pdf
    def validate_filename(self, filename: str) -> bool:
        """Cek akhiran .pdf, case-insensitive."""
        return filename.lower().endswith(self.ALLOWED_EXTENSION)

    # cek apakah ukuran file <= MAX_SIZE_MB
    def validate_size(self, size_mb: float) -> bool:
        """Cek ukuran file <= MAX_SIZE_MB (5 MB)."""
        return size_mb <= self.MAX_SIZE_MB

    # process validasi gabungan lalu masukkan ke antrean
    async def process(
        self,
        proposal: ProposalContext,
        file_size_mb: float,
        queue: asyncio.Queue,
    ) -> Tuple[bool, str]:
        """
        Validasi file proposal.
        Jika valid  -> masukkan ke antrean, return (True, pesan sukses).
        Jika tidak  -> tolak langsung, return (False, alasan penolakan).
        """

        # Cek ekstensi
        filename = getattr(proposal, "filename", "")

        if not self.validate_filename(filename):
            reason = (
                f"Ekstensi file '{filename}' tidak valid. "
                f"Hanya file {self.ALLOWED_EXTENSION} yang diperbolehkan."
            )
            print(f"\n  [Proxy] DITOLAK - {reason}")
            return False, reason

        # Cek ukuran
        if not self.validate_size(file_size_mb):
            reason = (
                f"Ukuran file {file_size_mb} MB melebihi batas "
                f"maksimal {self.MAX_SIZE_MB} MB."
            )
            print(f"\n  [Proxy] DITOLAK - {reason}")
            return False, reason

        # Semua valid -> masukkan ke antrean
        await queue.put(proposal)
        msg = (
            f"File {filename} ({file_size_mb} MB) valid -> masuk antrean."
        )
        print(f"\n  [Proxy] {msg}")
        return True, msg


# Worker berjalan di background, terus menerus mengambil
# proposal dari asyncio.Queue dan memprosesnya melalui
# Observer Pattern (upload -> verify -> notifikasi).
# Jika proposal REJECTED, worker menyimpannya
# ke dictionary rejected_proposals agar bisa diedit oleh user

async def worker(worker_id: int, queue: asyncio.Queue) -> None:
    while True:
        # Ambil proposal berikutnya dari antrean (blocking sampai tersedia)
        proposal = await queue.get()

        try:
            print(f"\n{'='*60}")
            print(f"  [Worker {worker_id}] Memproses proposal {proposal.id}...")
            print(f"{'='*60}")

            # Simulasi delay processing (background task)
            await asyncio.sleep(1)

            # Set validation strategy dari strategy_pattern.py
            strategy = get_strategy(proposal.pkm_type)
            proposal.set_validation_strategy(strategy)

            # Buat publisher dan daftarkan observer
            publisher = ProposalEventPublisher(proposal)

            email_notifier = EmailNotifier()
            dashboard_notifier = DashboardNotifier()
            audit_log = AuditLogObserver()

            publisher.subscribe(email_notifier)
            publisher.subscribe(dashboard_notifier)
            publisher.subscribe(audit_log)

            # Upload file content (State: DRAFT -> UPLOADING)
            publisher.upload(proposal.file_content)

            # Transisi UPLOADING -> VERIFYING (langsung tanpa publisher)
            proposal.verify()

            # Verifikasi proposal (State: VERIFYING -> SUBMITTED/REJECTED)
            publisher.verify()

            # Cetak status akhir
            status = proposal.get_status()
            print(f"\n  [Worker {worker_id}] Status akhir proposal {proposal.id}: "
                  f"{status}")

            # Simpan proposal REJECTED untuk fitur edit
            if "REJECTED" in status:
                rejected_proposals[proposal.id] = proposal
                print(f"  [Worker {worker_id}] Proposal {proposal.id} disimpan. "
                      f"Ketik 'edit' di menu utama untuk memperbaiki.")

            # Cetak audit log
            audit_log.print_all_logs()

        except Exception as e:
            print(f"\n  [Worker {worker_id}] Error saat memproses "
                  f"proposal {proposal.id}: {e}")

        finally:
            # Tandai task selesai agar queue.join() bisa proceed
            queue.task_done()

# Fungsi ini menampilkan daftar proposal yang berstatus REJECTED,
# meminta user memilih proposal yang ingin diedit, memasukkan konten baru
async def handle_edit(
    queue: asyncio.Queue,
) -> None:
    """
    Menangani fitur edit proposal yang ditolak (REJECTED).
    Menampilkan daftar proposal rejected, meminta user memilih,
    mengedit konten, lalu memasukkan kembali ke antrean.
    """

    # Cek apakah ada proposal yang ditolak
    if not rejected_proposals:
        print("\n  [EDIT] Tidak ada proposal yang ditolak saat ini.")
        print("  [EDIT] Semua proposal sudah berhasil disubmit atau belum diproses.\n")
        return

    # Tampilkan daftar proposal yang ditolak
    print(f"\n{'='*60}")
    print(f"  [EDIT] Daftar Proposal yang Ditolak ({len(rejected_proposals)} proposal)")
    print(f"{'='*60}")

    for idx, (pid, proposal) in enumerate(rejected_proposals.items(), 1):
        reason = proposal.get_status()
        print(f"  {idx}. ID: {pid} | Mahasiswa: {proposal.student_name} "
              f"| Tipe: {proposal.pkm_type}")
        print(f"     Status: {reason}")
        print(f"     Konten saat ini: {proposal.file_content}")
        print()

    print("  Panduan isi konten proposal:")
    print("    - PKM-K  : harus mengandung kata 'anggaran' atau 'rab'")
    print("    - PKM-RE : harus mengandung kata 'izin lab'")
    print("    - PKM-PM : harus mengandung kata 'mitra' atau 'kemitraan'")
    print()

    # Minta user memilih proposal yang ingin diedit
    try:
        selected_id = await asyncio.to_thread(
            input,
            "  Masukkan ID proposal yang ingin diedit (atau 'batal' untuk kembali): "
        )
    except EOFError:
        return

    selected_id = selected_id.strip()

    if selected_id.lower() == "batal":
        print("  [EDIT] Batal. Kembali ke menu utama.\n")
        return

    # Cari proposal yang dipilih
    if selected_id not in rejected_proposals:
        print(f"  [EDIT] Proposal dengan ID '{selected_id}' tidak ditemukan "
              f"dalam daftar proposal ditolak.\n")
        return

    proposal = rejected_proposals[selected_id]

    # Minta konten baru dari user
    print(f"\n  [EDIT] Mengedit proposal {proposal.id} (Mahasiswa: {proposal.student_name})")
    print(f"  [EDIT] Konten lama: {proposal.file_content}")

    try:
        new_content = await asyncio.to_thread(
            input,
            "  Masukkan konten proposal baru: "
        )
    except EOFError:
        return

    new_content = new_content.strip()

    if not new_content:
        print("  [EDIT] Konten kosong. Edit dibatalkan.\n")
        return

    # Panggil proposal.edit() dari State Pattern
    edit_success = proposal.edit(new_content)

    if not edit_success:
        print(f"  [EDIT] Gagal mengedit proposal {proposal.id}. "
              f"State saat ini tidak mengizinkan edit.\n")
        return

    # Upload ulang proposal
    proposal.upload(new_content)

    # Masukkan kembali ke antrean untuk diproses worker
    await queue.put(proposal)

    # Hapus dari daftar rejected karena sudah dikirim ulang
    del rejected_proposals[selected_id]

    print(f"  [EDIT] Proposal {proposal.id} berhasil diedit dan dikirim ulang ke antrean.")
    print(f"  [EDIT] Menunggu worker memproses...\n")

    # Tunggu worker selesai memproses
    await queue.join()



# SIMULASI H-1 (upload 7 proposal sekaligus)

async def simulate_h1(
    queue: asyncio.Queue,
    proxy: DocumentValidationProxy,
) -> None:

    # 7 data dummy
    dummy_proposals = [
        {
            "id": "01",
            "name": "Ilham",
            "pkm_type": "PKM-K",
            "filename": "proposal_ilham.pdf",
            "size_mb": 4.0,
            "content": "Proposal PKM-K dengan anggaran Rp 10 juta dan RAB terperinci.",
        },
        {
            "id": "02",
            "name": "Bayu",
            "pkm_type": "PKM-RE",
            "filename": "proposal_bayu.pdf",
            "size_mb": 3.5,
            "content": "Penelitian katalis, izin lab dari laboratorium kimia.",
        },
        {
            "id": "03",
            "name": "Audi",
            "pkm_type": "PKM-PM",
            "filename": "proposal_audi.pdf",
            "size_mb": 1.8,
            "content": "Pemberdayaan masyarakat karang taruna.",
        },
        {
            "id": "04",
            "name": "Lutfian",
            "pkm_type": "PKM-K",
            "filename": "proposal_lutfian.pdf",
            "size_mb": 4.2,
            "content": "Bisnis kuliner, biaya lengkap.",
        },
        {
            "id": "05",
            "name": "Fulca",
            "pkm_type": "PKM-RE",
            "filename": "proposal_fulca.pdf",
            "size_mb": 2.5,
            "content": "Riset enzim, sudah mendapat izin lab pusat.",
        },
        {
            "id": "06",
            "name": "Atmim",
            "pkm_type": "PKM-PM",
            "filename": "proposal_atmim.pdf",
            "size_mb": 2.5,
            "content": "Pemberdayaan masyarakat dengan mitra karang taruna.",
        },
        {
            "id": "07",
            "name": "Nusuki",
            "pkm_type": "PKM-PM",
            "filename": "proposal_nusuki.pdf",
            "size_mb": 7.0,
            "content": "Pemberdayaan masyarakat dengan mitra karang taruna.",
        },
    ]

    total = len(dummy_proposals)
    print(f"\n  [SIMULASI H-1] Mengirimkan {total} proposal sekaligus ke antrean...")

    for data in dummy_proposals:
        # Buat objek ProposalContext
        proposal = ProposalContext(
            data["id"],
            data["name"],
            data["pkm_type"],
        )
        proposal.file_content = data["content"]
        proposal.filename = data["filename"]

        # Validasi via Proxy (ekstensi & ukuran)
        accepted, message = await proxy.process(
            proposal, data["size_mb"], queue
        )

        if not accepted:
            print(f"  [SIMULASI H-1] Proposal {data['id']} DITOLAK: {message}")

    # Worker akan memproses proposal secara paralel di background.
    print(f"  [SIMULASI H-1] Semua proposal telah dikirim ke antrean.")
    print(f"  [SIMULASI H-1] Worker sedang memproses di background...\n")



# Main loop
async def main() -> None:
    """
    Fungsi utama:
      1. Buat asyncio.Queue + Proxy
      2. Jalankan worker tasks di background
      3. Loop interaktif: minta input proposal dari user
      4. Validasi via Proxy -> masuk antrean -> diproses Worker
      5. Ketik 'edit' untuk mengedit proposal yang ditolak
      6. Ketik 'h-1' untuk simulasi concurrency
      7. Ketik 'exit' untuk keluar
    """

    # Header
    print("\n" + "=" * 60)
    print("       ========== PKM UPLOAD SYSTEM ==========")
    print("=" * 60)
    print("  Sistem Upload Proposal PKM Asinkron")
    print("  Design Patterns: State | Strategy | Observer | Proxy")
    print("  Powered by asyncio.Queue + Worker Coroutines")
    print("=" * 60)
    print("\n  Panduan isi konten proposal:")
    print("    - PKM-K  : harus mengandung kata 'anggaran' atau 'rab'")
    print("    - PKM-RE : harus mengandung kata 'izin lab'")
    print("    - PKM-PM : harus mengandung kata 'mitra' atau 'kemitraan'")
    print("\n  Perintah khusus:")
    print("    - Ketik 'edit' pada ID proposal -> edit proposal yang ditolak")
    print("    - Ketik 'h-1'  pada ID proposal -> simulasi H-1 (concurrency)")
    print("    - Ketik 'exit' pada ID proposal -> keluar dari sistem")

    # Inisialisasi Queue & Proxy
    proposal_queue = asyncio.Queue()
    proxy = DocumentValidationProxy()

    # Buat worker tasks (2 worker)
    worker_tasks = []
    num_workers = 2
    for i in range(1, num_workers + 1):
        task = asyncio.create_task(worker(i, proposal_queue))
        worker_tasks.append(task)
    print(f"\n  [INFO] {num_workers} worker sudah aktif dan menunggu proposal...\n")

    # Loop interaktif
    while True:
        print("-" * 60)
        print("  Masukkan data proposal (ketik 'exit' untuk keluar)")
        print("-" * 60)

        # Input ID Proposal
        try:
            proposal_id = await asyncio.to_thread(input, "  ID proposal: ")
        except EOFError:
            break

        if proposal_id.strip().lower() == "exit":
            print("\n  [EXIT] Keluar dari sistem...")
            break

        # Simulasi H-1: kirim 7 proposal sekaligus (concurrency demo)
        if proposal_id.strip().lower() == "h-1":
            await simulate_h1(proposal_queue, proxy)
            continue

        # Fitur Edit proposal yang ditolak
        if proposal_id.strip().lower() == "edit":
            await handle_edit(proposal_queue)
            continue

        # Input data lainnya
        try:
            student_name = await asyncio.to_thread(input, "  Nama mahasiswa: ")
            pkm_type = await asyncio.to_thread(input, "  Tipe PKM (PKM-K/PKM-RE/PKM-PM): ")
            filename = await asyncio.to_thread(input, "  Nama file dokumen (contoh: proposal.pdf): ")
            size_input = await asyncio.to_thread(input, "  Ukuran file (MB): ")
            file_content = await asyncio.to_thread(
                input,
                "  Isi/teks proposal (teks simulasi isi dokumen): "
            )
        except EOFError:
            break

        # Parse ukuran file
        try:
            file_size_mb = float(size_input.strip())
        except ValueError:
            print("\n  [WARNING] Ukuran file tidak valid. Harus berupa angka.")
            continue

        # Buat objek ProposalContext
        proposal = ProposalContext(
            proposal_id.strip(),
            student_name.strip(),
            pkm_type.strip().upper(),
        )

        # Set file content (simulasi - tidak ada upload sungguhan)
        proposal.file_content = file_content.strip()

        # Set filename sebagai atribut tambahan untuk proxy validation
        proposal.filename = filename.strip()

        # Validasi via Proxy -> masuk antrean jika valid
        accepted, message = await proxy.process(
            proposal, file_size_mb, proposal_queue
        )

        if accepted:
            print(f"  [ANTREAN] Proposal {proposal.id} berhasil masuk antrean. "
                  f"Menunggu worker memproses...")
            # Tunggu worker menyelesaikan pemrosesan proposal ini
            # sebelum meminta input berikutnya (mencegah output tumpang tindih)
            await proposal_queue.join()
        else:
            print(f"  [DITOLAK] Proposal {proposal.id} ditolak oleh proxy: {message}")

    # Tunggu semua proposal di antrean selesai diproses
    print("\n  [MENUNGGU] Menunggu semua proposal dalam antrean selesai diproses...")
    await proposal_queue.join()
    print("  [OK] Semua proposal telah diproses!")

    # Batalkan semua worker tasks
    for task in worker_tasks:
        task.cancel()

    # Tunggu semua task selesai dicancel
    await asyncio.gather(*worker_tasks, return_exceptions=True)

    print("\n" + "=" * 60)
    print("  [SELESAI] PKM Upload System ditutup. Terima kasih!")
    print("=" * 60 + "\n")


# ENTRY POINT
if __name__ == "__main__":
    asyncio.run(main())
