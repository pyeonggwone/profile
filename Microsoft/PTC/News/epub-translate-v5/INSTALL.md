
npm install --no-audit --no-fund
npm start
node src/index.mjs
node src/index.mjs --format epub
node src/index.mjs --format azw3

# AZW3 번역에는 Calibre CLI가 필요하다.
# ebook-convert가 PATH에 없으면 .env에 EBOOK_CONVERT_PATH를 지정한다.
# Windows 예: EBOOK_CONVERT_PATH=C:\Program Files\Calibre2\ebook-convert.exe
# WSL 예: EBOOK_CONVERT_PATH=/mnt/c/Program Files/Calibre2/ebook-convert.exe

chmod +x run-translate.sh
mkdir -p input output work input/done ebook-metadata
./run-translate.sh
./run-translate.sh --format epub
./run-translate.sh --format azw3