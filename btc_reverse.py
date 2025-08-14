# btc_reverse.py

import hashlib
import ecdsa
import base58
import os
import sys

# ==================================================================================================
#                                 KONFIGURASI UTAMA
# ==================================================================================================

# Atur rentang pencarian private key dalam format heksadesimal.
# CONTOH DARI PENGGUNA:
# start_range = ""
# end_range = "00000000000000000000000000000000000000000000000000000000000007ff"
# 0000000000000000000000000000000000000000000000000000000000000400
# 0000000000000000000000000000000000000000000000400000000000000000
# 00000000000000000000000000000000000000000000007fffffffffffffffff
# 400000000000000000:7fffffffffffffffff
# Silakan ubah nilai di bawah ini sesuai dengan rentang yang ingin Anda coba.
start_range = "0000000000000000000000000000000000000000000000000000000000000200"
end_range   = "00000000000000000000000000000000000000000000000000000000000003ff"

# Nama file untuk daftar alamat Bitcoin yang akan dicari.
PUZZLE_FILE = "puzzle.txt"

# Nama file untuk menyimpan hasil jika kunci ditemukan.
WIN_FILE = "puzzle_win.txt"

# Nama file untuk menyimpan log pencarian yang gagal.
FAIL_FILE = "pencarian_gagal_reverse.txt"

# ==================================================================================================
#                               FUNGSI UNTUK PEMROSESAN BITCOIN
# ==================================================================================================

def private_key_to_public_key(private_key_hex):
    """
    Mengkonversi private key (hex) menjadi public key (hex terkompresi).
    """
    try:
        # Konversi private key dari hex ke integer
        private_key_int = int(private_key_hex, 16)

        # Buat curve secp256k1
        sk = ecdsa.SigningKey.from_secret_exponent(private_key_int, curve=ecdsa.SECP256k1)

        # Dapatkan public key
        vk = sk.get_verifying_key()

        # Public key dalam format hex terkompresi
        # Public key dimulai dengan 02 jika y genap, 03 jika y ganjil
        public_key_bytes = vk.to_string("compressed")
        public_key_hex = public_key_bytes.hex()

        return public_key_hex
    except Exception as e:
        print(f"Error saat mengkonversi private key: {e}")
        return None

def public_key_to_address(public_key_hex):
    """
    Mengkonversi public key (hex terkompresi) menjadi alamat Bitcoin (Legacy).
    """
    try:
        # Konversi public key dari hex ke bytes
        public_key_bytes = bytes.fromhex(public_key_hex)

        # Step 1: Lakukan SHA-256 pada public key
        sha256_hash = hashlib.sha256(public_key_bytes).digest()

        # Step 2: Lakukan RIPEMD-160 pada hasil SHA-256
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()

        # Step 3: Tambahkan versi byte (0x00 untuk mainnet Bitcoin)
        version_ripemd160 = b'\x00' + ripemd160_hash

        # Step 4: Lakukan SHA-256 pada hasil dari step 3
        checksum_hash1 = hashlib.sha256(version_ripemd160).digest()

        # Step 5: Lakukan SHA-256 pada hasil dari step 4
        checksum_hash2 = hashlib.sha256(checksum_hash1).digest()

        # Step 6: Ambil 4 byte pertama dari hasil step 5 sebagai checksum
        checksum = checksum_hash2[:4]

        # Step 7: Gabungkan versi byte, RIPEMD-160 hash, dan checksum
        address_bytes = version_ripemd160 + checksum

        # Step 8: Encode hasil gabungan ke Base58
        bitcoin_address = base58.b58encode(address_bytes).decode('utf-8')

        return bitcoin_address
    except Exception as e:
        print(f"Error saat mengkonversi public key ke alamat: {e}")
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

def save_winning_key(private_key_hex, public_key_hex, bitcoin_address):
    """
    Menyimpan private key, public key, dan alamat Bitcoin yang cocok ke dalam file.
    """
    with open(WIN_FILE, 'a') as f:
        f.write("================================================================\n")
        f.write("Match found!\n")
        f.write(f"Private Hex Key: {private_key_hex}\n")
        f.write(f"Public Key (Compressed): {public_key_hex}\n")
        f.write(f"Compressed BTC Address: {bitcoin_address}\n")
        f.write("================================================================\n\n")

def save_failed_search(start, end, status):
    """
    Menyimpan log pencarian yang gagal atau terinterupsi ke dalam file.
    """
    with open(FAIL_FILE, 'a') as f:
        f.write(f"Rentang pencarian terbalik dari {end} sampai {start} {status}.\n")
        f.write("================================================================\n\n")

def main():
    """
    Fungsi utama untuk melakukan brute force pada rentang private key.
    """
    # Periksa apakah file puzzle.txt ada
    target_addresses = get_target_addresses(PUZZLE_FILE)
    if not target_addresses:
        print("Tidak ada alamat yang ditemukan di puzzle.txt. Program berhenti.")
        return

    print("Mulai mencari private key secara terbalik...")
    print(f"Rentang pencarian: {end_range} sampai {start_range}")
    print(f"Alamat target: {target_addresses}")
    print("----------------------------------------------------------------")

    # Konversi rentang hex ke integer
    start_int = int(start_range, 16)
    end_int = int(end_range, 16)

    # Menghitung total kunci dalam rentang
    total_keys = end_int - start_int + 1
    print(f"Total kunci yang akan discan: {total_keys}\n")

    # Variabel untuk melacak apakah kecocokan ditemukan dan kunci terakhir yang discan
    match_found = False
    last_scanned_key = end_range

    try:
        # Lakukan iterasi dari end_int ke start_int secara terbalik
        for i in range(end_int, start_int - 1, -1):
            # Konversi integer kembali ke format hex 64 digit
            private_key_hex = hex(i)[2:].zfill(64)
            last_scanned_key = private_key_hex  # Simpan kunci terakhir yang sedang diproses

            # Hitung public key dari private key
            public_key_hex = private_key_to_public_key(private_key_hex)
            if not public_key_hex:
                continue

            # Hitung alamat Bitcoin dari public key
            bitcoin_address = public_key_to_address(public_key_hex)
            if not bitcoin_address:
                continue

            # Tampilkan private key dan alamat yang sedang diproses
            # Tampilkan status setiap 10000 iterasi
            if (end_int - i) % 10000 == 0:
                print(f"[{end_int - i + 1}/{total_keys}] Mencoba private key: {private_key_hex}")

            # Periksa apakah alamat yang dihasilkan cocok dengan alamat target
            if bitcoin_address in target_addresses:
                print("\n================================================================")
                print("                *** PUZZLE DITEMUKAN! ***")
                print("================================================================")
                print(f"Private key yang cocok: {private_key_hex}")
                print(f"Alamat Bitcoin: {bitcoin_address}")

                # Simpan hasil ke file puzzle_win.txt
                save_winning_key(private_key_hex, public_key_hex, bitcoin_address)
                print(f"\nHasil telah disimpan ke file {WIN_FILE}")

                match_found = True
                break # Berhenti setelah menemukan kunci

    except KeyboardInterrupt:
        # Menangani interupsi dari keyboard (Ctrl+C)
        print("\n\n----------------------------------------------------------------")
        print("Pencarian dihentikan oleh pengguna.")
        print(f"Rentang yang terakhir kali discan adalah dari {end_range} sampai {last_scanned_key}.")
        save_failed_search(start_range, last_scanned_key, "dihentikan oleh pengguna")
        print(f"Log pencarian yang dihentikan telah disimpan ke file {FAIL_FILE}")
        sys.exit(0) # Keluar dari program

    # Log pencarian yang gagal setelah loop selesai
    if not match_found:
        print("\n----------------------------------------------------------------")
        print("Pencarian selesai.")
        print("Tidak ada private key yang cocok dengan alamat target dalam rentang ini.")
        save_failed_search(start_range, end_range, "tidak ditemukan")
        print(f"Log pencarian yang gagal telah disimpan ke file {FAIL_FILE}")

    print("\n----------------------------------------------------------------")
    print("Program selesai.")

if __name__ == "__main__":
    main()
