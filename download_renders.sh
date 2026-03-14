#!/usr/bin/env bash
# Downloads front renders from GSMArena for all new brands
# Usage: bash download_renders.sh
# Images saved to {brand}Pics/{slug}.jpg (raw, before processing)

UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BASE="https://www.gsmarena.com"
FAILED=()
COUNT=0

download_model() {
  local brand_dir="$1"   # e.g. xiaomiPics
  local slug="$2"        # e.g. xiaomi-12-pro
  local query="$3"       # e.g. "Xiaomi 12 Pro"
  local out_path="/home/billy/Desktop/serviceGSM/production/${brand_dir}/${slug}.jpg"

  [[ -f "$out_path" ]] && { echo "  SKIP $slug (exists)"; return; }

  local encoded
  encoded=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$query")

  local search_html
  search_html=$(curl -s -L --user-agent "$UA" \
    "https://www.gsmarena.com/results.php3?sQuickSearch=${encoded}" 2>/dev/null)

  # Extract first device page path e.g. /xiaomi_12-11000.php
  local dev_path
  dev_path=$(echo "$search_html" | grep -oP 'href="/[a-z0-9_]+-[0-9]+\.php"' | head -1 | grep -oP '/[^"]+')

  if [[ -z "$dev_path" ]]; then
    echo "  FAIL (no result) $query"
    FAILED+=("$query")
    return
  fi

  local dev_html
  dev_html=$(curl -s -L --user-agent "$UA" "${BASE}${dev_path}" 2>/dev/null)

  # og:image contains the direct image URL
  local img_url
  img_url=$(echo "$dev_html" | grep -oP 'property="og:image" content="\K[^"]+')

  if [[ -z "$img_url" ]]; then
    echo "  FAIL (no image) $query"
    FAILED+=("$query")
    return
  fi

  curl -s -L --user-agent "$UA" -o "$out_path" "$img_url"
  if [[ $? -eq 0 && -s "$out_path" ]]; then
    echo "  OK  $slug"
    ((COUNT++))
  else
    echo "  FAIL (download) $query"
    FAILED+=("$query")
    rm -f "$out_path"
  fi

  sleep 0.6
}

echo "=== Huawei ==="
download_model "huaweiPics" "p30"            "Huawei P30"
download_model "huaweiPics" "p30-pro"        "Huawei P30 Pro"
download_model "huaweiPics" "nova-5t"        "Huawei Nova 5T"
download_model "huaweiPics" "mate-30"        "Huawei Mate 30"
download_model "huaweiPics" "mate-30-pro"    "Huawei Mate 30 Pro"
download_model "huaweiPics" "p40"            "Huawei P40"
download_model "huaweiPics" "p40-lite"       "Huawei P40 Lite"
download_model "huaweiPics" "p40-pro"        "Huawei P40 Pro"
download_model "huaweiPics" "p40-pro-plus"   "Huawei P40 Pro+"
download_model "huaweiPics" "mate-40"        "Huawei Mate 40"
download_model "huaweiPics" "mate-40-pro"    "Huawei Mate 40 Pro"
download_model "huaweiPics" "p50"            "Huawei P50"
download_model "huaweiPics" "p50-pro"        "Huawei P50 Pro"
download_model "huaweiPics" "nova-9"         "Huawei Nova 9"
download_model "huaweiPics" "nova-10"        "Huawei Nova 10"
download_model "huaweiPics" "nova-10-pro"    "Huawei Nova 10 Pro"
download_model "huaweiPics" "mate-50"        "Huawei Mate 50"
download_model "huaweiPics" "mate-50-pro"    "Huawei Mate 50 Pro"
download_model "huaweiPics" "pura-70"        "Huawei Pura 70"
download_model "huaweiPics" "pura-70-pro"    "Huawei Pura 70 Pro"
download_model "huaweiPics" "pura-70-ultra"  "Huawei Pura 70 Ultra"

echo "=== Honor ==="
download_model "honorPics" "honor-90"           "Honor 90"
download_model "honorPics" "honor-90-pro"       "Honor 90 Pro"
download_model "honorPics" "honor-magic-5-pro"  "Honor Magic 5 Pro"
download_model "honorPics" "honor-magic-6-pro"  "Honor Magic 6 Pro"
download_model "honorPics" "honor-magic-7-pro"  "Honor Magic 7 Pro"
download_model "honorPics" "honor-200"          "Honor 200"
download_model "honorPics" "honor-200-pro"      "Honor 200 Pro"
download_model "honorPics" "honor-x8b"          "Honor X8b"
download_model "honorPics" "honor-x9b"          "Honor X9b"
download_model "honorPics" "honor-x9c"          "Honor X9c"

echo "=== Xiaomi ==="
download_model "xiaomiPics" "mi-10"          "Xiaomi Mi 10"
download_model "xiaomiPics" "mi-10-pro"      "Xiaomi Mi 10 Pro"
download_model "xiaomiPics" "mi-10t"         "Xiaomi Mi 10T"
download_model "xiaomiPics" "mi-10t-pro"     "Xiaomi Mi 10T Pro"
download_model "xiaomiPics" "mi-10-lite"     "Xiaomi Mi 10 Lite"
download_model "xiaomiPics" "mi-11"          "Xiaomi Mi 11"
download_model "xiaomiPics" "mi-11-pro"      "Xiaomi Mi 11 Pro"
download_model "xiaomiPics" "mi-11-ultra"    "Xiaomi Mi 11 Ultra"
download_model "xiaomiPics" "mi-11-lite-5g"  "Xiaomi Mi 11 Lite 5G"
download_model "xiaomiPics" "xiaomi-12"          "Xiaomi 12"
download_model "xiaomiPics" "xiaomi-12-pro"      "Xiaomi 12 Pro"
download_model "xiaomiPics" "xiaomi-12t"         "Xiaomi 12T"
download_model "xiaomiPics" "xiaomi-12t-pro"     "Xiaomi 12T Pro"
download_model "xiaomiPics" "xiaomi-12-lite"     "Xiaomi 12 Lite"
download_model "xiaomiPics" "xiaomi-13"          "Xiaomi 13"
download_model "xiaomiPics" "xiaomi-13-pro"      "Xiaomi 13 Pro"
download_model "xiaomiPics" "xiaomi-13t"         "Xiaomi 13T"
download_model "xiaomiPics" "xiaomi-13t-pro"     "Xiaomi 13T Pro"
download_model "xiaomiPics" "xiaomi-13-lite"     "Xiaomi 13 Lite"
download_model "xiaomiPics" "xiaomi-14"          "Xiaomi 14"
download_model "xiaomiPics" "xiaomi-14-pro"      "Xiaomi 14 Pro"
download_model "xiaomiPics" "xiaomi-14t"         "Xiaomi 14T"
download_model "xiaomiPics" "xiaomi-14t-pro"     "Xiaomi 14T Pro"
download_model "xiaomiPics" "xiaomi-15"          "Xiaomi 15"
download_model "xiaomiPics" "xiaomi-15-pro"      "Xiaomi 15 Pro"

echo "=== Oppo ==="
download_model "oppoPics" "reno-4"         "Oppo Reno 4"
download_model "oppoPics" "reno-4-pro"     "Oppo Reno 4 Pro"
download_model "oppoPics" "reno-5"         "Oppo Reno 5"
download_model "oppoPics" "reno-5-pro"     "Oppo Reno 5 Pro"
download_model "oppoPics" "reno-6"         "Oppo Reno 6"
download_model "oppoPics" "reno-6-pro"     "Oppo Reno 6 Pro"
download_model "oppoPics" "reno-7"         "Oppo Reno 7"
download_model "oppoPics" "reno-7-pro"     "Oppo Reno 7 Pro"
download_model "oppoPics" "reno-8"         "Oppo Reno 8"
download_model "oppoPics" "reno-8-pro"     "Oppo Reno 8 Pro"
download_model "oppoPics" "reno-10"        "Oppo Reno 10"
download_model "oppoPics" "reno-10-pro"    "Oppo Reno 10 Pro"
download_model "oppoPics" "reno-12"        "Oppo Reno 12"
download_model "oppoPics" "reno-12-pro"    "Oppo Reno 12 Pro"
download_model "oppoPics" "reno-13"        "Oppo Reno 13"
download_model "oppoPics" "reno-13-pro"    "Oppo Reno 13 Pro"
download_model "oppoPics" "find-x2"        "Oppo Find X2"
download_model "oppoPics" "find-x2-pro"    "Oppo Find X2 Pro"
download_model "oppoPics" "find-x3"        "Oppo Find X3"
download_model "oppoPics" "find-x3-pro"    "Oppo Find X3 Pro"
download_model "oppoPics" "find-x5"        "Oppo Find X5"
download_model "oppoPics" "find-x5-pro"    "Oppo Find X5 Pro"
download_model "oppoPics" "find-x6"        "Oppo Find X6"
download_model "oppoPics" "find-x6-pro"    "Oppo Find X6 Pro"
download_model "oppoPics" "find-x7"        "Oppo Find X7"
download_model "oppoPics" "find-x7-ultra"  "Oppo Find X7 Ultra"

echo "=== Motorola ==="
download_model "motorolaPics" "moto-g9-play"       "Motorola Moto G9 Play"
download_model "motorolaPics" "moto-g9-plus"       "Motorola Moto G9 Plus"
download_model "motorolaPics" "moto-g9-power"      "Motorola Moto G9 Power"
download_model "motorolaPics" "moto-g30"           "Motorola Moto G30"
download_model "motorolaPics" "moto-g50"           "Motorola Moto G50"
download_model "motorolaPics" "moto-g60"           "Motorola Moto G60"
download_model "motorolaPics" "moto-g72"           "Motorola Moto G72"
download_model "motorolaPics" "moto-g82-5g"        "Motorola Moto G82 5G"
download_model "motorolaPics" "moto-g14"           "Motorola Moto G14"
download_model "motorolaPics" "moto-g24"           "Motorola Moto G24"
download_model "motorolaPics" "moto-g34-5g"        "Motorola Moto G34 5G"
download_model "motorolaPics" "moto-g44-5g"        "Motorola Moto G44 5G"
download_model "motorolaPics" "moto-g54-5g"        "Motorola Moto G54 5G"
download_model "motorolaPics" "moto-g64-5g"        "Motorola Moto G64 5G"
download_model "motorolaPics" "moto-g84-5g"        "Motorola Moto G84 5G"
download_model "motorolaPics" "moto-g85-5g"        "Motorola Moto G85 5G"
download_model "motorolaPics" "moto-edge-20"       "Motorola Moto Edge 20"
download_model "motorolaPics" "moto-edge-20-pro"   "Motorola Moto Edge 20 Pro"
download_model "motorolaPics" "moto-edge-30"       "Motorola Moto Edge 30"
download_model "motorolaPics" "moto-edge-30-pro"   "Motorola Moto Edge 30 Pro"
download_model "motorolaPics" "moto-edge-30-neo"   "Motorola Moto Edge 30 Neo"
download_model "motorolaPics" "moto-edge-30-ultra" "Motorola Moto Edge 30 Ultra"
download_model "motorolaPics" "moto-edge-40"       "Motorola Moto Edge 40"
download_model "motorolaPics" "moto-edge-40-pro"   "Motorola Moto Edge 40 Pro"
download_model "motorolaPics" "moto-edge-40-neo"   "Motorola Moto Edge 40 Neo"
download_model "motorolaPics" "moto-edge-50"       "Motorola Moto Edge 50"
download_model "motorolaPics" "moto-edge-50-pro"   "Motorola Moto Edge 50 Pro"
download_model "motorolaPics" "moto-edge-50-ultra" "Motorola Moto Edge 50 Ultra"
download_model "motorolaPics" "moto-edge-50-fusion" "Motorola Moto Edge 50 Fusion"

echo "=== OnePlus ==="
download_model "oneplusPics" "oneplus-8"       "OnePlus 8"
download_model "oneplusPics" "oneplus-8-pro"   "OnePlus 8 Pro"
download_model "oneplusPics" "oneplus-8t"      "OnePlus 8T"
download_model "oneplusPics" "oneplus-9"       "OnePlus 9"
download_model "oneplusPics" "oneplus-9-pro"   "OnePlus 9 Pro"
download_model "oneplusPics" "oneplus-9r"      "OnePlus 9R"
download_model "oneplusPics" "oneplus-10-pro"  "OnePlus 10 Pro"
download_model "oneplusPics" "oneplus-10t"     "OnePlus 10T"
download_model "oneplusPics" "oneplus-11"      "OnePlus 11"
download_model "oneplusPics" "oneplus-11r"     "OnePlus 11R"
download_model "oneplusPics" "oneplus-12"      "OnePlus 12"
download_model "oneplusPics" "oneplus-12r"     "OnePlus 12R"
download_model "oneplusPics" "oneplus-13"      "OnePlus 13"
download_model "oneplusPics" "oneplus-13r"     "OnePlus 13R"
download_model "oneplusPics" "nord"            "OnePlus Nord"
download_model "oneplusPics" "nord-2"          "OnePlus Nord 2"
download_model "oneplusPics" "nord-2t"         "OnePlus Nord 2T"
download_model "oneplusPics" "nord-3"          "OnePlus Nord 3"
download_model "oneplusPics" "nord-4"          "OnePlus Nord 4"
download_model "oneplusPics" "nord-ce"         "OnePlus Nord CE"
download_model "oneplusPics" "nord-ce-2"       "OnePlus Nord CE 2"
download_model "oneplusPics" "nord-ce-3"       "OnePlus Nord CE 3"
download_model "oneplusPics" "nord-ce-4"       "OnePlus Nord CE 4"

echo "=== Realme ==="
download_model "realmePics" "realme-8"          "Realme 8"
download_model "realmePics" "realme-8-pro"      "Realme 8 Pro"
download_model "realmePics" "realme-8i"         "Realme 8i"
download_model "realmePics" "realme-9"          "Realme 9"
download_model "realmePics" "realme-9-pro"      "Realme 9 Pro"
download_model "realmePics" "realme-9-pro-plus" "Realme 9 Pro+"
download_model "realmePics" "realme-9i"         "Realme 9i"
download_model "realmePics" "realme-10"         "Realme 10"
download_model "realmePics" "realme-10-pro"     "Realme 10 Pro"
download_model "realmePics" "realme-10-pro-plus" "Realme 10 Pro+"
download_model "realmePics" "realme-11"         "Realme 11"
download_model "realmePics" "realme-11-pro"     "Realme 11 Pro"
download_model "realmePics" "realme-11-pro-plus" "Realme 11 Pro+"
download_model "realmePics" "realme-12"         "Realme 12"
download_model "realmePics" "realme-12-pro"     "Realme 12 Pro"
download_model "realmePics" "realme-12-pro-plus" "Realme 12 Pro+"
download_model "realmePics" "realme-gt"         "Realme GT"
download_model "realmePics" "realme-gt-2"       "Realme GT 2"
download_model "realmePics" "realme-gt-2-pro"   "Realme GT 2 Pro"
download_model "realmePics" "realme-gt-neo-2"   "Realme GT Neo 2"
download_model "realmePics" "realme-gt-neo-3"   "Realme GT Neo 3"
download_model "realmePics" "realme-gt-neo-5"   "Realme GT Neo 5"
download_model "realmePics" "realme-gt-6"       "Realme GT 6"
download_model "realmePics" "realme-c31"        "Realme C31"
download_model "realmePics" "realme-c33"        "Realme C33"
download_model "realmePics" "realme-c35"        "Realme C35"
download_model "realmePics" "realme-c51"        "Realme C51"
download_model "realmePics" "realme-c53"        "Realme C53"
download_model "realmePics" "realme-c55"        "Realme C55"
download_model "realmePics" "realme-c67"        "Realme C67"

echo "=== Google ==="
download_model "googlePics" "pixel-6"          "Google Pixel 6"
download_model "googlePics" "pixel-6-pro"      "Google Pixel 6 Pro"
download_model "googlePics" "pixel-6a"         "Google Pixel 6a"
download_model "googlePics" "pixel-7"          "Google Pixel 7"
download_model "googlePics" "pixel-7-pro"      "Google Pixel 7 Pro"
download_model "googlePics" "pixel-7a"         "Google Pixel 7a"
download_model "googlePics" "pixel-8"          "Google Pixel 8"
download_model "googlePics" "pixel-8-pro"      "Google Pixel 8 Pro"
download_model "googlePics" "pixel-8a"         "Google Pixel 8a"
download_model "googlePics" "pixel-9"          "Google Pixel 9"
download_model "googlePics" "pixel-9-pro"      "Google Pixel 9 Pro"
download_model "googlePics" "pixel-9-pro-xl"   "Google Pixel 9 Pro XL"
download_model "googlePics" "pixel-9-pro-fold" "Google Pixel 9 Pro Fold"
download_model "googlePics" "pixel-fold"       "Google Pixel Fold"

echo ""
echo "=== DONE ==="
echo "Downloaded: $COUNT"
echo "Failed (${#FAILED[@]}):"
for f in "${FAILED[@]}"; do echo "  - $f"; done
