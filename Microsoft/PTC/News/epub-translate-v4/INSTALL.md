Get-Command node,npm
node -v
npm -v
winget install OpenJS.NodeJS.LTS
Get-Command node,npm
node -v
npm -v
winget install Microsoft.VisualStudio.2022.BuildTools
cd profile/Microsoft/PTC/News/epub-translate-v4
Copy-Item .env.example .env
notepad .env
npm install
Get-ChildItem input
npm start
node src/index.mjs
node src/index.mjs --input input
node src/index.mjs --input input/book.epub
node src/index.mjs --format epub
node src/index.mjs --output output --metadata ebook-metadata
