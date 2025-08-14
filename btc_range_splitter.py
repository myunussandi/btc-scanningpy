# btc_range_splitter.py
# Script ini membagi rentang heksadesimal menjadi beberapa bagian yang sama dan menyimpannya ke file JSON.

import json

# =============================================================
# Konfigurasi Awal
# =============================================================
# Rentang heksadesimal awal yang ingin dibagi.
# Rentang ini di-padding menjadi 64 digit heksadesimal (256 bit).
start_hex_range = '0000000000000000000000000000000000000000000000000000000000080000'
end_hex_range = '00000000000000000000000000000000000000000000000000000000000fffff'

# Jumlah bagian yang Anda inginkan untuk membagi rentang.
# Anda bisa mengubah nilai ini menjadi 10, 1000, atau lainnya.
num_splits = 100

# Nama file output untuk menyimpan rentang dalam format JSON.
OUTPUT_FILE = "range_splitter.json"

# =============================================================
# Logika Perhitungan
# =============================================================
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

    # Looping untuk mencetak dan menyimpan semua rentang
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
            "id": i + 1,
            "start": start_hex,
            "end": end_hex
        })

        # Menyiapkan start_dec untuk iterasi berikutnya
        current_start_dec = current_end_dec + 1

    # Simpan list rentang ke dalam file JSON
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(ranges, f, indent=4)
    print(f"\nSemua rentang telah disimpan ke file '{OUTPUT_FILE}'.")

except ValueError:
    print("Error: Pastikan rentang heksadesimal yang Anda masukkan valid.")

