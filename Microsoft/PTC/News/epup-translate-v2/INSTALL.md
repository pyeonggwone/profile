```bash
sudo dnf install -y --allowerasing curl gcc-c++ make python3
sudo dnf module reset -y nodejs
sudo dnf module install -y nodejs:20
node -v
cd profile/Microsoft/PTC/News/epup-translate-v2
cp .env.example .env
vi .env
chmod +x run-translate.sh
npm install
# input/ 에 번역할 .epub 파일을 넣고 실행
./run-translate.sh input
```
