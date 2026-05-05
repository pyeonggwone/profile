# install

## Rust toolchain

```powershell
winget install Rustlang.Rustup
rustup default stable
rustup update
```

## Node.js toolchain

```powershell
winget install OpenJS.NodeJS.LTS
```

## Workspace dependencies (default features)

```powershell
cd profile\Microsoft\PTC\News\pdf-translate-v1
cargo fetch
cargo build
cargo test
```

## Workspace with optional native codecs

```powershell
vcpkg install openjpeg:x64-windows jbig2dec:x64-windows
$env:VCPKG_ROOT = "C:\vcpkg"
cargo build --features "pdf_filters/jpx-openjpeg pdf_filters/jbig2-jbig2dec pdf_filters/mozjpeg-encode"
```

## Server

```powershell
cargo run -p pdftr_server
```

## CLI

```powershell
cargo run -p pdftr_cli -- inspect path\to\sample.pdf
cargo run -p pdftr_cli -- text path\to\sample.pdf
cargo run -p pdftr_cli -- render-plan path\to\sample.pdf 1
cargo run -p pdftr_cli -- roundtrip path\to\sample.pdf
cargo run -p pdftr_cli -- edit input.pdf output.pdf --edits edits.json
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Frontend production build

```powershell
cd frontend
npm run build
npm run preview
```

## Environment variables

```powershell
$env:PDFTR_ADDR = "127.0.0.1:7878"
$env:PDFTR_WORKDIR = "C:\pdftr\workdir"
```

## Cleanup

```powershell
cargo clean
Remove-Item -Recurse -Force frontend\node_modules
Remove-Item -Recurse -Force frontend\dist
Remove-Item -Recurse -Force workdir
```
