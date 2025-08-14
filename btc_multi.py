# btc_multiprocess.py

import hashlib
import ecdsa
import base58
import os
import json
from multiprocessing import Process, Value, Lock

import smtplib
import ssl
from email.mime.text import MIMEText

EMAIL_SENDER = "tesakunyunus01@gmail.com"  # Ganti dengan email pengirim Anda
EMAIL_PASSWORD = "wumw nsju xfbm toye"   # Ganti dengan sandi aplikasi (bukan sandi akun)
EMAIL_RECEIVER = "myunussandi@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# ==================================================================================================
#                                 KONFIGURASI UTAMA
# ==================================================================================================

# Nama file untuk daftar alamat Bitcoin yang akan dicari.
PUZZLE_FILE = "puzzle.txt"

# Nama file untuk menyimpan hasil jika kunci ditemukan.
WIN_FILE = "puzzle_win.txt"

# Nama file log untuk pencarian yang gagal atau dihentikan.
FAIL_FILE = "pencarian_gagal.txt"

# Nama file untuk membaca rentang pencarian yang dibagi.
RANGE_FILE = "range_splitter.json"

# ==================================================================================================
#                               FUNGSI UNTUK PEMROSESAN BITCOIN
# ==================================================================================================

def send_email(subject, body):
    """
    Mengirim email notifikasi.
    """
    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = EMAIL_SENDER
    message["To"] = EMAIL_RECEIVER

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, message.as_string())
        print("Notifikasi email berhasil dikirim!")
    except Exception as e:
        print(f"Error saat mengirim email: {e}")

def private_key_to_public_key(private_key_hex):
    """
    Mengkonversi private key (hex) menjadi public key (hex terkompresi).
    """
    try:
        private_key_int = int(private_key_hex, 16)
        sk = ecdsa.SigningKey.from_secret_exponent(private_key_int, curve=ecdsa.SECP256k1)
        vk = sk.get_verifying_key()
        public_key_bytes = vk.to_string("compressed")
        public_key_hex = public_key_bytes.hex()
        return public_key_hex
    except Exception as e:
        # Menghilangkan output error yang berlebihan untuk setiap kunci yang gagal
        return None

def public_key_to_address(public_key_hex):
    """
    Mengkonversi public key (hex terkompresi) menjadi alamat Bitcoin (Legacy).
    """
    try:
        public_key_bytes = bytes.fromhex(public_key_hex)
        sha256_hash = hashlib.sha256(public_key_bytes).digest()
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
        version_ripemd160 = b'\x00' + ripemd160_hash
        checksum_hash1 = hashlib.sha256(version_ripemd160).digest()
        checksum_hash2 = hashlib.sha256(checksum_hash1).digest()
        checksum = checksum_hash2[:4]
        address_bytes = version_ripemd160 + checksum
        bitcoin_address = base58.b58encode(address_bytes).decode('utf-8')
        return bitcoin_address
    except Exception as e:
        # Menghilangkan output error yang berlebihan
        return None

def get_target_addresses(file_path):
    """
    Membaca daftar alamat Bitcoin target dari file teks.
    """
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} tidak ditemukan.")
        return None
    with open(file_path, 'r') as f:
        addresses = [line.strip() for line in f.readlines() if line.strip()]
    return addresses

# def save_winning_key(private_key_hex, public_key_hex, bitcoin_address, lock):
#     """
#     Menyimpan private key, public key, dan alamat Bitcoin yang cocok ke dalam file.
#     Menggunakan lock untuk mencegah konflik saat menulis ke file.
#     """
#     with lock:
#         with open(WIN_FILE, 'a') as f:
#             f.write("================================================================\n")
#             f.write("Match found!\n")
#             f.write(f"Private Hex Key: {private_key_hex}\n")
#             f.write(f"Public Key (Compressed): {public_key_hex}\n")
#             f.write(f"Compressed BTC Address: {bitcoin_address}\n")
#             f.write("================================================================\n\n")

def save_failed_search(start, end, status, lock, is_reverse=False):
    """
    Menyimpan log pencarian yang gagal atau terinterupsi ke dalam file.
    Menggunakan lock untuk mencegah konflik saat menulis ke file.
    """
    with lock:
        with open(FAIL_FILE, 'a') as f:
            if is_reverse:
                f.write(f"Rentang pencarian terbalik dari {end} sampai {start} {status}.\n")
            else:
                f.write(f"Rentang pencarian dari {start} sampai {end} {status}.\n")
            f.write("================================================================\n\n")

def update_range_in_json(process_id, new_start_key, lock):
    """
    Mengambil rentang dari file range_splitter.json dan memperbarui nilai 'start'
    untuk proses tertentu.
    """
    with lock:
        try:
            with open(RANGE_FILE, 'r') as f:
                ranges = json.load(f)

            for r in ranges:
                if r['id'] == process_id:
                    r['start'] = new_start_key
                    break

            with open(RANGE_FILE, 'w') as f:
                json.dump(ranges, f, indent=4)
        except Exception as e:
            print(f"[Proses {process_id}] Error saat memperbarui progres: {e}")
            pass

def remove_range_from_json(process_id, lock):
    """
    Menghapus rentang yang sudah selesai dipindai dari file range_splitter.json.
    """
    with lock:
        try:
            with open(RANGE_FILE, 'r') as f:
                ranges = json.load(f)

            # Filter rentang yang sudah selesai
            updated_ranges = [r for r in ranges if r['id'] != process_id]

            with open(RANGE_FILE, 'w') as f:
                json.dump(updated_ranges, f, indent=4)
        except Exception as e:
            # Peringatan jika terjadi error, tapi tidak menghentikan program
            print(f"[Proses {process_id}] Error saat menghapus rentang dari file JSON: {e}")
            pass

# ==================================================================================================
#                           FUNGSI UNTUK PROSES PENCARIAN
# ==================================================================================================

def brute_force_process(process_id, start_range, end_range, target_addresses, found_flag, lock):
    """
    Fungsi yang akan dijalankan oleh setiap proses untuk mencari private key.
    """
    start_int = int(start_range, 16)
    end_int = int(end_range, 16)

    # Menghitung total kunci dalam rentang ini
    total_keys = end_int - start_int + 1

    print(f"[Proses {process_id}] Mulai mencari dari {start_range} sampai {end_range}. Total {total_keys} kunci.")

    scanned_keys_count = 0

    for i in range(start_int, end_int + 1):
        # Memeriksa apakah kunci sudah ditemukan oleh proses lain
        if found_flag.value:
            # Menyimpan progres terakhir sebelum keluar
            last_scanned_key = hex(i - 1)[2:].zfill(64)
            update_range_in_json(process_id, last_scanned_key, lock)
            print(f"[Proses {process_id}] Progres terakhir '{last_scanned_key}' disimpan.")
            return

        private_key_hex = hex(i)[2:].zfill(64)

        scanned_keys_count += 1
        # Menyimpan progres setiap 10.000 iterasi
        if scanned_keys_count % 10000 == 0:
            update_range_in_json(process_id, private_key_hex, lock)
            print(f"[Proses {process_id}] Progres disimpan. Kunci terakhir: {private_key_hex}")

        public_key_hex = private_key_to_public_key(private_key_hex)
        if not public_key_hex:
            continue

        bitcoin_address = public_key_to_address(public_key_hex)
        if not bitcoin_address:
            continue

        if bitcoin_address in target_addresses:
            with lock:
                if not found_flag.value:
                    found_flag.value = 1
                    print(f"\n================================================================")
                    print(f"*** PUZZLE DITEMUKAN OLEH PROSES {process_id}! ***")
                    print(f"================================================================")
                    print(f"Private key yang cocok: {private_key_hex}")
                    print(f"Alamat Bitcoin: {bitcoin_address}")
                    # save_winning_key(private_key_hex, public_key_hex, bitcoin_address, lock)
                    # Simpan ke file puzzle_win.txt
                    with open(WIN_FILE, 'a') as f:
                        f.write("================================================================\n")
                        f.write("Match found!\n")
                        f.write(f"Private Hex Key: {private_key_hex}\n")
                        f.write(f"Public Key (Compressed): {public_key_hex}\n")
                        f.write(f"Compressed BTC Address: {bitcoin_address}\n")
                        f.write("================================================================\n\n")

                    # Kirim notifikasi email
                    subject = "Bitcoin Puzzle Match Found!"
                    body = (f"Halo,\n\nSebuah kunci Bitcoin telah ditemukan!\n\n"
                            f"Private Hex Key: {private_key_hex}\n"
                            f"Public Key (Compressed): {public_key_hex}\n"
                            f"Compressed BTC Address: {bitcoin_address}\n\n"
                            f"Salam,\nSkrip Brute Force")
                    send_email(subject, body)
                    print(f"\nHasil telah disimpan ke file '{WIN_FILE}' dan dikirim via email.")
            return

    # Jika pencarian selesai tanpa menemukan kecocokan
    if not found_flag.value:
        print(f"[Proses {process_id}] Selesai mencari dalam rentang ini tanpa menemukan kunci.")
        save_failed_search(start_range, end_range, "tidak ditemukan", lock)
        # Menghapus rentang dari file JSON karena sudah selesai dipindai
        remove_range_from_json(process_id, lock)


def main():
    """
    Fungsi utama untuk menjalankan pencarian multiproses.
    """
    # Periksa apakah file puzzle.txt ada
    target_addresses = get_target_addresses(PUZZLE_FILE)
    if not target_addresses:
        print("Tidak ada alamat yang ditemukan di puzzle.txt. Program berhenti.")
        return

    # Periksa apakah file range_splitter.json ada
    if not os.path.exists(RANGE_FILE):
        print(f"Error: File '{RANGE_FILE}' tidak ditemukan.")
        print("Jalankan 'btc_range_splitter.py' terlebih dahulu untuk membuat file ini.")
        return

    # Muat rentang dari file JSON
    with open(RANGE_FILE, 'r') as f:
        ranges = json.load(f)

    if not ranges:
        print(f"Error: File '{RANGE_FILE}' kosong atau tidak valid.")
        return

    # Siapkan variabel multiprocessing
    found_flag = Value('b', 0)
    lock = Lock()
    processes = []

    print("Membuat proses untuk setiap rentang...")

    for r in ranges:
        # Membuat proses baru untuk setiap rentang pencarian
        p = Process(target=brute_force_process, args=(
            r['id'], r['start'], r['end'], target_addresses, found_flag, lock
        ))
        processes.append(p)
        p.start()

    print(f"{len(processes)} proses telah dimulai.\n")

    try:
        for p in processes:
            p.join() # Menunggu semua proses selesai
    except KeyboardInterrupt:
        print("\n\nInterupsi Keyboard terdeteksi. Menghentikan semua proses...")
        for p in processes:
            p.terminate() # Menghentikan proses secara paksa
        for p in processes:
            p.join() # Menunggu semua proses benar-benar berhenti
        print("Semua proses telah dihentikan.")
        print("Program telah dihentikan oleh pengguna.")

    # Cek apakah kunci ditemukan
    if found_flag.value:
        print("\n================================================================")
        print("Pencarian selesai. Kunci ditemukan.")
    else:
        print("\n================================================================")
        print("Pencarian selesai. Tidak ada kunci yang ditemukan.")

    print("----------------------------------------------------------------")

if __name__ == "__main__":
    main()
