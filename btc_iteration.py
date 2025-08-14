# Script ini menghitung jumlah iterasi yang dibutuhkan untuk memindai sebuah rentang
# heksadesimal dengan jumlah kunci per iterasi yang sudah ditentukan.

# =============================================================
# Konfigurasi Awal
# =============================================================
# Rentang heksadesimal awal yang ingin dibagi.
# 200000000000000000:3fffffffffffffffff
start_hex_range = '5f5c28f5c28f5c28ea'
end_hex_range = '5ffffffffffffffff3'

# Jumlah kunci privat yang akan di-scan dalam setiap iterasi.
keys_per_iteration = 1000000

# =============================================================
# Logika Perhitungan
# =============================================================
try:
    # Mengonversi rentang heksadesimal ke angka desimal
    start_dec = int(start_hex_range, 16)
    end_dec = int(end_hex_range, 16)

    # Menghitung total kunci yang ada di rentang
    total_keys = end_dec - start_dec + 1

    # Menghitung jumlah iterasi
    # Kami menggunakan floor division (//) untuk mendapatkan bilangan bulat
    num_iterations = total_keys // keys_per_iteration

    # Menghitung sisa kunci yang tidak termasuk dalam iterasi penuh
    remainder_keys = total_keys % keys_per_iteration

    print(f"Total kunci dalam rentang: {total_keys:,}")
    print(f"Jumlah kunci per iterasi: {keys_per_iteration:,}\n")

    print(f"Jumlah iterasi yang dibutuhkan: {num_iterations:,}")
    if remainder_keys > 0:
        print(f"(Tersisa {remainder_keys:,} kunci yang akan berada di iterasi terakhir.)")

except ValueError:
    print("Error: Pastikan rentang heksadesimal yang Anda masukkan valid.")
