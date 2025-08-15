-- File: create_table.sql
-- Skrip SQL ini akan membuat tabel 'key_ranges' untuk menyimpan rentang private key.
-- Tipe data dipilih untuk menampung data dalam jumlah besar dan panjang heksadesimal 64 karakter.

CREATE TABLE IF NOT EXISTS key_ranges (
    -- Kolom ID menggunakan BIGINT UNSIGNED dengan AUTO_INCREMENT.
    -- Ini dapat menampung nilai hingga 18.446.744.073.709.551.615, lebih dari cukup untuk kuadriliun baris.
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    
    -- Kolom start dan end menyimpan string heksadesimal dengan panjang 64 karakter.
    -- VARCHAR(64) adalah tipe data yang fleksibel dan efisien untuk kasus ini.
    start VARCHAR(64) NOT NULL,
    end VARCHAR(64) NOT NULL
);
