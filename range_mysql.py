# btc_range_to_mysql.py
# Script ini membagi rentang heksadesimal dan menyimpannya ke tabel 'key_ranges' di database MySQL.

import mysql.connector
import sys

# =============================================================
# Konfigurasi Awal
# =============================================================
# Rentang heksadesimal awal yang ingin dibagi.
# Rentang ini di-padding menjadi 64 digit heksadesimal (256 bit).
# 400000000000000000:7fffffffffffffffff
# 0000000000000000000000000000000000000000000000000000000000080000
# 0000000000000000000000000000000000000000000000400000000000000000
# 00000000000000000000000000000000000000000000007fffffffffffffffff
start_hex_range = '0000000000000000000000000000000000000000000000000000000000080000'
end_hex_range = '00000000000000000000000000000000000000000000000000000000000fffff'

# Jumlah bagian yang Anda inginkan untuk membagi rentang.
num_splits = 100

# ==================================================================================================
#                                 KONFIGURASI DATABASE
# ==================================================================================================
# Ubah nilai di bawah ini dengan detail database MySQL Anda.
DB_HOST = "sql10.freesqldatabase.com"       # Host database
DB_USER = "sql10794884"            # Username database
DB_PASSWORD = "JbDXM3EPDt"            # Password database
DB_NAME = "sql10794884"  # Nama database

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

def save_ranges_to_db(ranges):
    """
    Menyimpan list rentang ke dalam tabel 'key_ranges' di database MySQL.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Menghapus data lama sebelum memasukkan data baru
    print("Menghapus data lama dari tabel 'key_ranges'...")
    cursor.execute("TRUNCATE TABLE key_ranges")

    sql = "INSERT INTO key_ranges (start, end) VALUES (%s, %s)"
    data = [(r['start'], r['end']) for r in ranges]

    print("Memasukkan rentang baru ke dalam database...")
    try:
        cursor.executemany(sql, data)
        conn.commit()
        print(f"{cursor.rowcount} rentang berhasil disimpan ke database.")
    except mysql.connector.Error as err:
        print(f"Error saat memasukkan data: {err}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

# =============================================================
# Logika Perhitungan
# =============================================================
def main():
    """
    Fungsi utama untuk membagi rentang dan menyimpan ke MySQL.
    """
    try:
        # Mengonversi rentang heksadesimal ke angka desimal
        start_dec = int(start_hex_range, 16)
        end_dec = int(end_hex_range, 16)

        # Menghitung total kunci yang ada di rentang
        total_keys = end_dec - start_dec + 1

        # Menghitung jumlah kunci per iterasi (dibagi berdasarkan num_splits)
        keys_per_iteration = total_keys // num_splits

        # Menghitung sisa pembagian (jika ada)
        remainder = total_keys % num_splits

        print(f"Total kunci dalam rentang: {total_keys:,}")
        print(f"Jumlah kunci per iterasi: {keys_per_iteration:,}")
        print(f"Dibagi menjadi: {num_splits} bagian\n")

        current_start_dec = start_dec
        ranges = []

        # Looping untuk membagi dan menyimpan semua rentang
        for i in range(num_splits):
            # Menghitung akhir rentang untuk iterasi saat ini
            if i < num_splits - 1:
                current_end_dec = current_start_dec + keys_per_iteration - 1
            # Untuk iterasi terakhir, tambahkan sisa pembagian
            else:
                current_end_dec = current_start_dec + keys_per_iteration + remainder - 1

            # Format rentang heksadesimal dengan padding 0 untuk konsistensi
            start_hex = f'{(hex(current_start_dec))[2:]:0>64}'
            end_hex = f'{(hex(current_end_dec))[2:]:0>64}'

            print(f"Bagian ke-{i+1:03}: {start_hex}:{end_hex}")

            # Tambahkan rentang ke dalam list
            ranges.append({
                "start": start_hex,
                "end": end_hex
            })

            # Menyiapkan start_dec untuk iterasi berikutnya
            current_start_dec = current_end_dec + 1

        # Menyimpan semua rentang ke database MySQL
        save_ranges_to_db(ranges)

    except ValueError:
        print("Error: Pastikan rentang heksadesimal yang Anda masukkan valid.")
    except Exception as e:
        print(f"Error tidak terduga: {e}")

if __name__ == "__main__":
    main()

