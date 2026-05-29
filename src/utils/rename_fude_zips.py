import os
import glob
import re

# 都道府県コードと英語名のマッピング
prefs = {
    "01": "hokkaido", "02": "aomori", "03": "iwate", "04": "miyagi",
    "05": "akita", "06": "yamagata", "07": "fukushima", "08": "ibaraki",
    "09": "tochigi", "10": "gunma", "11": "saitama", "12": "chiba",
    "13": "tokyo", "14": "kanagawa", "15": "niigata", "16": "toyama",
    "17": "ishikawa", "18": "fukui", "19": "yamanashi", "20": "nagano",
    "21": "gifu", "22": "shizuoka", "23": "aichi", "24": "mie",
    "25": "shiga", "26": "kyoto", "27": "osaka", "28": "hyogo",
    "29": "nara", "30": "wakayama", "31": "tottori", "32": "shimane",
    "33": "okayama", "34": "hiroshima", "35": "yamaguchi", "36": "tokushima",
    "37": "kagawa", "38": "ehime", "39": "kochi", "40": "fukuoka",
    "41": "saga", "42": "nagasaki", "43": "kumamoto", "44": "oita",
    "45": "miyazaki", "46": "kagoshima", "47": "okinawa"
}

def rename_fude_zips(target_dir="data/gis_raw"):
    count_fude = 0
    count_agri = 0
    
    # 1. 筆ポリゴン (MB0001_2025_2020_XX.zip) のリネーム
    for file_path in glob.glob(os.path.join(target_dir, "MB0001_2025_2020_*.zip")):
        filename = os.path.basename(file_path)
        match = re.search(r"MB0001_2025_2020_(\d{2})\.zip", filename)
        if match:
            code = match.group(1)
            if code in prefs:
                pref_name = prefs[code]
                new_name = f"{code}_{pref_name}_fude.zip"
                new_path = os.path.join(target_dir, new_name)
                
                if os.path.exists(new_path):
                    os.remove(new_path)
                    
                os.rename(file_path, new_path)
                print(f"筆ポリゴン リネーム成功: {filename} -> {new_name}")
                count_fude += 1

    # 2. 農業振興地域 (A12-15_XX_GML.zip または A05-15_XX_GML.zip 等) のリネーム
    # 今回は A12-15_XX_GML.zip で検索
    for file_path in glob.glob(os.path.join(target_dir, "A*-*_GML.zip")):
        filename = os.path.basename(file_path)
        match = re.search(r"A\d+-\d+_(\d{2})_GML\.zip", filename)
        if match:
            code = match.group(1)
            if code in prefs:
                pref_name = prefs[code]
                new_name = f"{code}_{pref_name}_agri_zone.zip"
                new_path = os.path.join(target_dir, new_name)
                
                if os.path.exists(new_path):
                    os.remove(new_path)
                    
                os.rename(file_path, new_path)
                print(f"農業振興地域 リネーム成功: {filename} -> {new_name}")
                count_agri += 1
                
    print(f"\n合計 筆ポリゴン {count_fude} 個, 農業振興地域 {count_agri} 個 のデータをリネームしました。")

if __name__ == "__main__":
    rename_fude_zips()
