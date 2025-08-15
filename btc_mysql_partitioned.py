# btc_mysql_partitioned.py

# Import library yang dibutuhkan
import hashlib
import ecdsa
import base58
import os
import mysql.connector
from multiprocessing import Process, Value, Lock
import sys
import smtplib
import ssl
from email.mime.text import MIMEText

# ==================================================================================================
#                                 KONFIGURASI UTAMA
# ==================================================================================================

# Nama file untuk daftar alamat Bitcoin yang akan dicari.
PUZZLE_FILE = "puzzle.txt"

# Nama file untuk menyimpan hasil jika kunci ditemukan.
WIN_FILE = "puzzle_win.txt"

# Nama file log untuk pencarian yang gagal atau dihentikan.
FAIL_FILE = "pencarian_gagal.txt"

EMAIL_SENDER = "tesakunyunus01@gmail.com"
EMAIL_PASSWORD = "wumw nsju xfbm toye"
EMAIL_RECEIVER = "myunussandi@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# ==================================================================================================
#                                 KONFIGURASI DATABASE
# ==================================================================================================
# Ubah nilai di bawah ini dengan detail database MySQL Anda.
# HOST ini akan diubah ke IP Privat VM utama (ubuntu-btc)
DB_HOST = "localhost"       
DB_USER = "yunus"            
DB_PASSWORD = "Yunus@1234"           
DB_NAME = "btc_scanning"  

def get_db_connection():
    """
    Membuat dan mengembalikan koneksi ke database MySQL.
    Akan menghentikan program jika koneksi gagal.
    """
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error: Gagal terhubung ke database MySQL: {err}")
        sys.exit(1)

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
    except Exception:
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
    except Exception:
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

def save_failed_search(start, end, status, lock):
    """
    Menyimpan log pencarian yang gagal atau terinterupsi ke dalam file.
    Menggunakan lock untuk mencegah konflik saat menulis ke file.
    """
    with lock:
        with open(FAIL_FILE, 'a') as f:
            f.write(f"Rentang pencarian dari {start} sampai {end} {status}.\n")
            f.write("================================================================\n\n")

# ==================================================================================================
#                               FUNGSI INTERAKSI DATABASE
# ==================================================================================================

def update_range_in_db(process_id, new_start_key, lock):
    """
    Memperbarui nilai 'start' untuk proses tertentu di database.
    """
    with lock:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            sql = "UPDATE key_ranges SET start = %s WHERE id = %s"
            cursor.execute(sql, (new_start_key, process_id))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"[Proses {process_id}] Error saat memperbarui progres di DB: {e}")
            pass

def remove_range_from_db(process_id, lock):
    """
    Menghapus rentang yang sudah selesai dipindai dari database.
    """
    with lock:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            sql = "DELETE FROM key_ranges WHERE id = %s"
            cursor.execute(sql, (process_id,))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"[Proses {process_id}] Error saat menghapus rentang dari DB: {e}")
            pass

def get_key_ranges_from_db(start_id, end_id):
    """
    Mengambil rentang kunci dari database berdasarkan rentang ID.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT id, start, end FROM key_ranges WHERE id BETWEEN %s AND %s"
        cursor.execute(sql, (start_id, end_id))
        ranges = cursor.fetchall()
        cursor.close()
        conn.close()
        return ranges
    except Exception as e:
        print(f"Error: Gagal mengambil rentang dari database: {e}")
        return []

# ==================================================================================================
#                           FUNGSI UNTUK PROSES PENCARIAN
# ==================================================================================================

def brute_force_process(process_id, start_range, end_range, target_addresses, found_flag, lock):
    """
    Fungsi yang akan dijalankan oleh setiap proses untuk mencari private key.
    """
    try:
        start_int = int(start_range, 16)
        end_int = int(end_range, 16)
    except ValueError:
        print(f"[Proses {process_id}] Error: Nilai rentang '{start_range}' atau '{end_range}' tidak valid.")
        return

    total_keys = end_int - start_int + 1
    print(f"[Proses {process_id}] Mulai mencari dari {start_range} sampai {end_range}. Total {total_keys} kunci.")

    scanned_keys_count = 0

    for i in range(start_int, end_int + 1):
        if found_flag.value:
            last_scanned_key = hex(i - 1)[2:].zfill(64)
            update_range_in_db(process_id, last_scanned_key, lock)
            print(f"[Proses {process_id}] Progres terakhir '{last_scanned_key}' disimpan.")
            return

        private_key_hex = hex(i)[2:].zfill(64)

        scanned_keys_count += 1
        # Update progres setiap 10.000 kunci
        if scanned_keys_count % 10000 == 0:
            update_range_in_db(process_id, private_key_hex, lock)
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

                    # Hapus semua rentang dari database setelah ditemukan
                    remove_range_from_db(process_id, lock)
            return

    if not found_flag.value:
        print(f"[Proses {process_id}] Selesai mencari dalam rentang ini tanpa menemukan kunci.")
        save_failed_search(start_range, end_range, "tidak ditemukan", lock)
        remove_range_from_db(process_id, lock)


def main():
    """
    Fungsi utama untuk menjalankan pencarian multiproses dengan database MySQL.
    """
    # Mengambil rentang ID dari argumen baris perintah
    if len(sys.argv) < 3:
        print("Penggunaan: python3 btc_mysql_partitioned.py <start_id> <end_id>")
        sys.exit(1)
    
    start_id = int(sys.argv[1])
    end_id = int(sys.argv[2])
    
    target_addresses = get_target_addresses(PUZZLE_FILE)
    if not target_addresses:
        print("Tidak ada alamat yang ditemukan di puzzle.txt. Program berhenti.")
        return

    # Ambil rentang spesifik dari database
    ranges = get_key_ranges_from_db(start_id, end_id)
    if not ranges:
        print(f"Tidak ada rentang yang ditemukan untuk ID {start_id} sampai {end_id}.")
        return

    found_flag = Value('b', 0)
    lock = Lock()
    processes = []

    print(f"Membuat proses untuk rentang ID {start_id} sampai {end_id}...")

    for r in ranges:
        p = Process(target=brute_force_process, args=(
            r['id'], r['start'], r['end'], target_addresses, found_flag, lock
        ))
        processes.append(p)
        p.start()

    print(f"{len(processes)} proses telah dimulai.\n")

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        print("\n\nInterupsi Keyboard terdeteksi. Menghentikan semua proses...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.join()
        print("Semua proses telah dihentikan.")
        print("Program telah dihentikan oleh pengguna.")

    if found_flag.value:
        print("\n================================================================")
        print("Pencarian selesai. Kunci ditemukan.")
    else:
        print("\n================================================================")
        print("Pencarian selesai. Tidak ada kunci yang ditemukan.")

    print("----------------------------------------------------------------")

if __name__ == "__main__":
    main()
